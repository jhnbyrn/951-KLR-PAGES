# How the ADC is read

##Overview
The process of reading the ADC is more complicated in the KLR than in the DME. The reason for this is that it needs to be timed very carefully. Knock is most likely to happen within a window of around 10-70 degrees ATDC. The KLR's knock detection system integrates the sensor's output during a certain window within this range of angles, and that means that the system must begin the integration process at a fairly specific angle, and read the final value at some later specific angle. 

For convenience we'll call these angles:

* Angle #1 - the start of the knock window, where we turn on the sensor integrator circuit
* Angle #2 - the end of the knock window, where we read the value from the integrator

The other ADC channels are not really sensitive to timing in the same way, but since it's convenient to do all the ADC reading in one process, these other channels are read around the same time. 

The sequence goes like this:

1. at angle 1 we start the knock sensor integrator (~20-40 degrees ATDC)
2. at angle 2 we start reading the ADC (~40 degrees later):
  * one of channels 0-3 (different one each time)
  * knock sensor
  * MAP sensor
  * TPS sensor

(channels 0-3 are knock sensor noise level, battery voltage, __unused__ and TPS power supply, respectively.)

In the time between steps 1 and 2, we check the knock self-test counter, and do the test if the counter indicates that it's time.

So in summary, we need to (a) measure out the correct angle to start the process, and (b) carry out the sequence of steps that involve *possibly* performing the self test, and then the ADC read operations.

Neither of these steps are trivial. We'll look at them in detail separately. 

## How the anglular measurement works
The timer and its interrupt routine, combined with the trigger signal, provide the basic measurement mechanism. 

Every time the timer interrupt routine runs, it decrements the counter __r4__, bank 0 (after doing its other tasks). Thus __r4__ counts timer ticks, and by loading r4 with an appropriate value (in the trigger routine, which we know is ~71 deg. BTDC) we can measure approximate angles, based on when r4 reaches zero. I say *approximate* because the engine speed is changing all the time - this doesn't give us anything like the precision that the DME has for measuring angles, but it's good enough.

Of course, since the timer ticks are fixed at 87us, the number of ticks that corresponds to a given angle varies with engine speed. So we need to constantly use the current engine speed measurement to convert our desrired angles into timer ticks. 

The actual target angles for starting the sensor integration and then reading the value also vary a little by rpm, presumably because the characteristics of engine knock vary with rpm. For every trigger event, we load two the target angles for the current rpm into 2A and 2B. The angle in 2A is Angle #1 (where we start the integrator), and 2B is Angle #2 (relative to 2A) where we read the output. 

Because engine speed (in 24h) is measured in terms of timer ticks, and we need our counter variables to also be in timer ticks, *and* we know that trigger events are 180 degrees apart, the values in 2A and 2B can be understood simlply as fractions of 180 degrees. So for instance 155 means ```180 * (155/256) degrees```. Subtracting 71 from this gives us the corresponding angle ATDC. 

2A and 2B are each multiplied by engine speed 24h and the results are divied by 256 and stored in 22h and 23h respectively. These are the timer tick counts. In the trigger routine, __r4__ is initialized with 22h. 

## How the sequencing works
The way the ADC operation sequencing is achieved is by using a table of function pointers, located at 0x400. The timer routine calls __40B__ when our counter __r4__ reaches zero, and 40B cycles through the functions in the table - each time 40B is called, it jumps to the next function in the table. 

Recall that the first value loaded into __r4__ represents the Angle #1, the start of the knock window. By default the timer routine reloads the tick counter __r4__ with __2__ just before calling 40B. That means we'll call 40B again after another 2 timer ticks, unless something in 40B overrides this value in r4. Function #4 does exactly that - (the last one before the actual ADC read) - it overrides r4 with the tick count value for Angle #2 (calculated earlier and stored in 23h). 


The functions in the table are:

time interval | function # | purpose |
-----------|---------|
Angle #1 | 0 | start integrator, choose one of channels 0-3, latch first address, prepare knock sensor channel
2 ticks | 1 | generate fake knock pulse for test
2 ticks | 2 | generate fake knock pulse for test
2 ticks | 3 | generate fake knock pulse for test
2 ticks | 4 | finalize knock system test, override __r4__ with Angle #2
Angle #2 | 5 | read channel 0-3, latch knock sensor channel, prepare MAP channel
2 ticks | 6 | read knock sensor, latch MAP channel, prepare TPS channel
2 ticks | 7 | read MAP sensor, latch TPS channel

There's no function in the list for actually reading the TPS sensor. Instead this is read at the beginning of the trigger routine, but because of the way the address preparation and latching is staggered, it makes sense to think of it as part of the same over all process. 

Why does each of the ADC read functions do channel selection like this? The process of actually taking a reading from the ADC consists of a few fairly standard steps:

1. prepare the address, i.e. put the address on the bus (p1 bits 0-2)
2. latch the address (rising edge of ALE)
3. wait for the ADC to perform the conversion
4. read the result (via movx)

This is really the same process as the DME uses (it uses the same 0809 ADC chip) but in the DME code the code is simple, because it's all done in a single loop with a hard coded delay, and otherwise without any particular concern for precise timing. 

Here, the four steps are staggered accross the table functions, in the way described in the table above. 

The delay needed for the conversion comes from the timer ticks that we count via __r4__ between calls to the function table - the trick to this is that each ADC read function performs these three steps:

1. toggle ALE to latch the address currently on the bus
2. put the *next* address on the bus
3. read the current value (which corresponds to the address latched by the previous function)

So for example, function #0 latches of of the channels 0-3, and then puts channel 5 (knock sensor) on the bus. Function #5 then toggles ALE (thus latching the *knock sensor* address ch. 5), puts channel 4 on the bus (MAP sensor), and then finally reads the current conversion, which is the channel 0-3 that was latched back in function #0, and so on. 

In the KLR code the latching of the ALE pin is performed by pulling p1.3 high, then low again. The address presently on p1.0-p1.2 is latched by the ADC on the rising edge. The instruction sequence for this typically looks like this

```
0x4a2 orl  p1,#$8		;00001000 
0x4a4 anl  p1,#$F7		;11110111
```

But it's also possible to select the next channel address at the same time that we turn ALE off, like this

```
0x44d orl  p1,#$8		;00001000 ALE latch
0x44f anl  p1,#$F4		;11110100 (toggle ALE off and select Ch. #4)
```



 
