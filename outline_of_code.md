# KLR Code Outline

__0x000 -  0x003__ -- prep for trigger routine. The rest is at 0x77

__0x003 -  0x006__ -- prep for INT interrupt. The rest is at 0x30E

__0x007 -  0x072__ -- timer interrupt

__0x003 -  0x108__ -- trigger/initialization

__0x109 -  0x???__ -- LED blinking (in the middle of trigger routine)

__0x??? -  0x1B0__ -- more trigger init

__0x1B1 -  0x1C7__ -- calcuate timing delay (using 73h + 3Fh)

__0x1C8 -  0x200__ -- nop

__0x200 -  0x29C__ -- calculate blink codes, store in 33h

__0x29C -  0x2B5__ -- call 0x500 (afterwards, manipulate stack for housekeeping function list at 0x800?)

__0x2B5 -  0x2FF__ -- nop

__0x300 -  0x20d__ -- generic 8x8 bit multiply (16-bit result)

__0x30E -  0x329__ -- INT routine

__0x32B -  0x335__ -- decrement error counters, set error code (33h)

__0x336 -  0x39D__ -- ? diagnostic output - possibly unused?

__0x39E -  0x3FB__ -- nop

__0x3FB -  0x3FF__ -- ? a few probably unused instructions

__0x400 -  0x408__ -- ADC function table

__0x409 -  0x40A__ -- constants for knock testing (comparison to 2Fh)

__0x40B -  0x40D__ -- jmpp to ADC function from table at 0x400 (offset 2Ch)

__0x40E -  0x426__ -- ADC function #1 - select address

__0x427 -  0x42B__ -- ADC function #3 - self-test

__0x43C -  0x44B__ -- ADC function #2 - sef-test (called 3 times)

__0x44C -  0x48B__ -- ADC function #4 - ADC read ch. 0-3

__0x48C -  0x497__ -- ADC funciton #5 - ADC read ch. 5 (KNOCK)

__0x498 -  0x4B7__ -- ADC function #6 - ADC read ch. 4 (MAP)

__0x4B8 -  0x7FF__ -- nop

__0x800 -  0x813__ -- misc. function list (housekeeping)

__0x814 -  0x8FF__ -- nop

__0x900 -  0x924__ -- read routine for rpm maps, and rpm/throttle PID gain map

__0x925 -  0x990__ -- rpm maps (various rpm-dependant constants)

__0x991 -  0x9B1__ -- rpm/throttle map for PID gain (value loaded into 6Bh)

__0x9B1 -  0x9FF__ -- nop

__0xA00 -  0xA0E__ -- rpm map axis

__0xA0F -  0x???__ -- ? unkown number of possibly unused opcodes before the next function begins

__0xA16 -  0xA56__ -- calculate 3Ah (throttle position)

__0xA57 -  0xA81__ -- read rpm axis value into 43h

__0xA82 -  0xA8C__ -- read CV feedforward map using rpm/throttle, into 68h

__0xA8D -  0xA9D__ -- read target boost using rpm/throttle, into 51h. Subtract 57h (knock-related boost reduction).

__0xA9E -  0xAAD__ -- calculate R4 counter values for ADC read angles

__0xAAE -  0xAFF__ -- nop

__0xB00 -  0xB7F__ -- CV feed-forward map (rpm/throttle)

__0xB80 -  0xB8A__ -- multiply @r0 by rpm value in 24h

__0xB8C -  0xB8C__ -- ? unkown jmp instruction

__0xB8D -  0xBFC__ -- nop

__0xBFD -  0xBFF__ -- ? unknown jmp

__0xC01 -  0xC7F__ -- target boost map (rpm/throttle)

__0xC80 -  0xCD4__ -- map read routine (map determined by f1)

__0xCD4 -  0xCFF__ -- nop

__0xD00 -  0xDDD__ -- knock detection, timing/boost retard, self-test

__0xDDE -  0xDF7__ -- part of PID (call the exponential smoothing function)

__0xDF7 -  0xDFF__ -- nop

__0xE00 -  0xE07__ -- boost control PID loop (controlled by 2Ch)

__0xE08 -  0xE2F__ -- exponential smoothing function

__0xE30 -  0xE81__ -- boost control PID (derivative term?)

__0xE82 -  0xEF5__ -- boost control PID (proportional & integral terms?)

__0xEF6 -  0xEF6__ -- call 0xF00

__0xEF8 -  0xEFF__ -- nop

__0xF00 -  0xFA8__ -- CV PWM calculation (PID output + CV feedforward; also cap timing delay at 6 deg.)

__0xFA9 -  0xFBC__ -- call exp. smoothing and rotate cylinder values for adaptive knock threshold

__0xFBD -  0xFD4__ -- calculate rpm-dependant coefficient for knock threshold (using map value 47h)

__0xFD5 -  0xFDE__ -- helper for PID output; cap CV on-time

__0xFDF -  0xFF4__ - nop

__0xFF5 -  0xFFF__ - ? a few possibly unused opcodes
