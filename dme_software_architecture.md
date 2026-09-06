# DME Software Architecture

The main loop is 1F3A. The sequence of funciton calls, with repititions removed, is

* diagnostics
* timer1 low stage (1F87)
* TPS processing
* timing calculation (including fuel cuts)
* dwell calculation
* main fuel enrichments (temp, FQS etc.)


Routine 1F87 from the main loop just checks if the ISV PWM signal is in the low period, and if so, calls 02C6 (while clearing the flag).

The sequence of stuff 02C6 does is:

* read the ADC
* linearize the temp sensor readings (02DD)
* update the software counters (02EF)
* calculate the timing accel/decel adjustment (030C)
* AFM transfer function/load calculation (0381)
* acceleration enrichment (1F8E)
* post fuel routine - injector latency/intialize fuel value 4B:4A (040D)
* diagnostics (0434)
* update overload timer (0C57)
* idle stabilizer routine (0895)

The idle stabilizer routine finally returns to the main loop. 

Note that 1F87 uses ```jbc``` on 22h.7, so we only do this list once per timer period. 
