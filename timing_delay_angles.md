# Timing Delay Angles

The KLR must be able to delay ignition timing by a specific angle, but it doesn't have the ability to measure angles directly. The DME has the benefit of the crankshaft sensors, which allow it to measure out any angle by just counting the pulses from the speed sensor. But the KLR only gets the [trigger and ignition signals](signal_timing.md) and so it has to convert the required angle into a linear quantity that can be used as a counter. 


You may recall from the [ignition signal generation](ignition_signal.md) section that the required timing delay must be in the form of 2 counter values - a coarse value (which is used for the timer) and a fine value (which is used in a djnz loop). The unit of measurement for the coarse counter is just the timer period itself - [usually 87us](speed_measurement.md). The units for the fine counter are 2.7us, because that's the time it takes to run the djnz instruction that's used for the fine-counter loop.

Now we'll examine how these counter values are actually calculated form the timing delay angles. 

## The Code

The code is found at 0x1B1. It runs after the trigger routine,  and it's very simple:

```asm
0x1b1 sel  rb1
0x1b2 mov  r1,#$73
0x1b4 mov  a,@r1
0x1b5 mov  r1,#$3F
0x1b7 add  a,@r1
0x1b8 mov  r3,a
0x1b9 call $0300
```

Location 73h contains the angle that timing should be delayed by; this value is initialized by the [knock detection](knock_detection.md) routine, and at the end of this section we'll look at the actual values that are used. The purpose of 3Fh here is not so clear; I'm not sure what it's doing here. Clearly it's added to 73h, but it actually has to be zero normally, or else nothing would work out. 

The 0x300 routine that's called at 0x1B9 is just a multiply function that takes 2 8-bit numbers and gives a 16-bit product. The 2 numbers to be multipled are in registers r3 and r6; before this routine is called, r6 is loaded with the value from 24h, which is the [raw engine speed measurement](speed_measurement.md). The result of the multiplication is stored in __a__ (high byte) and r3 (low byte). 

Next, the high byte of the result is divided by 2 and stored in 29h:

```asm
0x1bb clr  c
0x1bc rrc  a
0x1bd mov  r1,#$29
0x1bf mov  @r1,a
```

Then the low byte of the result is divided by 2, and *then* divided by 16 (swap followed by AND with 15):

```asm
0x1c0 mov  a,r3
0x1c1 rrc  a
0x1c2 swap a
0x1c3 anl  a,#$F
0x1c5 dec  r1
0x1c6 mov  @r1,a
0x1c7 jmp  $0200
```

The dec instruction at 0x1C5 points r1 to 28h, and so we store our divided low byte in 28h. 

So really all we're doing is multiplying the desired timing retard angle by the raw engine speed measurement, and then doing a little bit of scaling on the final value. But next, let's look at what this does with some real values. 

## Some Examples

Let's say that 73h contained the number 1. Now we'll need to pick a speed value to test this code with; let's go with 114 (which represents about 3000rpm). 

Multiplying these together just gives 114 in the low byte, and 0 in the high byte. Since the low byte value is divided by 2 and then by 16, we can just divide it by 32, to get 3 (of course we're just rotating the bits to the right, so we're doinig integer division). 

So we end up with 0 in 29h, and 3 in 28h. (*A quick note about what happens to these values after this routine runs: in the next trigger routine, these values get copied into 21h and 20h respectively. In the next trigger routine after __that__, they get copied into 25h and 26h. Then 25h ends up in r2, and ultimately r2 and 26 are used as the coarse and fine counters for the delay in the [ignition signal](ignition_signal.md) generation routine. The reason for all this copying of values is to make sure that 4 ignition cylces have passed from the time a cylinder knocks to the time the delay is applied - that way, the delay is applied to the cylinder that knocked*)

Since we now have 0 for the course counter, and 3 for the fine counter, let's look at what angle this will delay the ignition by. 

Recall from the [ignition signal](ignition_signal.md) section that the fine counter is always multiplied by 2 at least once (then it's also doubled *again* as many times as necessary to account for the variable timer interval, r7). Then the final fine counter value controls a loop running the __djnz__ instruction (at 0x029). That instruction is 2 cycles long, which means it takes 2.7us each time. So, with a value of 3 in 28h, we'll have a delay of 16.2us (after doubling). Now, since we picked 3000rpm as our test value for engine speed, we know that the 180-degree ignition period is __10ms__. So the angle represented by 16.2us is just __180*(16.2/10000)__ which is approximately __0.3__. 

So a value of 1 in 73h produces an angle delay of about 0.3 degrees in the ignition signal routine! So it looks like we should need a value of 10 to get the 3 degree timing delay we want when a cylinder knocks.

So let's plug the number 10 in to this code and make sure:

10 * 114 = 1140, which means the high byte will be 4 (1023) and the low byte will be 117 (the balance of 1140 - 1023). From the code above, the high byte is divided by 2 (0x1BC) so that gives 2. The low byte is divided by 32, so that gives 3. So now we've got 2 for the coarse counter and 3 for the fine counter. 

Recall that the coarse counter is the number of timer intervals to wait before firing the ignition; the timer interval is 87us, so our high byte value of 2 gives 174us. Add the fine counter value of 16.2 (same as the previous example) and we end up with 190.2us. And __180*(190.2/10000) = 3.4__. So a value of 10 in 73h gives a delay of 3.4 degrees. 

Wait, what? Shouldn't that be 3 degrees? Well it turns out that there's some rounding going on with these calculation (remember the integer division of the low byte by 32?). And this means that as we count up from 1, we get some variation in the angle that's represented by each increment. It's not always exactly 0.3 degrees, and in fact it's usually a bit more. So it turns out that __9__ is the number you need to get a 3 degree delay. And that's why the knock detection routine adds the value 9 to location 73h when it detects knock!
