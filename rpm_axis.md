# RPM Range/Map Axis

In this section, we'll get to see a map being used. But this map doesn't contain boost or cycling valve duty cycle or anything cool like that. It just contains the ranges needed for the rpm axis of the cool maps! So this map is a pretty simple one, with only one axis. Still, you need to understand this if you want to understand most of the KLR code. RPM is used all over the place. In addition to the main maps I mentioned above, there's also 12 very small rpm-only maps that control all kinds of parameters, like the maximum timing to pull when knocking occurs, or how many igntition cylces to wait before restoring timing etc. So the routine we're going to examine here is really critical, and it's output is one of the most used parameters in the whole system. 

## Overview

We previously looked at [how engine speed is measured](speed_measurement.md) in the KLR code. That measurement gives us speed in *timer-ticks-per-180-degrees*, but for many things we need the engine speed in the more familiar unit of *revolutions-per-minute*. 

We don't really need the exact rpm though; most maps use either 8 or 16 rpm ranges (separated by a few hundred rpm), so what we really need is a number from 0 to 15 that indicates which *range* the rpm is in (e.g. 2000-2400, 2401-2800 etc.). That number will then be used to look up map values. 

The way this is done is a little convoluted, but it's not too complicated. The basic idea is: there's a map that stores 15 values that represnent the 15 rpm ranges (the 16th is a default), and we just take the current speed measurement, and turn it into an *index*  (or *offset*) into that map, and then look up and store the corresponding value. That value then represents the rpm range that we're currently in, and can be used to look up things like boost and cycling valve pulsewidth from the main maps. 

There are two things that complicate the situation, however: 

1. we must do some arithmetic on the existing speed measurement in order to use it as a map offset

2. the map values represent the *differences* between rpm ranges, not the ranges themselves. This is a common technique used in Motronic software (i.e. in the DME). It actually makes the code simpler, but it makes things a little harder to think about. 


## How The RPM Axis Algorithm Works

The code for this function is found at 0xA57, but it's worth describing the algorithm at an abstract level before diving into the code. 

First, here's what the map actually looks like (it's stored at 0xA00):


0  |  1|  2|  3|  4|  5|  6|  7|  8|  9| 10| 11| 12| 13| 14
---|---|---|---|---|---|---|---|---|---|---|---|---|---|---
1| 1| 2| 1| 1| 2| 2| 2| 2| 2| 3| 3| 3| 4| 4

