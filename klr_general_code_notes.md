## KLR architecture outline

### Reset (pseudo ext interrupt)
* reset jumps to the trigger routine at 077.
* trigger routine jumps to 01B1 if rpm>=1500 (timing delay calculation)
* 01B1 jumps to 200 (blink code calculation)
* blink code __calls__ D00 (detect knock)
  * knock jumps to E00, boost control PID selector
	* E82 (PI) jumps to F00, CV, returns to blink code
	* DDE (filter target boost) returns to blink code
	* E30 (D) returns via DF1 to blink code
* blink code calls 336 diagnostics
* blink code calls housekeeping function table via ret

### Housekeeping function table
* 020F(A0E) - throttle processing
* 028D (A8D) - read target boost map
* 0257 (A57) - calculate rpm map axis
* 0282 (A82) - read CV open loop map
* 029E (A9E) - calculate ADC angle tick counts
* 0100 (900) - read RPM maps
* 0012 (812) - sit in a tight loop forever

### External interrupt

### Timer interrupt
* handle ignition signal
* cycling value PWM signal
* call ADC function table

### ADC process
* check if it's time to do the knock self test
* generate the fake knock pulses if so
* read one of channels 0-3 (different each time)
* read knock sensor
* read MAP sensor
* latch TPS channel for trigger/reset routine to read
