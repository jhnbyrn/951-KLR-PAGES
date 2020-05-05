# Knock Detection Software

In this section we'll examine the knock detection routine from the KLR code in detail. Before reading this section, you should have a pretty good idea of what knock is, and how it's mitigated by reducing spark advance (aka "timing"), and ideally you should be reasonably familiar with the KLR's [knock sensor hardware](knock_hardware.md). 

If you're not already familiar with this stuff, I high recommend reading [Engine Basics: Detonation and Pre-Ignition](http://944enhancement.com/html/knock_ping.html) by Allen W. Cline. 

To understand the code, you'll also need to be reasonably fluent in 8048 series assembly code at this point; see the [notes on reading MCS48 code](reading_code.md) and the early sections on [engine speed](speed_measurement.md) and [ignition signal generation](ignition_signal.md) for an introduction if you're not already familiar with this. 

## Overview

As usual we'll start with an abstract overview of how the knock routine works, and then dive into the code afterwards. The knock sensor code is pretty complicated though, so even the overview will have to be pretty involved!

Recall from the hardware section that the knock sensor's output is integrated and then fed to the ADC. There's a routine that's dedicated to just reading the various ADC channels and storing the values, and it's quite involved, so for the purpose of analyzing the knock routine we'll assume that the integrated knock sensor value has been read already. It's stored in location 0x46.

Very briefly, the knock routine checks if the signal from the knock sensor looks like knock or not, and if so, it takes steps to mitigate it, starting with a timing delay of 3 degrees, to be applied to the knocking cylinder the next time it fires. If it knocks again, it ets another 3 degrees of timing delay, and if knocking persists after that, we start reducing boost by around 4kpa at a time. 

In order to decide if the signal from the sensor really is knock or not, it must be compared to a threshold. The thresholds in the KLR are actually pretty sophisticated:

* each cylinder has it's own threshold, so that knock can be reliably detected even though each cylinder has a different level of "normal" noise.

* the thresholds are adaptive, so that the normal noise level for each cylinider can change slowly without triggering a false knock detection.

* the sensitivity is adjusted by rpm, so that detection is a little less sensitive at higher rpm. 

One important thing that's *not* done in the software is filtering for any particular frequency. The frequency filtering is done by the hardware, which you can read about [here](knock_hardware.md). 

## A Note on Timing

A very important point to note is *when* the knock routine runs. It runs *before* the ADC read routine - therefore it must operate on the knock sensor value from the *previous* cycle. That's ok, because __knocking is tracked and controlled individually for each cylinder__. So when the knock routine runs, we know that the cylinder that fired on the *previous* cycle won't fire again until another 3 ignition cycles have taken place. So, we'll calculate any necessary delay, and then make sure that that delay is applied to the ignition signal after 3 more ignition events. In order to achive this, there's a lot of copying and rotating of values in various parts of the code, and it can be pretty confusing to try to decipher all that while you're trying to understand the calculations at the same time. So I've put together a walkthrough of how it all works in the appendix. If you don't want to think about all that rotating etc., you can just trust that the timing delay that's calculated in this routine will be applied to the same cylinder that generated the knock signal, and it will be applied the *next time* that cylinder fires. 

## The Knock Routine in Pseudo-Code

I thoguht it might be usefufl to have a quick rundown of everything that the knock routine actually does, in the order that it's done in, before getting into the actual code:

* detect if the most recent ignition event caused knock:

	* load the knock threshold for the cylinder in question; if it's below a certain minimum value, replace it with the minimum. This has the effect of establishing an absolute threshold - a sort of catch-all that applies to all cylinders.

	* we then scale the threshold using a coefficient that's looked up from a map, based on rpm ([it's the value in 0x47 from this map](rpm_constants.md). This has the effect of making knock detection less sensitive at higher rpm. 

	* next we compare the knock sensor's output to our scaled, per-cylinder threshold to determine if we have knock

	* if the knock threshold is exceeded, we initialize an ignition timing delay of 3 degrees

* restore timing pulled from a previous cylinder, if appropriate. 

	* for this, we decrement a counter and if it overflows, we subtract 0.3 degrees from the timing delay values for all cylinders that have a delay, and reset the counter. 

	* the counter value that's used varies with rpm, so that timing is restored more slowly at higher rpm ([0x4A fom the rpm constants map](rpm_constants))

* rotate the RAM locations that keep track of the timing delays for each cylinder (70h - 73h) (more detail on this in the next section)