(There are only 15 values because there's a default value that the code uses for speeds above 6380rpm.)

Now, starting with the first entry from this map, we multiply that entry by 4 and add the result to our pseudo-rpm. Then we move to the second map entry, and repeat. We keep doing this until the add results in a carry (i.e. overflow). When that happens, the map offset of the last entry we added represents the rpm range! So we just store that number, and use it later any time we need to look things up by rpm. 

Of course there are a few special cases and caveats in the code, but that's the gist of how it works. Having this outline in mind when you read the code should make it more manageable. 

Now [recall](speed_measurement.md) that the speed meaurement was originally taken by counting down from 255 between trigger events, and then it was complemented before being stored in 0x24h. That means that the value in 24h is lower for higher engine speeds. In this routine, we complement it again, so that higher numbers represent higher speeds. You can see what this means for the map values: the higher the number we start with, the sooner we'll hit an overflow when we start adding the map entries. Therefore the values 0 to 15 represent the rpm ranges from __high__ to __low__, with 0 being the highest rpm, and 15 being the lowest. 

The map offest is stored in RAM location 0x44h at the end of the routine. The value in 0x44h will from 0 to 60. There aren't 60 values in the map of course - there are only 15. But they're represented as 1/4 values, which you'll see in the code below.  Later, when 0x44h is being used to look up values from a map, it'll be divided by either 4 or 8 (depending on whether the map in question has 8 or 16 values in it's rpm axis) and then 1 will be added. 

I want to show you the actual ranges used, but I don't want to show you all 60 of them, for the sake of readability. So I'll show *(0x44h / 8) + 1* in the following table, since that's how the values are actually used later:

RPM Range | Axis Value
----------|------
0000 - 1863| 16
1864 - 2040| 15
2041 - 2253| 14
2254 - 2445| 13
2446 - 2673| 12
2674 - 2947| 11
2948 - 3163| 10
3164 - 3414| 9
3415 - 3707| 8
3708 - 4056| 7
4057 - 4478| 6
4479 - 4723| 5
4724 - 4997| 4
4998 - 5652| 3
5653 - 6049| 2
6050 - 6386| 1
6387 - limit| 0

One odd thing that jump out from this is how irregular the spacing is between the rpm ranges. This is a result of the irregular map values shown above. Genererally the spacing increases as rpm goes up. I don't know the reason for this - it's as if more resolution was required for lower rpms. In any case, the maps in the DME work the same way, but the actual values used there are more rounded. But in the DME code, the raw speed measurement happens to come out as a nice round number in the first place - it's actual rpm divided by 40. So the irregular values used in the KLR are probably just a consequence of the awkward way in which engine speed is measured (see [here](speed_measurement.md).)

### The Code

This routine makes use of the __movp__ instruction to look up values from a map. If you're not familiar with how that works, it's worth reading the [notes on reading 8048 code](reading_code.md) - particularly the section on __movp__. 

First, we initalize some registers, then load __and complement__ the current speed measurement, storing the complemented version in __r4__:

```asm
0xa57 mov  r1,#$44
0xa59 mov  r0,#$24
0xa5b mov  r6,#$0
0xa5d mov  a,@r0
0xa5e cpl  a
0xa5f mov  r4,a
```

Location 0x44h will take the output of this routine (the rpm axis value); the current raw speed measurement is in 0x24h. The counter __r6__ is initialized to zero and will be used to keep track of the map offset. 


Next we check if engine speed is below 1500rpm:

```asm
0xa60 sel  rb0
0xa61 mov  a,r7
0xa62 sel  rb1
0xa63 cpl  a
0xa64 jb1  $0A7C
0xa66 cpl  a
```

If you don't understand how this relates to checking current engine speed, read [this](speed_measurement.md). Also, if you don't know what the __sel__ instructions do here, they just make sure that we're using the correct version of __r7__, since there are 2 register banks of __r0__ to __r7__. Read [the notes](reading_code.md) on MCS48 code for a complete explanation of this. 

If we're currently below 1500rpm, we jump to 0xA7C which just sets the output to 60, which is the maximum value. 

Next (if above 1500rpm) we add 56 to the value from __r7__ (which must be 254 at this point; again, read the speed measurement section if you're not sure why). This leaves the accumulator at 54. 

To that, we add the complemented speeed measurement. If it carries, that means the original speed measurement value was < 54, which corresponds to an rpm of > approximately 6380; in this case we jump to the end and set the output to 0 (the minimum value). 

```asm
0xa67 add  a,#$38
0xa69 add  a,r4
0xa6a mov  r4,a
0xa6b jc   $0A77
```

So, assuming we haven't jumped to the end for either the maximum or minimum values, we need to do the calculation I described in the previous section:

```asm
0xa6d inc  r6
0xa6e mov  a,r6
0xa6f rrc  a
0xa70 clr  c
0xa71 rrc  a
0xa72 movp a,@a
0xa73 add  a,r4
0xa74 mov  r4,a
0xa75 jnc  $0A6D
```

The above loop increments __r6__, divides it by 4 (2 rrc operations), looks up the value from the map, and adds it to the current running total in __r4__. The map for this routine is located at 0xA00. The __movp__ instruction always operates relative to the beginning of the current 256 word __page__ (see [this section](reading_code.md)) for a complete explanation of this). 

Recall that in the previous section I said the value from the map is multipled by 4. Here's the detailed explanation of that: because the map offset is divided by 4 in the code above (integer division of course), it'll take 4 iterations to get to the next value. It's one step up and 3 steps back! So we'll add the same map value to the running total 4 times before we move on to the next one. 

I was simplfying things in the previous section of course; the overflow could happen after adding the map value once, twice, or three times. So we are getting better resolution by storing 1/4 values in the map. 

Remember the starting value in __r4__ was the __complement__ of the raw speed measuremnt, so lower values mean lower rpm, and so we'll need more iterations of the loop - and hence a higher value of __r6__ - to get the overflow that breaks the loop. 

Eventually it's guaranteed to overflow though, and in that case we proceed:

```asm
0xa77 mov  a,#$C4
0xa79 add  a,r6
0xa7a jnc  $0A7F
0xa7c mov  r6,#$3C
```

The above code checks if the value that ended up in __r6__ was greater than 60, and if so, just sets it to 60. Recall from the beginning of this section that 60 is the maximum value, representing the lowest rpm range (0 - ~1800).

Finally we get the value from __r6__ and store it in the location pointed to be __r1__ (which you'll recall was 0x44h), and return. The __xch__ command here is just a convenient way of putting the value from __r6__ into the accumulator. The value of the accumulator is simulaneously stored in __r6__, but it's not used. 

Also note that if we jumped from 0xA6B due to rpm being very high, then __r6__ would be zero at this point (from the initialization of the function) so the output would be 0, which represents the highest rpm range (~6380 and up). 

```asm
0xa7e clr  a
0xa7f xch  a,r6
0xa80 mov  @r1,a
0xa81 ret
```

