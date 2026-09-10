# How the ADC is read

The process of reading the ADC is more complicated in the KLR than in the DME. The main reason for this is that it needs to be timed very carefully. Knock is most likely to happen within a window of around 10-70 degrees ATDC. The KLR's knock detection system integrates the sensor's output during a certain window within this range of angles, and that means that the system must begin the integration process at a fairly specific angle, and read the final value at some later specific angle. 

For convenience we'll call these angles:

* Angle #1 - the start of the knock window, where we turn on the sensor integrator circuit
* Angle #2 - the end of the knock window, where we read the value from the integrator

The other ADC channels are not really sensitive to timing in the same way, but since it's convenient to do all the ADC reading in one process, these other channels are read around the same time. Additionally, some processing of raw values is mixed up with the real time aspect of reading the ADC, which contributes to the complexity. We'll see the details below. 

The sequence goes like this:

1. at angle 1 we start the knock sensor integrator (~20-40 degrees ATDC)
2. at angle 2 we start reading the ADC (~40 degrees later):
  * one of channels 0-3 (different one each time)
  * knock sensor
  * MAP sensor
  * TPS sensor

(channels 0-3 are knock sensor noise level, battery voltage, __unused__ and TPS power supply, respectively.)

For quick reference, here's a table of the ADC channels and the locations used:

Channel| Pin| Purpose | RAM location
----|----|------------
0| 26| knock sensor noise level | 2F
1| 27| battery voltage | 3D
2| 28| unused | 6F
3| 1| TPS +v supply | 39
4| 2| MAP sensor | 52
5| 3| knock sensor integrator | 46 
6| 4| unused, not read | 
7| 5| TPS angle | 3C

In the time between steps 1 and 2, we check the knock self-test counter, and do the test if the counter indicates that it's time.

So in summary, we need to:

* measure out the correct angle to start the process
* carry out the sequence of steps that involve *possibly* performing the self test, and then the ADC read operations.

Neither of these tasks are trivial. Next, we'll look at them in detail, separately. 

## How the anglular measurement works
The timer and its interrupt routine, combined with the trigger signal, provide the basic measurement mechanism for angles. 

Every time the timer interrupt routine runs, it decrements the counter __r4__, bank 0 (at location __63__, after doing its other tasks). Thus r4 counts timer ticks, and by loading r4 with an appropriate value (in the trigger routine, which we know is ~71 deg. BTDC) we can measure approximate angles, based on when r4 reaches zero. I say *approximate* because the engine speed is changing all the time - this doesn't give us anything like the precision that the DME has for measuring angles, but it's good enough.

Of course, since the timer ticks are fixed at 87us, the number of ticks that corresponds to a given angle varies with engine speed. So we need to constantly use the current engine speed measurement to convert our desrired angles into timer ticks. 

The actual target angles for starting the sensor integration and then reading the value also vary a little by rpm, presumably because the characteristics of engine knock vary with rpm. For every trigger event, we load two the target angles for the current rpm into 2A and 2B. The angle in 2A is Angle #1 (where we start the integrator), and 2B is Angle #2 (relative to 2A) where we read the output. 

The target angles are stored in the rpm maps at _900_ - here are the relevant maps for 2A and 2B:

RPM range/Value | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 
-------------------|---|---|---|---|---|---|---|---|
2A |  155 | 155 | 149 | 146 | 145 | 138 | 131 | 127
2B | 61 | 49 | 48 | 48 | 48 | 48 | 48 | 55
 
Because engine our basic engine speed measurement (in 24h) is measured in terms of timer ticks, and we need our counter variables to also be in timer ticks, *and* we know that trigger events are 180 degrees apart, the values in 2A and 2B can be understood simlply as fractions of 180 degrees. So for instance 155 means ```180 * (155/256) degrees```. Subtracting 71 from this gives us the corresponding angle ATDC. 

At __A9E__, 2A and 2B are each multiplied by engine speed 24h and the results are divied by 256 and stored in 22h and 23h respectively. These are the timer tick counts. In the trigger routine, __r4__ is initialized with 22h. 

Here's a table of the angles we end up with, based on the rpm ranges above (note that Angle #1 is ATDC but Angle #2 is relative to Angle #1):

