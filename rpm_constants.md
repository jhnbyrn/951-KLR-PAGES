# RPM Constant Maps

In this section we'll take a look at a number of small rpm based maps that contain various constants. 

## Overview
The routine that reads these maps is located at 0x900. It uses the rpm axis value in 0x44h as its input - you can read about where that value comes from in the [rpm axis](rpm_axis.md) section. 

This is a fairly short routine, but there's one very interesting thing about it that we don't see in the other map routines: it uses the current rpm to read many small, separate maps, and the locations into which the various values are loaded are *themselves stored in the map*. So there's a little bit of clever indirect RAM addressing involved. 

## The Maps
 
It's worth looking at the structure of the maps first before we dive into the code - that should make it much easier to understand what's going on. 

What we have is a series of one-axis maps - twleve of them. Each one has 9 entries. The first entry is the RAM location that will be used to store the value we look up from that map. The remaining 8 values are the actual map values for the 8 possible rpm ranges. These maps begin at 0x925. Here's the first map and a little bit of the second one, just to illustrate the structure we're dealing with (I've shown the RAM locations as hex and the map values as decimal to highlight the difference in their purpose):

Location| Value
--------|------
0x925| __0x2A__
0x926| 155
0x927| 155
0x928| 149
0x929| 146
0x92a| 145
0x92b| 138
0x92c| 131
0x92d| 127
0x92e| __0x2B__
0x92f| 61
0x930| 49
...| ...

So, reading the first map will result in loading one of the values from 0x926 to 0x92d being loaded into location 0x2A, and so on. Next we'll look at the code that achieves this. 

## The code
The routine begins at 0x900. I'm going to lean heavily on the notes I wrote in the [reading the code](reading_code.md) section here. If you aren't familiar with the stuff covered in there (especially around the __movp__ instruction and special registers __r0__ and __r1__) then you'll want to brush up on that first. 

```asm
0x900 mov  r1,#$44
0x902 mov  a,@r1
0x903 rl   a
0x904 swap a
0x905 anl  a,#$7
0x907 inc  a
0x908 mov  r5,a
```
We start by loading the current rpm axis value from 0x44h. The code from 0x903 to 0x907 reduces the rpm axis value into the range of 1 to 8 (divdide by 8, then add 1). Then we just store that value in __r5__. 

Soon we will use that value as an offset into *each* of the various rpm constant maps. 

The following sections are where all the action happens:

```asm
0x909 mov  r2,#$25
0x90b mov  a,r2
0x90c movp a,@a
0x90d jz   $0919
0x90f mov  r1,a
```

We load 0x25h into __r2__ and then load the value from the resulting program memory location into the accumulator. So __r2__ is the offset for the start of each map (relative to the start of the page, which is 0x900). __r5__ will be the offset into the map itself, from which we'll get the actual value. 

If the value was zero, we jump to the end; otherwise, we continue here. But note what we're doing with the value we just looked up - it goes into __r1__. This is one of the registers used for indirect RAM addressing, which should indicate to you that this value is not a variable, but a RAM address, as we discussed. 

This RAM location that we just stored in __r1__ will be the location that holds the actual map value that we're about to look up:

```asm
0x910 mov  a,r2
0x911 add  a,#$9
0x913 xch  a,r2
0x914 add  a,r5
0x915 movp a,@a
0x916 mov  @r1,a
0x917 jmp  $010B
```

Here we add 9 to the __r2__ map offset, but exchange the current value into the accumulator at the same time. So __r2__ now has the offset for the beginning of the next map, and the accumulator has the offset of the beginning of the current map. 

Next we add the actual map offset __r5__ to __r2__ and look up the value using __movp__. We store that value into the location pointed to be __r1__, which you will recall was the first value we looked up using __r2__ - that's some pretty cool programming!

Don't be caught out by the last line, which looks like it jumps to somewhere completely different. That's a bank 1 address, so it's really 0x90B, which is what causes this code to loop until we look up a zero into __r2__. There's a zero stored at the end of the maps for exactly this purpose. If this jump confuses you, you need to read the [notes](reading_code.md).

That's actually the end of the rpm constants lookup code. The next part of the routine is for looking up another map, which has a must more complicated use, and so we'll have to leave that until another section (it's the rpm/throttle map for PID gain values, if you're interested!). 


## What Did We Just Do?

So now that we've just used the current rpm value to look up no fewer than 12 separate map values, what are they all for? Well, you'll see them used throughout the code, and I'll try to make sure that I mention where they come from. But for now, here's the complete list of which locations we just filled, and what the general purpose of each value is. I'm not showing the actual values here, because there's quite a lot of them - maybe I'll add that later. Just remember each one of these is looked up by rpm only:

Location | Purpose
---------|---------
0x2A|    for calculating the angle to start ADC prep and self-test (that angle will be stored in 0x22h)
0x2B|    for calculating the angle for ADC read (angle will be stored in 23h)
0x47|    coefficient for knock threshold (makes knock detection less sensitive at higher rpm)
0x4A|    cycle count before restoring 0.3 deg. timing (this value is used to initialize the counter 49h)
0x50|    cycle count before restoring boost
0x4E|    cycle count before pulling boost
0x4B|    max timing retard (set to 18 decimal for all rpm, which corresponds to ~6 degrees)
0x48|    throttle position threshold for knock control
0x4C|    threshold for pulling boost
0x3E|    angle for WOT (set to 66 decimal for all rpm)
0x45|    minimum knock threshold value (10 decimal for all rpm)
0x69|    counter for 6A (set to 4 for all rpm; used in PID boost control)

Many of these might not make much sense at this point, but they all have their place in the code. Any time you come across a mysterious variable that the programmers seemed to have just presumed would be initialized, it's worth referring to this table to see if it's one of these guys!

I mentioned that several of these maps have all entries set to the same value. Clearly, these are things that the engineers contemplated tuning by rpm, but ultimately thought better of it. So for example, the TPS angle that triggers the wide-open-throttle signal can be tuned by rpm - but in the end they made it the same for all engine speeds. 