* perform the [self-test of the knock sensor circuit](knock_hardware.md) (if it's time)

	* the self-test is run every few hundred cycles, so this part of the knock routine is actually skipped most of the time
	
	* the test constists of injecting a fake knock signal into the knock sensor amplifier and checking if that triggers knock detection. The signal is generated in the ADC read routine; the knock routine keeps count of how many times it fails to detect knock
	
	* if the test fails to trigger knock detection 6 times in a row, a blink code is triggered to indicate that the KLR is faulty. 

* deal with the knocking we detected 

	* set the knocking YES/NO pin if necessary (if the knock threshold was exceeded)

	* add the timing delay we initialized earlier to the total timing delay for this cylinder

* calculate a new knock threshold for the current cylinder, and rotate it in the same way as the timing delay values

	* this new threshold is calculated from the knock sensor output value. The value is passed into an [exponential smoothing function](exponential_smoothing.md) which has the effect of a low-pass filter. (Wikipedia article [here](https://en.wikipedia.org/wiki/Exponential_smoothing.)) In other words, brief spikes in noise won't change the threshold significantly, but a change in the base noise level that lasts consistently will. 

* restore previous boost reduction if appropriate (in increments of about 0.8 kpa)

* finally we check if it's necessary to add a futher boost reduction, and if so, add 5 units (approx 4 kpa) to the total boost reduction value (57h). 

## The Code

The knock detection routine begins at 0xD00. The first section is where detection actually happens. First, we load the current knock threshold value for the cylinder that fired in the previous cycle (7Ah), then we check if that threshold is higher than the maximum (45h), and if so, overwrite it with maximum value:

```asm
0xd00 mov  r0,#$7A
0xd02 mov  r1,#$45
0xd04 mov  a,@r1
0xd05 cpl  a
0xd06 add  a,@r0
0xd07 jc   $0D0B
0xd09 mov  a,@r1
0xd0a mov  @r0,a
```

The value in 45h is one of the [rpm constants](rpm_constants.md) that's looked up from a one-axis map, so that it can be tuned by rpm. But it's actually set to 10 for all rpm, so it looks like the engineers decided not to use this tuneability in the end. 

The above code has the effect of establishing the value in 45h as an *absolute* threshold that applies to all cylinders. Recall that the knock sensor output is inverted by the hardware, so we'll be checking for vaues *below* the threshold in 7Ah. 

Next we come to a part that's a little difficult to follow:

```asm
0xd0b mov  r1,#$47
0xd0d mov  r2,#$0
0xd0f mov  a,@r0
0xd10 mov  r0,a
0xd11 mov  r4,a
0xd12 rlc  a
0xd13 call $07C1		;0xFC1
0xd15 call $07C1
0xd17 call $07BD		;0xFDB
0xd19 call $07BD
0xd1b mov  a,@r1
0xd1c swap a
0xd1d xchd a,@r1
```

Here's the tl;dr version of what the above code actually does: it multiples our threshold value 7Ah by a coefficient (47h). This coeffecient is another of the [rpm constants](rpm_constants) and it's effectively 1.5 (low rpm), 1.25 (medium rpm), or 1 (high rpm). This makes knock detection more sensitive at lower rpm, and (relatively speaking) less sensitive at medium to higher rpm. 

Now that you know what it does, you can carry on with the main walkthough. But if you want a detailed description of this multiplcation routine, it's in the Appendix section. 

So, now we have our scaled threshold, and it's time to actually compare it to the knock sensor value and decide if we have knock, or not:

```asm
0xd1e dec  r1
0xd1f mov  a,@r1
0xd20 cpl  a
0xd21 add  a,r4
0xd22 jc   $0D29
0xd24 mov  r2,#$9
0xd26 mov  a,@r1
0xd27 rrc  a
0xd28 mov  @r1,a
```

At the beginning of the above code, r1 contained 47h so the first instruction points r1 to 46h - the knock sensor value. We load the value into __a__, and subtract it from our scaled threshold. If the carry flag is set, then the knock sensor value was higher than the threshold, and we don't have knock, so we skip beyond this section. 

But if carry is not set, that means the that the sensor value was lower than the threshold, which we interpret as knock. At 0xD24, we load the value 9 into r2: *this represents a timing delay of 3 degrees*. We'll see r2 being used throughout the rest of the knock routine as a flag that indicates whether knock was detected or not. 

You can read an explanation of why the number 9 corresesponds to 3 degrees here: [Timing Delay Angles](timing_delay_angles.md). 

Next we do something a litle strange-looking: assuming we detected knock, we again load the knock sensor value from 46h, divide it by 2, and store it back into 46h. This is because 46h will be used a little later to calculate a new knock threshold for this cylinder, and that calulation actually takes account of whether knock was detected or not.

That's the end of the section that depends on the knock threshold - the next part always runs, regardless:

```asm
0xd29 mov  r0,#$73
0xd2b mov  r1,#$49
0xd2d mov  r3,#$4
0xd2f clr  f0
0xd30 cpl  f0
0xd31 call $0798    ;0xF98
```

The code above is where timing is restored. The value in 73h contains the timing delay from a previous cycle. This really has nothing to do with the knock detection we're performing *now*. It's just some housekeeping that needs to be done before we load the timing delay for the current knocking cylinder into 73h. 

The routine at 0xF98 checks if a counter (49h) has overflowed, and if so, it decrements the timing delay value in 73h and resets the timer. Since a value of 9 represents 3 degrees of timing delay, decrementing this value by 1 has the effect of restoring timing by approximately 1/3 of a degree. 

You can read a detailed breakdown of the routine at 0xF98 in the Appendix. It's not a very involved routine though so feel free to skip that - the important thing to note is that the decremented value from that routine is stored in the accumulator. 

Next we rotate the 4 timing delay values (one for each cylinder) to make sure that we're working on the correct cylinder:

```asm
0xd33 mov  r0,#$6F
0xd35 mov  r3,#$4
0xd37 inc  r0
0xd38 xch  a,@r0
0xd39 djnz r3,$0D37
```

The above code loops 4 times (controlled by r3) and each time it moves the values starting at 70h up by one location (70h goes into 71h, 71h into 72h etc.), with the recently decremented value from 73h (in the accumulator) going back to 70h. 

This is a key point to understanding the knock routine: the value in 73h before the above code ran was for an earlier cylinder; but __from this point onwards, the value in 73h contains the timing delay for the cylinder that fired most recently - the same one that we just checked for knock__. 

The next section involves the throttle angle value (in 3Ah):

```asm
0xd3b mov  r1,#$3A
0xd3d mov  a,@r1
0xd3e mov  r5,a
0xd3f add  a,#$F0
0xd41 jc   $0D4B
0xd43 mov  r1,#$33
0xd45 mov  a,@r1
0xd46 add  a,#$EF
0xd48 jnz  $0D4B
0xd4a mov  @r1,a
```

The above code first loads the throttle angle value 3Ah and stores it in r5 for later. Then it checks if 3Ah is at or below 15 (which equates to about 18% throttle), and if so, then it checks the blink code location (33h). If the value in 33h is 17, it gets set to 0. As you'll see later, 17 is not a real blink code - it's actually a special flag that's used to indicate that at least one cylinder has exceeded 6 degrees of timing retard. So this code resets that flag if the throttle position goes below ~18%. It's not a hugely significant step at this point, so don't worry about this flag until later. 

Next we do another comparison of the throttle angle:

```asm
0xd4b mov  r1,#$48
0xd4d mov  a,@r1
0xd4e cpl  a
0xd4f add  a,r5
```

The value in 48h is yet another one of the [rpm constants](rpm_constants.md). It has the value 32, 27 or 16 depending on rpm (higher rpm=lower values of 48h). 

Strangely, the result of this comparison (i.e. the carry flag) isn't checked immediately. Instead, the next part of the code deals with the knock circuitry *self-test*. You can read more about the self-test in the [knock hardware section](knock_hardware.md). For now, just take it that when the counter in 31h counts to 0, there's some code in the ADC routine that generates a fake knock signal, which is injected into the knock sensor's amplifier. If that signal was generated during the previous cycle, then we should now detect is as knock. If we don't detect it, then something is wrong with the circuit. 

The first part skips the whole self-test unless the counter 31h is ready:

```asm
0xd50 mov  r1,#$31
0xd52 mov  a,@r1
0xd53 mov  r7,a
0xd54 djnz r7,$0D74
```

Next, assuming 31h has reached zero, we reset it to 2, increment r2 (just so that we can test it with djnz), and load 34h with the value 6:

```asm
0xd56 mov  @r1,#$2
0xd58 inc  r2
0xd59 mov  a,#$6
0xd5b mov  r0,#$34
0xd5d xch  a,@r0
```

The value in 34h controls how many times the knock self-test can fail before we declare the KLR to be faulty. Here, we're exchanging the current value with 6, so that the accumulator gets the current value. If it turns out that it's just about to hit 0, then we've already reset it to 6 for next time, via the xch instruction. 

Next we test r2, which is being used as a flag to indicate if knock was just detected. Remember, we set it to 9 earlier if knock was detected; otherwise it was zero. Then we incremented it a moment ago so that the djnz instruction would leave it unchanged. If there was something in r2, we skip to 0xD62; otherwise we decrement the value we just loaded from 34h, and load it back into 34h:

```asm
0xd5e djnz r2,$0D62
0xd60 dec  a
0xd61 mov  @r0,a
```

Next, if the value from 34h has not reached 0, we skip to 0xD68. But if it has reached 0, that means we have run out of patience waiting for the KLR to detect it's own induced knock signal, and it's time to trigger a blink code!

```asm
0xd62 jnz  $0D68
0xd64 mov  r1,#$33
0xd66 mov  @r1,#$23
```

The values that go in the blink code location (33h) are *binary coded decimal* or BCD. To interpret them, you just take each of the 2 4-bit halves ( or *nibbles*) as digits. So, 23h is 35 decimal, which looks like this in binary:

```
0010 0011
```

So that equates to blink code __2 - 3__ "Control Unit Faulty" (from the [Porsche documentation](reference/DME_KLR_Test_Plan.pdf)). 

Now we're done with the self-test, and it's back to normal knock detection stuff. The first thing we do is rotate the cylinder knock threshold values:

```asm
0xd68 mov  r0,#$7B
0xd6a mov  a,@r0
0xd6b mov  r3,a
0xd6c dec  r0
0xd6d mov  a,@r0
0xd6e mov  r6,#$74
0xd70 call $07AB
```

Next comes a very important part: if we ran the self test this time, then any knock we detected is *fake*, and we must not do anything to try to "fix" it! Recall that if the test was skipped (due to the counter 31h not being ready) then we would have jumped to 0xD74. Otherwise, we'll hit the instruction at 0xD72 which skips a bit of code:

```asm
0xd72 jmp  $0589    ;0xD90
```

But the test only runs every few hundred ignition cyles, so we'll now assume that we didn't run the test this time, and so we don't skip anything here. 

So, next we finally consider the carry flag from the add way back at 0xD4F, where we compared the throttle angle to 16, 27 or 32 (which correspond to 20%, 33% or 40% throttle respectively). The particular value that's used depends on rpm. If the throttle angle is greater than this threshold, then the carry flag is set. Otherwise, we skip to 0xD7E. 

If the throttle angle threshold is met, we load our knock delay value into the accumulator, and if it's not zero, we set Port 1 bit 6 __low__. From the [pin assignments](pin_assignments.md) section we see that this is the Knocking YES/NO indicator. This pin is not explicitly reset though; it'll get reset when the trigger signal resets the 8048. That means that the pulse length will get shorter as rpm goes up, but it probably wasn't worth implementing a constant pulse length for this, since it's not even connected to anything in the car!

Next we add r2 to 73h, which you should recall is the timing delay value for the cylinder we're analyzing right now (r0 still points to 73h from the rotation loop at 0xD34). Note, we don't check if 73h already had a timing delay value. It could have already had any value from 0 up to the maximum. All we care about right now is that the cylinder we're considering produced a knock the most recent time it fired, so we're pulling 3 degrees of timing. Later, in another section of code, we check if any cylinder has exceeded the maximum of 6 degrees, and cap them all to 6 degrees if necessary. But that's actually done in a separate routine. 

```asm
0xd74 clr  a
0xd75 jnc  $0D7E
0xd77 mov  a,r2
0xd78 jz   $0D7C
0xd7a anl  p1,#$BF
0xd7c mov  a,@r0
0xd7d add  a,r2
0xd7e mov  @r0,a

```

The next bit calculates a new knock threshold for this cylinder and rotates it (like the rotation we did with 73h earlier):

```asm
0xd7f mov  r0,#$7A
0xd81 mov  r1,#$46
0xd83 mov  r6,#$74
0xd85 mov  r7,#$4
0xd87 call $07A9
```

To understand this, let's take a look at the code at 0x7A9. Of course, because we're in Bank 1, the address is really 0xFA9:

```asm
0xfa9 call $0608    ;0xE08
0xfab call $07B0    ;0xFB0 (look a few instructions below here)
0xfad call $07B0
0xfaf ret
0xfb0 xch  a,r6
0xfb1 mov  r0,a
0xfb2 xch  a,r6
0xfb3 xch  a,r3
0xfb4 mov  r7,#$4
0xfb6 xch  a,@r0
0xfb7 inc  r0
0xfb8 xch  a,@r0
0xfb9 inc  r0
0xfba djnz r7,$0FB6
0xfbc ret
```

In the code above I've commented the subroutine calls with their true Bank1 locations to make it clearer. 

The first call here (to 0xE08) is to the [exponential smoothing](exponential_smoothing.md) function. That function filters or smooths out any sudden changes in the threshold, so that only a consistent increase or decrease will have any effect. It's a bit too much to get into here, so you can read the linked section if you want to see the details of how that works. 

The next routine is called twice in succession, and its definition can be seen just after the __ret__ instruction. All this does is rotate the threshold values through 4 locations, just like we saw earlier with the timing delay values 70h - 73h. 

The rotate routine is called twice because the smoothing function works with 16-bit values. Rememeber at the beginning of this section, when I said that 7Ah contained the knock threshold for this cylinder? Well that wasn't the full story: in fact, the threshold was calculated as a 16-bit value, with the high byte in 7Ah and the low byte in 7Bh. Only the high byte is actually used as the threshold for comparison with the knock sensor signal, but the low byte has to be preserved to avoid rounding errors when calculating new thresholds. So the above rotation routine rotates 8 values through locations 74h to 7Bh. 

I won't get into that rotation code in as much detail as I usually do because I don't want to derail the discussion of the knock routine any more than necessary. Consider it an excercise for the reader if you need to see exactly how it works!

Next we use exactly the same routines again, to calculate (and rotate) a low-pass filtered version of 73h; this will be used to decide if we should pull boost or not:

```asm
0xd89 mov  r0,#$5E
0xd8b mov  r1,#$73
0xd8d mov  r6,#$58
0xd8f mov  r7,#$4
0xd91 call $07A9    ;0xFA9
```

Finally, we get to the section that deals with reducing boost if we have persistent knocking. 

I'll start this section by telling you that 57h is the boost reduction value. You can see this in action if you look at the code that reads the target boost from the map: that code is located at 0xA8E. After loading the map value, the value in 57h is immediately subtracted from the target before that routine returns. But we're getting ahead of ourselves; I just wanted you to know what 57h represents before we look into the next bit of the knock routine code:

```asm
0xd93 mov  r0,#$57
0xd95 mov  r1,#$2C
0xd97 mov  a,@r1
0xd98 anl  a,#$38
0xd9a mov  r4,a
0xd9b jnz  $0DA5
```

The value in 2Ch is a special counter that's incremented once per ignition cycle. It is used in various places, usually by dividing it by some number with an AND operation, to produce counters of various lower frequencies. In the trigger routine, 2C is always increased to the next multiple of 8 (0x100). So if you take all the multiples of 8, and AND them with 0x38 (56 decimal) as seen above, the result will be zero on every 8th count. Therefore, the AND at 0xD98 divides the 2C counter by 8. It stores the result in r4 for later, and then checks it it's 0. If it's not, we skip to 0xDA5. 

If the counter is 0 (which you now know happens once every 8 cycles), then we do the next bit:

```asm
0xd9d mov  r1,#$4F
0xd9f mov  r3,#$1
0xda1 cpl  f0
0xda2 call $0798
0xda4 mov  @r0,a
```

Recall that the flag f0 was set at 0xD30. Here it's complemented, so it's cleared. This flag will be used later to indicate whether the above code ran this time or not. The call to 0x798, we've seen before: that routine was used to decrement the timing delay value in 73h *if* the specified counter rolled over. Here it's being used to decrememnt 57h (which is the location that r0 points to now), but only if the counter in 4Fh indicates that it's time. Since we know that 57h is the boost reduction, clearly this code is responsible for restoring the boost we pulled, if enough time has passed. 

The counter 4F is initialized from location 50h, which is one of the [rpm constants](rpm_constants.md). It's set to range from 12 to 37 (low to high rpm). 

To summarize fo far, then, the map value in 50h is used as a counter that's effectively divided by 8, and when it finally overflows, we decrement the boost reduction value 57h, restoring a little bit of lost boost. But we haven't yet seen how much boost the number in 57h represents. I'll just tell you for now: a value of __1__ in this variable is about __0.8kpa__. 

Next we see yet another of the [rpm constants](rpm_constants.md) being used: 4Ch. This one is actually very strange. It's set to 128 for all rpm values, but that in itself is not too weird - we see that with other rpm constants. What's weird is the way the value is used in he following code:

```asm
0xda5 mov  r1,#$4C
0xda7 mov  a,@r1
0xda8 swap a
0xda9 cpl  a
0xdaa mov  r2,a
0xdab orl  a,#$F0
0xdad inc  a
0xdae mov  r1,#$58
0xdb0 add  a,@r1
```

So we take the value 128, __swap__ it, giving 8, complement that, giving 247 (which we store in r2 for later), then __OR__ that with 240, which results in no change to 247, then incrememt it to 248. 

Next we load the value from 58h and add it to our 248. The next section checks if the result of the add carried. 

```asm
0xdb1 jnc  $0DBA
0xdb3 jnz  $0DBA
```

The effect of these 2 checks is that we'll jump to 0xDBA if 58h was less than 8 (i.e. the complement of 248), and we'll also jump there if 58h was anything other than 8. So the next section of code (before 0xDBA will only run if 58h was exactly 8. The reason for this is that the code that's guarded by this check deals with the *low byte* of the filtered timing value, 59h. We don't care about the value in the low byte unless the high byte is exactly 8:

```asm
0xdb5 inc  r1
0xdb6 mov  a,r2
0xdb7 orl  a,#$F
0xdb9 add  a,@r1
```

Here we increment r1 to point to 59h, and we __OR__ the value in r2 (which is 247 from earlier) with 15, giving 255. Then we add that to 59h. Obviously this must result in a carry if 59h is anything other than zero, but if the original value 128 (from 4C) had been something else, then we could have bigger values in 59h without causing a carry. *Still, having experimented with other values for 4C, I find this approach strange and I'm not sure why all the swapping and ORing at 0xDA8 is necessary.*

Next there a little more counter stuff before we actually check that carry flag:

```asm
0xdba mov  r1,#$4D
0xdbc mov  a,@r1
0xdbd jf0  $0DC0
0xdbf inc  @r1
0xdc0 jnz  $0DCE
0xdc2 mov  @r1,a
0xdc3 jnc  $0DCE
```

So, here we're checking yet another counter, also initialized from one of the [rpm constants](rpm_constants.md) (this time 4Eh), and we only incrememt this counter if the flag f0 is clear. Recall from the start of this boost related section that f0 was cleared if the 2Ch counter was 0 (when ANDed with 56). That had the effect of dividing the boost restoration counter by 8, and it does the same thing here. If the flag is clear, we incrememt this 4Dh counter, and then we check if it's zero. Interestingly, the __jnz__ instruction operates on the accumulator, so we're checking the value from 0xDBC, *before* we incremented it. If it is zero at this point, we overwrite it with the value before the increment, and finally we check the carry flag from the __add__ way back at 0xDB0. 

Recall that this carry flag tells us whether the filtered timing delay value is higher than 8.0 or not. If the value we tested at 0xDB0 was exactly 8, then the carry is derived from the next __add__ instrution on the low byte at 0xDB9. 

So, in the code snippet above, if the carry is not set, that means that the 16-bit value in 58h/59h was less than or equal to 8.0, and so we will skip the boost reduction code that you're about to see.

But wait... *9* was the value that correseponded to 3 degrees! A value of 8 would be around 2.7 degrees or so. Why should that be the threshold value for reducing boost? Well, remember that 58h and 59h are the high and low bytes of the timing delay value, *after* it's passed through our [low-pass filter](exponential_smoothing.md), so it's a bit more complicated than a simple numeric comparison. In fact, if the timing value in 73h is exactly 8.0 then it will take many, many cycles for the code we're looking at now to "catch up" and add a boost reduction. During that time, if the cylinder in question stopped knocking, the timing would be restored, and we'd never exceed the threshold of 8.0 in this routine. The only way this routine will reduce boost is if at least one cylinder is knocking so persistently that even the low-pass filtered version of the timing retard is higher than 8.0. I wish I could tell you exactly what circumstances are required to trigger it, but it's just not that simple. All I can really say is that the value is filtered, and if you want to know more about it, you'll have to write some expereimental code in your favourite programming language to see how it behaves, or analyze it mathematically! (Indicentally, I scripted this function in Python and I can tell you it's behavior is exactly what we need). 

So, if our filtered value is above 8.0, we run the next bit of code, which actually sets a boost reduction:

```asm
0xdc5 mov  a,@r0
0xdc6 add  a,#$5
0xdc8 mov  @r0,a
0xdc9 inc  r1
0xdca mov  a,@r1
0xdcb cpl  a
0xdcc dec  r1
0xdcd mov  @r1,a
```

In the code above, r0 still points to 57h, and by adding __5__ to it, we're adding approximately __4kpa__ to the boost reduction value (recall that the value in 57h is always subtracted from the target boost value that's looked up from the map). 

The instructions after that just reset the 4Dh counter from 4E, which is one of the rpm constants I've mentioned so many times before. 

Next we cap the boost reduction to the value 77 (it's 4D in hex, but there's no connection between this value and the rpm constant in *location* 4D!):

```asm
0xdce mov  r2,#$4D
0xdd0 mov  a,@r0
0xdd1 cpl  a
0xdd2 add  a,r2
0xdd3 jc   $0DD7
0xdd5 mov  a,r2
0xdd6 mov  @r0,a
0xdd7 mov  r0,#$6B
0xdd9 mov  a,r4
0xdda clr  f0
0xddb cpl  f0
0xddc jmp  $0600    ;0xE00
```

The __add__ at 0xDD2 will carry if 57h is less than 77; in that case, we skip to 0xDD7. Otherwise, we store the value 77 into 57h. Now, since __1=0.8kpa__, 77 should be about __62kpa__, or __0.62__ bar. So basically the knock routine will eventually pull almost all your boost if the engine won't stop knocking!

Finally, after capping 57h, we load 6Bh into r0, r4 into a and set the f0 flag; these are all preparation for the next routine, which relates to boost control. But we'll have to leave that for another time. 

## Appendix: Tracking Individual Cylinders:

Now I mentioned a earlier that timing delay and threshold values are *rotated* to keep track of each cylinder individually. Now we'll get into that in detail. 

There are 2 variables that are tracked for each individual cylinder:

1. the required timing delay 

2. the knock threshold

It's worth mentioning why these 2 variables are tracked on a per-cylinder basis:

1. In order to reduce knocking, we have to pull timing *on the cylinder that was knocking*! You could just pull timing on all cylinders, but that would reduce power more than necessary. This system was designed to run close to the threshold of knock *constantly*, so it's important that it doesn't pull timing willy-nilly. 

2. All the cylinders make noise, and each one makes it's own unique noise. They don't all make the same *volume* of noise as each other; they get louder as rpm and load increase; and they're not even all the same distance from the knock sensor! So not only must we have separate thresholds for each cylinder, but those thresholds must adapt as the noise level changes (such as from increased rpm and/or load). 

So we keep track of the various per-cylinder values in the knock routine by rotating vaues through a list of adjacent memory locations. Here's what I mean by *rotating*: the 4 timing delay values are stored in locations 70h to 73h. Every time the knock routine runs, the value currently in 73h is placed in 70h; the value that *was* in 70h is moved into 71h; similarly, the value that was in 71h goes to 72h, and finally the value that was in 72h becomes the __new__ 73h. So it takes 4 engine cycles for a given cylinder's timing value to go from 73h back around to 73h again. 

Now the way that these rotated values are used is still somewhat complicated, because they get propagated through a few more locations during the trigger routine. So let's consider a knocking cylinder - we'll call it Cylinder *N* because it doesn't matter which number it is - and then we'll walk through a complete cycle, from knocking to ignition retard, tracking what the KLR does for Cylinder *N* at each stage. Note, however, that we'll only consider what's being done for *this one cylinder* at each stage; you have to remember that at each of these stages, the KLR is doing a different one of these steps for each of the *other* 3 cylinders - we'll just ignore those other cylinders here for the sake of clarity. 

Each of the following numbered points represents an ignition event; the steps in *italics* happen in the knock routine - the others happen elsewhere. The "Cylinder *N+m* part refers to the cylinder that will fire during this cycle, but for the most part I haven't bothered to specify whether each of the steps I've listed happens before or after the firing, unless it's really relevant. So here goes:

1. __Cylinder *N*__. Cylinder *N* knocks. In the ADC routine, near the end of the cycle, we read the knock value into 46h. 

2. __Cylinder *N+1*__. *In the knock routine, we check if an engine cycle counter has reached it's limit, and if so, restore 0.3 degrees of timing to the current 73h. But this value in 73h has nothing to do with __Cylinder N__; it's from a previous cycle, which we'll ignore for now! Still in Cycle 2, we next rotate the current value in 73h into 70h and make 72h the __new__ 73h; this new 73h corresponds to __Cylinder N__, so we process the knock sensor value (46h) that we read in cycle #1 and decide whether or not to add 3 degrees to this value of 73h. It might already contain 0, 3 or 6 degrees of timing delay; we don't check that at this point.*

3. __Cylinder *N+2*__. After the trigger routine, we use the angle value in 73h to calculate the timer values for ignition delay, which go into 28h/29h. *In the knock routine, the current value of 73h gets rotated back into 70h. This is fine, because we have just transferred the information from 73h into 28h/29h, and so we don't need this 73h again for a while.*

4. __Cylinder *N+3*__: In the trigger routine, we copy 29h into 21h. In the INT routine, we copy 21h into r3. *In the knock routine, 70h (which now corresponds __Cylinder N__) is promoted to 71h*

5. __Cylinder *N+4*__: Now we are back to the same cylinder that knocked in cycle 1! In the trigger routine, we copy 21h into 25h, which will be loaded into r2 in the INT routine, just before ignition is fired on this cycle. r3 has the same value as 21h/25h, which was loaded during the INT routine of the previous cycle. These values (r2 and r3) will be the dwell and ignition delays for *this* cycle. *In the knock routine, 71h is moved to 72h. On the next cycle, it will get moved into 73h, and will get an appropriate value depending on whether __this__ cycle caused knocking (in other words, a repeat of cycle #2)*

Phew! If all that talk about trigger routines, INT routines and so many memory locations and registers was unfamiliar, then you need to read the section on [ignition signal generation](ignition_signal.md). There's just too much in that to recap on it here. 

Still though, don't worry if you found the above steps confusing and hard to think about. That's probably normal. I don't think I can help by saying more about it; I'd probably just make it worse. Tracing your way through the code carefully is probably the way to go. Or you can just trust that the rotation works, and never think about it again!

## Appendix: Knock Threshold Scaling by RPM 

This is a detailed description of the threshold scaling routine that's called near the beginning of the knock routine. Here's the relevant knock routine code again:

```asm
0xd0b mov  r1,#$47
0xd0d mov  r2,#$0
0xd0f mov  a,@r0
0xd10 mov  r0,a
0xd11 mov  r4,a
0xd12 rlc  a
0xd13 call $07C1		;0xFC1
0xd15 call $07C1
0xd17 call $07BD		;0xFDB
0xd19 call $07BD
0xd1b mov  a,@r1
0xd1c swap a
0xd1d xchd a,@r1
```

First, the value from 7Ah is loaded into both r0 and the accumulator. 

Next, the threshold value in the accumulator is doubled (0xD12) and then the first routine is called. Now, trust me on this: __it's easier to understand this routine if you just pretend, for now, that the accumulator is zero__. At the end, we'll consider the effect of loading the accumulator with 7Ah, and it'll be really simple. 

The calls to 0x7C1 and 0x7BD are Bank 1, so the true addresses are 0xFC1 and 0xFDB respectively. They're really part of the same routine because 0x7DB leads into 0x7C1. The complete routine is below. 

```asm
0xfbd mov  a,r0    ;this is the second entry point (0x7BD)
0xfbe clr  c
0xfbf rrc  a
0xfc0 mov  r0,a
0xfc1 xch  a,@r1    ;this is the first entry point (0x07C1)
0xfc2 rlc  a
0xfc3 xch  a,@r1
0xfc4 jnc  $0FC9
0xfc6 add  a,r4
0xfc7 xch  a,r4
0xfc8 ret
0xfc9 mov  a,r0
0xfca ret
```

This routine works basically the same way as the classic shift+add routine used for multiplication in simple processors that don't have a multiply instruction. What makes it different is that the multiplier is a fraction!

The first entry point rotates the vaue from 47h to the left, and checks the carry flag. If we rotated out a zero, we just return without doing anything. If we rotated out a one then we add the value in a to our running total, r4. When the routine is called from the second entry point, we rotate the accumulator to the right, dividing it by 2. 

So effectively, we iterate over the leftmost 4 bits of 47h, and when there's a 1, we add a corresponding value to our running total. The values that correspond to the 4 bits are:

Bit| Value
---|------
0 | 2
1 | 1
2 | 1/2
3 | 1/4

What all this means is that the upper half (or upper *nibble*) of 47h represents a value from 0 to 4, in increments of 0.25. __But because we loaded our running total r4 with the original value from 7Ah first, we've ended up with 7Ah *plus* (7Ah*C), where C is the scaling coefficient.__ 

The final 2 instructions at 0xD1C just restore the lower nibble of 47h back to where it was (since we rotated it into the upper half for our multiplcation routine). I'm not sure why this done because this value doesn't appear to be used again anywhere. 

One final point: here are the actual values in 47h for the 8 rpm ranges (ranging from low to high rpm, left to right):

1 | 2 | 3 | 4 |  5| 6 | 7 | 8
--|---|---|---|---|---|---|----
68| 68| 85| 102| 102| 102| 102| 102|

So there's only 3 different values used. Since we want to understand what effect these values have in the above routine, let's take a look at the binary representation of the upper nibble of each one:

Decimal|Binary (upper half)
-------|-------------------
68| 0100
85| 0101
102| 0110

The first one has a 1 in the *1's* place and nothing else, so that will be multiplication by 1. The second one has a 1 in the *1's* place, and a 1 in the *1/4's* place, so that'll be multiplication by 1.25, and so on. 


## Appendix: Restoring Timing

TBD...

```asm
0xf98 inc  @r1
0xf99 mov  a,@r1
0xf9a jnz  $0FA1
0xf9c inc  r1
0xf9d mov  a,@r1
0xf9e cpl  a
0xf9f dec  r1
0xfa0 mov  @r1,a
0xfa1 add  a,r3
0xfa2 mov  a,@r0
0xfa3 jnc  $0FA8
0xfa5 jz   $0FA8
0xfa7 dec  a
0xfa8 ret
```