| RPM range/Angle | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| 2A (Angle #1 degrees ATDC) | 38 | 38 | 34 | 32 | 31 | 26 | 21 | 18 |
| 2B (Angle #2 degrees after #1) | 43 | 34 | 34 | 34 | 34 | 34 | 34 | 38 |


## How the sequencing works
The way the ADC operation sequencing is achieved is by using a table of function pointers, located at __400__. The index to this function table is __2C__. When our main counter r4 reaches zero in the timer routine, we increment 2C and call __40B__. 

Thus 40B cycles through the functions in the table - each time it's called, it jumps to the next function in the table. 

Recall that the first value loaded into r4 represents the Angle #1, the start of the knock window. By default the timer routine reloads the tick counter r4 with __2__ just before calling 40B. That means we'll call 40B again after another 2 timer ticks, unless something in 40B overrides this value in r4. Function #4 does exactly that - (the last one before the actual ADC read) - it overrides r4 with the tick count value for Angle #2 (calculated earlier and stored in 23h). 


The functions in the table are:

time interval | function # | address offset | purpose |
-----------|---------|
Angle #1 | 0 | 0E | start integrator, choose one of channels 0-3, latch first address, prepare knock sensor channel
2 ticks | 1 | 3C | generate fake knock pulse for test
2 ticks | 2 | 3C | generate fake knock pulse for test
2 ticks | 3 | 3C | generate fake knock pulse for test
2 ticks | 4 | 47 | finalize knock system test, override __r4__ with Angle #2
Angle #2 | 5 | 4C | read channel 0-3, latch knock sensor channel, prepare MAP channel
2 ticks | 6 | 8C | read knock sensor, latch MAP channel, prepare TPS channel
2 ticks | 7 | 98 | read MAP sensor, latch TPS channel

There's no function in the list for actually reading the TPS sensor. Instead this is read at the beginning of the trigger routine, but because of the way the address preparation and latching is staggered, it makes sense to think of it as part of the same over all process. 

The process of actually taking a reading from the ADC consists of a few fairly standard steps:

1. prepare the address, i.e. put the address on the bus (p1 bits 0-2)
2. latch the address (rising edge of ALE)
3. wait for the ADC to perform the conversion
4. read the result (via movx)

This is really the same process as the DME uses (it uses the same 0809 ADC chip) but in the DME code the code is simple, because it's all done in a single loop with a hard coded delay, and otherwise without any particular concern for precise timing. 

Here, the four steps are staggered accross the various table functions. Here's some more detail on these steps:

The delay needed for the conversion comes from the timer ticks that we count via __r4__ between calls to the function table - the trick to this is that each ADC read function performs these three steps:

1. toggle ALE to latch the address currently on the bus
2. put the *next* address on the bus
3. read the current value (which corresponds to the address latched by the previous function)

So for example, function #0 latches one of the channels 0-3, and then puts channel 5 (knock sensor) on the bus. Function #5 then reads the value from channel 0-3, toggles ALE (thus latching the *knock sensor* address ch. 5), and puts channel 4 on the bus (MAP sensor). This process is repeated for each channel that's read. 

In the KLR code, the latching of the ALE pin is performed by pulling p1.3 high, then low again. The address presently on p1.0-p1.2 is latched by the ADC on the rising edge. The instruction sequence for this typically looks like this

```
0x4a2 orl  p1,#$8		;00001000 
0x4a4 anl  p1,#$F7		;11110111
```

But it's also possible to select the next channel address at the same time that we turn ALE off, like this

```
0x44d orl  p1,#$8		;00001000 ALE latch
0x44f anl  p1,#$F4		;11110100 (toggle ALE off and select Ch. #4)
```

Each of the individual ADC reading functions stores the value read from the ADC in its appropriate location in addition to handling the addressing and latching just described - but many of them do some extra processing before storing the value and returning. 

## Functions

The function table is looked up via

```
0x40b anl  a,#$7
0x40d jmpp @a
```

The anl instruction masks all but the lowest 3 bits. This means we're taking 2C *mod 8* - it can count freely forever but the value we get here will always just cycle through 0-7. The next instruction jumps to the location pointed to by __a__, *relative* to the start of the page, which means 400h plus the byte value from the function table. 

### Function 0 (40E) - start integrator and select first channel
```
0x40e anl  p1,#$F7		;11110111
0x410 mov  a,@r0
0x411 dec  a			;a=current function
0x412 jz   $041C
0x414 anl  p1,#$F3		;1111 0011 select ch. 3
0x416 jb4  $041A
0x418 anl  p1,#$F5		;1111 0101 clear p1.1 (selects ch. 1)
0x41a jb3  $041E
0x41c anl  p1,#$F6		;1111 0110 clear p1.0 (selects 0 or 2)
0x41e orl  p2,#$20		;0010 0000 (p2.5 knock sensor integrator)
0x420 orl  p1,#$8		;0000 1000 ADC ALE (latch the current addr)
0x422 anl  p1,#$F5		;1111 0101
0x424 orl  p1,#$5		;0000 0101
0x426 ret
```

This can be quite tricky to read. It's not doing anything very complicated. Register r0 points to 2C at this point, which was incremented before we got here, so we just decrement it to get the value that corresponds to this iteration. 

If it's zero then we select channel 6 which I don't think is used. But 2C is a free counter and usually isn't zero. So next we do a clever sequence of masking that tests bits 3 and 4 of 2C and selects channels 0, 1, 2 or 3 accordingly. It's hard to visualize but the effect of this is to select each one for 8 counts, then the next one. That means that if we start with channel 0, this code will switch to channel 1 after 8 iterations, which corresponds to the next ignition event (since there are 8 functions in the table and each one gets called for each ignition event, with 2C incremented each time). 

So to summarize, every ignition event, we'll pick the next channel in the sequence 0-3. Thus these channels are the lowest piority, each one being read every 4 cycles, while the others are read every cycle. 

After this we latch the address via ALE - this begins the ADC conversion process and the address bus is now free, so we put channel 5 on the bus (knock sensor). The next function after the self-test functions will read the channel 0-3 value and also latch the address on the bus (channel 5/knock sensor). 

### Functions 1-3 (43C) - generate fake knock signal

After the initial set up where the intergrator is turned on, this function is called three times in a row, at intervals of 2 timer ticks. 

```
0x43c add  a,#$7		;a points to the adc function number
0x43e movp a,@a			;99 8f 00 (153, 143, 0)
0x43f mov  r0,#$2F
0x441 add  a,@r0
0x442 jc   $044B		;jump if 2F > 103, 113, and itself
0x444 mov  r0,#$31
0x446 mov  a,@r0
0x447 jnz  $044B
0x449 anl  p1,#$7F		;01111111 - fake knock signal off
0x44b ret
```

On each call, it checks the current knock sensor noise level against one of three thresholds, and toggles the fake knock output off if the noise is above the threshold (2F is inverted, so lower values mean more background noise). 

The third threshold is simply the 2F value itself, meaning that the third pulse is always generated. Thus we have one, two or three pulses, depending on noise level, with the maximum number of pulses for the noisiest case. 

The idea seems to be that the quiter the background noise is (as measured by the knock sensor) the more sensitive we expect the knock detection circuitry and logic to be. 

### Function 4 (47) - finalize knock test
```
0x427 mov  r0,#$23		;ADC read angle counter
0x429 mov  a,@r0
0x42a mov  r4,a			;r4 controls when we call the ADC routine from the timer
0x42b mov  r0,#$2F
0x42d mov  a,@r0
0x42e add  a,#$C0		;192
0x430 mov  r0,#$31
0x432 jc   $0446		;jump if 2F >= 64
0x434 mov  a,@r0
0x435 jb2  $0438
0x437 ret
0x438 anl  a,#$7		;00000111 ch. 7 TPS angle
0x43a mov  @r0,a		;limit 31h to 7?
0x43b ret
```
First we set our tick counter r4 to Angle #2 - that controls when we will call the next function, which is where the actual ADC reads begin. 

Next, if the noise level 2F is > 64, we add one more fake knock pulse. If the noise level was <= 64, then we would normally get three pulses from the first function, __3C__. For lower noise levels, we could get as few as one pulse from that function, but in that case we're guaranteed to get another one from here. 

If we don't add that pulse, we check if the self-test countdown variable 31h has bit 2 set, and if so we mask it to 7 or les before returning. TODO - investigate why. 

### Function 5 (4C) - read channels 0-3
Here we read one of these low priority channels. 

First we read the value, then determine which channel it was using the same logic we used in Function 0 to select the channel (i.e. via bits 3 and 4 of the function table index, 2C):

```
0x44c movx a,@r0
0x44d orl  p1,#$8		;00001000 ALE latch
0x44f anl  p1,#$F4		;11110100 (ALE toggle and select #4 MAP)
0x451 xch  a,@r0
0x452 jb4  $0480
0x454 jb3  $047B
```
At this point, __r0__ points to __2C__ our table index. We swap it into __a__ temporarily. 

If both bits are clear, that means Function 0 would have selected channel 0, so we have just read the knock sensor noise level input. 

Let's look at how that channel is processed first:

```
0x456 xch  a,@r0        ;this undoes the previous xch above
0x457 mov  r1,a
0x458 mov  a,@r0
0x459 xrl  a,#$6
0x45b mov  r0,#$2F		;knock sensor noise
0x45d jz   $0476
0x45f mov  a,#$C0
0x461 add  a,r1
0x462 jnc  $0478
0x464 mov  a,r1
0x465 mov  @r0,a
0x466 mov  r1,#$34
0x468 mov  a,@r1
0x469 add  a,#$FA
0x46b jz   $0475
0x46d cpl  a
0x46e jz   $0472
0x470 mov  a,#$FC
0x472 add  a,#$69
0x474 mov  @r0,a
0x475 ret
0x476 mov  r0,#$2D
0x478 mov  a,r1
0x479 mov  @r0,a
0x47a ret
```

We'll look at the simplest cases first. 

We check if 2C is *exactly* 6 via xrl, and if so, we store our new value in __2D__ and return. As far as I can tell, this is never used. But 2C is a free counter - any time we get to this function, we know that it's value must be 6 *mod 8*, but it's only exactly 6 once in every 256 counts. So this is probably some unused edge case or diagnostic thing. 

Next we check if the newly read value (now in r1) is < 64, and if so, store it in 2F and return. Recall that the input to this channel is inverted, so lower values mean more noise. 

If the value is >= 64, things get a little bit more complicated. The next steps actually override 2F with false values depending on the state of the self test. 

If there haven't been any self-test failures (i.e. if 34h = 6) then we return with the new reading stored in 2F. 

Otherwise, if there was exactly one failure (34h = 5), we set 2F to 105, and for higher failure counts, we set it to 101. 

In function #3 (3C), a value of 105 will cause *one* pulse to be dropped, reducing the intensity of the fake knock signal, thus raising the bar a little for the next self test. But a value of 101 will restore all three pulses, so the reasoning is a little unclear here. The threshold comparisons that function 3C uses are loaded from a table, which implies emperical testing and tuning. 

The remaining code is much simpler:

```
0x47b xch  a,@r0
0x47c mov  r0,#$2E		;battery voltage
0x47e mov  @r0,a
0x47f ret
0x480 jb3  $0487
0x482 xch  a,@r0
0x483 mov  r0,#$6F
0x485 nop
0x486 ret
0x487 xch  a,@r0
0x488 mov  r0,#$39		;TPS v+ ?
0x48a mov  @r0,a
0x48b ret
```
For the battery voltage case, we simply store the value into 2E and return. Measured value at ADC Ch. 1 with 10.2v input: 2.752v, i.e. ~140. 

If bit 3 of 2C is set then we jump to 487, and store the value in 39h - this is the TPS power supply. 

If bit 3 is not set, then we select Ch. 2 (pin 28) and store the value in 6F. But Ch. 2 is grounded on the KLR board. 

### Function 6 (8C) - read knock sensor integrator
Recall that we turned on the integrator back in Function 0 (0E), which was called when we had reached Angle #1. Then after the self-test functions, we loaed the counter with the tick count for Angle #2, and then began reading the channels. All this was to arrange for the knock signal accumulate during the proper window ATDC. 

```
0x48c movx a,@r0
0x48d orl  p1,#$8		;00001000
0x48f anl  p1,#$F7		;11110111
0x491 orl  p1,#$7		;00000111 select ch. 7 TPS
0x493 mov  r0,#$46
0x495 cpl  a
0x496 mov  @r0,a
0x497 ret
```
As usual we first read the value, then latch the address that was waiting on the bus (which was the MAP sensor Ch. 4, and then put the address for the *next* channel on the bus, to be latched by the next function. 

The rest is trivial - we complement the value and store it in __46h__. The knock sensor integrator produces in an inverted output, like the noise channel, so complementing it here puts it the right way around - bigger numbers mean a stronger knock signal. 


### Function 7 (98) read MAP sensor

```
0x498 mov  r0,#$52
0x49a movx a,@r0		;store ADC value into a (not 52h!)
0x49b add  a,#$A		;add 10 to the value from 52h
0x49d mov  r4,a			;r4 <- value from 52h + 10
0x49e cpl  a
0x49f add  a,@r0		;c=1 if a < 52h (previous reading)
0x4a0 mov  r0,#$6C		;used in blink code checking - we only check boost trigger boost codes if this is 0 
0x4a2 orl  p1,#$8		;00001000 
0x4a4 anl  p1,#$F7		;11110111 toggle ALE
0x4a6 jnc  $04B1		;c=0 if boost is increasing
0x4a8 mov  @r0,#$0		;here 6Ch is set to 0 which enables boost error code checking
0x4aa mov  r0,#$52
0x4ac mov  a,r4
0x4ad mov  @r0,a		;store the value from r4 into 52h
0x4ae mov  r4,#$FF		;r4 <- 255
0x4b0 ret
0x4b1 inc  @r0			;inc the value in 6Ch
0x4b2 mov  a,@r0
0x4b3 jb2  $04A8		;looks like we only enable error code checking every 4th read if boost is increasing.
0x4b5 mov  r4,#$FF
0x4b7 ret
```

After reading the raw value from the ADC into __a__, we do

```
a = a + 10
r4 = a
toggle ALE (latching the final address, Ch. 7 TPS)
if a <= 52h (previous value):
	6Ch = 0
	52h = r4 (new value)
	r4 = 255 (stop calling the ADC funciton table now)
	return
else:
	6Ch++
	if 6Ch >= 4:
		6Ch = 0
		52h = r4 (new value)
	return
 ```

Now 6C controls boost related error checking in the blink code routine - over and underboost checks are skipped if 6C=0. 

So in summary if boost is decreasing, we store the value and everything is normal. If increasing, then we only store the value and check for boost related errors every 4th read. 
