# DME Software Architecture

The best way to think of the DME program is that is consists of two main parts: the main loop an the real-time part. These two parts work in a similar way to separate threads in a multithreaded OS. Of course there's no OS in the Motronic DME, but the the concept is similar. 

The real-time part is interrupt driven, with the crank sensors and timers as the interrupt sources. When the system is powered up, it enters the main loop, and when the crankshaft starts turning, the two sensors each create signals that interrupt the main loop. When this happens, the main loop is effectively paused while the interrupt routine runs. When the interrupt routine finishes, execution of the main loop resumes where it left off. This is a pretty standard architecture for real time embedded systems. Things that require precise timing happen in the real time, interrupt driven part, while things that require long calculations (that might take a variable length of time) happen in the main loop. The main loop just runs whenever there isn't currently an interrupt that needs to be handled. 

The reason it works this way should be fairly obvious: the engine needs dwell, spark and fuel injector signals at precise times on every revolution. Even if we're still in the middle of calculating updated fuel and timing values in the main loop, when the time comes, we need to generate those output signals no matter what. If the main loop had to take account of precise timing as well as calculating all the variables we need, that would make the code very complicated. With an interrupt driven design, each part can run more or less independently, which keeps the code as simple as possible. 

In our DME, roughly speaking the main loop calulates timing, fuel, and idle control variables, and the real-time part uses these values to create the actual signals. 

## Main loop
The main loop is located at 1F3A. The sequence of funciton calls, (with repititions removed), is

* diagnostics (101A)
* timer1 low stage (1F87)
  * read the ADC
  * [linearize the temp sensor readings](ntc_info.md) (02DD)
  * [update the software counters](dme_software_timers.md) (02EF)
  * [calculate the timing accel/decel adjustment](dme_acceleration_timing_damping.md) (030C)
  * [AFM transfer function/load calculation](dme_load_calculation.md) (0381)
  * [acceleration enrichment](dme_acceleration_enrichment_code_walkthrough.md) (1F8E)
  * [post fuel routine - injector latency/intialize fuel value 4B:4A](dme_fuel_enrichments_code_walkthrough.md) (040D)
  * diagnostics (0434)
  * [update overload timer](dme_fuel_cut_overview.md) (0C57)
  * [idle stabilizer routine](isv_routine.md) (0895) (this returns to the main loop).
* TPS processing/region code processing (1BC1)
* [timing calculation](dme_ignition_timing_calculation_overview.md), including fuel cuts (1C24)
* dwell calculation (07B7)
* [main fuel enrichments](dme_fuel_enrichments_overview.md) (temp, FQS etc.) (1D23)
  * [lambda](dme_lambda_overview.md) (1053)

Routine 1F87 from the main loop just checks if the ISV PWM signal is in the low period, and if so, calls 02C6 (while clearing the flag via ```jbc```). This results in this routine running once every roughly 11.5ms, as we'll see below. 

These links generally link to articles that explain the function at a high level without showing much actual code. But each one has a link to a detailed code walkthrough, except for a few where I felt it made more sense to combine the overview and code walkthrough into one. 

## Real time
There are four interrupt sources:

* external interrupt 0, aka ext0 (0003)
* external interrupt 1, aka ext1 (0013)
* timer 0 (000B)
* timer 1 (001B)

External interrupts 0 and 1 are driven by the reference and speed sensors respectively. Timer 0 is only used to turn the fuel injectors off (they're turned on just after the spark is fired in the external interrupt 1 routine), and Timer 1 controls the idle stabilizer PWM signal and measures engine speed. 

Timer 1 is configured to run at a frequency of approximiately 87Hz, giving a roughly 11.5ms period. This is a suitable frequency for the ISV and for running the "timer low stage" routines in the main loop. But the thing that drives this particular choice of frequency is that it results in a very convenient engine speed measurement. Engine speed is measured by counting the number of flywheel teeth that pass by the sensor within a single Timer 1 period. With the chosen frequency, this comes out to rpm/40. 

Now, the 951 has 132 flywheel teeth The 8v NA version of the car has 130. Why they are different is beyond me. But needless to say its very convenient to have both versions of the car use the same units of rpm/40, and for that reason the 951 and NA versions have slightly different Timer 1 frequencies. 

Unlike the functions called from the main loop, the various interrupt routines can't really be understood easily in isolation. Instead it's better to think of them working together like this: 

* there are four real time outputs that the DME produces (three in the case of the 8v NA cars):
  * dwell/spark signal
  * injector signal
  * ISV PWM signal
  * KLR trigger signal (951 only)
* ext0 detects the reference sensor pulse and synchronizes counters for the dwell, spark and KLR trigger signal
* ext1 does:
  * the actual counting: rpm measurement, ignition event countdown (dwell and spark) and KLR trigger countdown
  * the coil, injector and KLR trigger activation logic when the respective counters reach zero
  * various other transient adjustments to fuel, and timing that are best done in real time
* timer 0 only turns off the injectors
* timer 1 does:
  * storing and resetting the rpm counter
  * toggling the ISV PWM signal on/off

So in summary, dwell, spark, and KLR triggering are handled by ext1, injection is shared by ext1 and timer0, and ISV PWM is handled only by timer 1. Ext0 doesn't produce any outputs directly, but it's needed for the counter values that ext1 to be properly synchronized. 

I have covered the details of the real time part in these articles, which don't correspond to specific interrupt orutines, but rather to logical funciton:

* [crank sensor signal processing](dme_crank_sensor_hardware.md)
* [post ignition routine](dme_post_ignition_overview.md)

As usual each of these links to other relevant articles including detailed code walkthroughs. 
