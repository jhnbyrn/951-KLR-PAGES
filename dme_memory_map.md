# DME memory map

This is a master list of the DME's variables, flags, constants and maps, compiled from the existing code walkthroughs. 


A note on completeness: this is built from the code that has actually been walked through so far, so it's a record of what's been worked out rather than a complete map of the DME's RAM. 

## Byte variables

These live in the 8051's internal RAM. Locations 10h-1Ah are mostly ADC results and map lookup results; the higher locations hold calculated state.

| Location | Purpose | Covered in |
|----------|---------|------------|
| 10h | raw AFM wiper value, from the ADC | [load](dme_load_code_walkthrough.md), [acceleration enrichment](dme_acceleration_enrichment_code_walkthrough.md) |
| 11h | system voltage, from the ADC | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 12h | intake air temperature (NTC I), from the ADC | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 13h | coolant temperature (NTC II), from the ADC | [NTC info](ntc_info.md), and most fuel and timing articles |
| 14h | altitude sensor / region coding input, from the ADC | see the flag setting logic below |
| 17h | FQS switch position, from the ADC | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 18h | lambda correction step, condition unchanged (Map 62 or 65) | [lambda](dme_lambda_code_walkthrough.md) |
| 19h | lambda correction step, changed to lean (Map 63 or 66) | [lambda](dme_lambda_code_walkthrough.md) |
| 1Ah | lambda correction step, changed to not-lean (Map 64 or 67) | [lambda](dme_lambda_code_walkthrough.md) |
| 1Bh | lambda correction factor, high byte | [lambda](dme_lambda_code_walkthrough.md) |
| 1Ch | lambda correction factor, low byte | [lambda](dme_lambda_code_walkthrough.md) |
| 2Bh | ignition event counter to the next dwell or spark, in whole teeth | [ignition timing](ignition_timing_code.md) |
| 2Ch | pre-calculated replacement for 2Bh, relative to the ref sensor | [ignition timing](ignition_timing_code.md) |
| 2Dh | KLR trigger counter, in whole teeth | [ignition timing](ignition_timing_code.md) |
| 2Eh | pre-calculated replacement for 2Dh, relative to the ref sensor | [ignition timing](ignition_timing_code.md) |
| 2Fh | dwell angle, in half-teeth | [ignition timing](ignition_timing_code.md) |
| 30h | dwell duration used by the speed sensor routine, in half-teeth | [ignition timing](ignition_timing_code.md) |
| 31h | current ignition advance, in half-teeth | [ignition timing](ignition_timing_code.md), [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 32h | target ignition advance | [post-ignition](dme_post_ignition_code_walkthrough.md), [fuel cut](dme_fuel_cut_code.md) |
| 33h | half-tooth count to the next TDC | [ignition timing](ignition_timing_code.md) |
| 34h | countdown to the next permitted ignition timing step | [post-ignition](dme_post_ignition_code_walkthrough.md), [fuel cut](dme_fuel_cut_code.md) |
| 35h | cylinder firing index (0 or 1) | [ignition timing](ignition_timing_code.md), [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 36h | speed sensor pulse counter, used for rpm measurement | [ignition timing](ignition_timing_code.md) |
| 37h | engine speed, in units of 40rpm | most articles |
| 3Ch | post-start enrichment (software counter, 414ms units) | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md), [software timers](dme_software_timers.md) |
| 3Dh | all-rpm acceleration enrichment (software counter, 58ms units) | [acceleration enrichment](dme_acceleration_enrichment_code_walkthrough.md), [software timers](dme_software_timers.md) |
| 3Eh | lambda timer (software counter, 11.5ms units) | [lambda](dme_lambda_code_walkthrough.md), [software timers](dme_software_timers.md) |
| 3Fh | lambda load threshold timer (software counter, 345ms units) | [lambda](dme_lambda_code_walkthrough.md), [software timers](dme_software_timers.md) |
| 41h | timer1 ISV on-time, high byte | [ISV routine](isv_routine.md) |
| 42h | timer1 ISV on-time, low byte | [ISV routine](isv_routine.md) |
| 44h | timer1 ISV off-time, low byte | [ISV routine](isv_routine.md) |
| 45h | timer1 ISV off-time, high byte | [ISV routine](isv_routine.md) |
| 46h | smoothed 24-bit load value, high byte | [load](dme_load_code_walkthrough.md) |
| 47h | smoothed 24-bit load value, middle byte | [load](dme_load_code_walkthrough.md) |
| 48h | smoothed 24-bit load value, low byte | [load](dme_load_code_walkthrough.md) |
| 49h | load, i.e. the high byte of the scaled base fuel pulse | [load](dme_load_code_walkthrough.md) |
| 4Ah | final fuel pulse, low byte (timer0 ticks of 2us) | [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 4Bh | final fuel pulse, high byte | [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 4Ch | low-rpm acceleration enrichment, added directly to the pulse | [acceleration enrichment](dme_acceleration_enrichment_code_walkthrough.md) |
| 4Dh | injection event counter, capped at 128 | [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 4Eh | accumulated fuel adjustment, low byte | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 4Fh | accumulated fuel adjustment, high byte | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 50h | count of outstanding left shifts (pending multiplications by 2) | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 51h | AFM history queue, most recent previous reading | [acceleration enrichment](dme_acceleration_enrichment_code_walkthrough.md) |
| 52h | AFM history queue, second previous reading | [acceleration enrichment](dme_acceleration_enrichment_code_walkthrough.md) |
| 53h | AFM history queue, third previous reading (~35ms old) | [acceleration enrichment](dme_acceleration_enrichment_code_walkthrough.md) |
| 54h | injector dead-time | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md), [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 55h | lagging rpm reference that chases 37h | [timing damping](dme_acceleration_timing_damping.md) |
| 56h | fractional accumulator controlling how fast 55h chases 37h | [timing damping](dme_acceleration_timing_damping.md) |
| 57h | acceleration/deceleration ignition timing adjustment | [timing damping](dme_acceleration_timing_damping.md), [ignition timing](ignition_timing_code.md) |
| 58h | overload timer | [fuel cut](dme_fuel_cut_code.md) |
| 59h | prescale counter for 58h | [fuel cut](dme_fuel_cut_code.md) |
| 7Bh | high byte of the doubled ISV correction | [ISV routine](isv_routine.md) |
| 7Ch | ISV flare hold counter | [ISV routine](isv_routine.md) |
| 7Dh | ISV integral term, low byte | [ISV routine](isv_routine.md) |
| 7Eh | ISV integral term, high byte | [ISV routine](isv_routine.md) |
| 7Fh | ISV target idle rpm | [ISV routine](isv_routine.md) |

## Bit flags

### 20h - ISV control and lambda enable

| Flag | Meaning | Covered in |
|------|---------|------------|
| 20h.0 | ISV flare variant: 0 = return to idle, 1 = startup | [ISV routine](isv_routine.md) |
| 20h.2 | ISV idle rpm error sign: 1 = rpm too high, 0 = rpm too low | [ISV routine](isv_routine.md) |
| 20h.2 | *reused for lambda:* current condition, 0 = lean, 1 = not lean | [lambda](dme_lambda_code_walkthrough.md) |
| 20h.3 | blocks integration when a positive ISV correction is clamped | [ISV routine](isv_routine.md) |
| 20h.4 | blocks integration when a negative ISV correction is clamped, or when load is below the Map 87 value | [ISV routine](isv_routine.md) |
| 20h.5 | ISV PWM correction overflow sign (which way to clamp) | [ISV routine](isv_routine.md) |
| 20h.6 | an idle flare is needed on return to idle | [ISV routine](isv_routine.md) |
| 20h.7 | master enable for closed loop lambda control; only set on US (cat/O2) cars | [lambda](dme_lambda_code_walkthrough.md) |

Bits 20h.0 to 20h.6 are local logic flags for ISV closed loop control, and some of them are reused by the lambda code.

### 21h - fuel cut, enrichment latches, injector state

| Flag | Meaning | Covered in |
|------|---------|------------|
| 21h.0 | the ~3 second overload pre-timer is running | [fuel cut](dme_fuel_cut_code.md) |
| 21h.1 | overload confirmed; the ~60 second lockout is running | [fuel cut](dme_fuel_cut_code.md) |
| 21h.2 | injectors are currently on | [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 21h.4 | latch marking that the cranking enrichment phase-out has started | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 21h.5 | transient fuel correction after reactivation is active | [fuel cut](dme_fuel_cut_code.md), [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 21h.6 | selects return-to-idle (Map 1140) vs return-to-throttle (Map 1150) | [fuel cut](dme_fuel_cut_code.md), [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 21h.7 | latch for a pending 4Ch acceleration enrichment pump shot | [acceleration enrichment](dme_acceleration_enrichment_code_walkthrough.md), [post-ignition](dme_post_ignition_code_walkthrough.md) |

### 22h - half-tooth corrections and timing change rate

| Flag | Meaning | Covered in |
|------|---------|------------|
| 22h.0 | half-tooth correction applied to the next ignition event | [ignition timing](ignition_timing_code.md) |
| 22h.1 | half-tooth rounding error left over from the 021D calculation | [ignition timing](ignition_timing_code.md) |
| 22h.3 | coil state to apply in the ref sensor routine (set = dwell off) | [ignition timing](ignition_timing_code.md) |
| 22h.4 | timing change rate select, lowest priority of the three | [post-ignition](dme_post_ignition_code_walkthrough.md), [fuel cut](dme_fuel_cut_code.md) |
| 22h.5 | timing change rate select, medium priority | [post-ignition](dme_post_ignition_code_walkthrough.md), [fuel cut](dme_fuel_cut_code.md) |
| 22h.6 | timing change rate select, highest priority | [post-ignition](dme_post_ignition_code_walkthrough.md), [fuel cut](dme_fuel_cut_code.md) |

### 23h - engine operating mode

| Flag | Meaning | Covered in |
|------|---------|------------|
| 23h.0 | TPS at idle (1 = at idle) | [ISV routine](isv_routine.md), and most fuel articles |
| 23h.1 | WOT (1 = WOT). Controlled by the KLR, which calls > 65 deg. WOT | [ISV routine](isv_routine.md), [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 23h.2 | cranking (1 = rpm below 160). Cleared at a temperature-dependent threshold from Map 3 | see the flag setting logic below |
| 23h.3 | ISV alternate code path, set via ADC channel 5 (DME pin 28) | [ISV routine](isv_routine.md) |
| 23h.4 | startup | [lambda](dme_lambda_code_walkthrough.md), [timing damping](dme_acceleration_timing_damping.md), [fuel cut](dme_fuel_cut_code.md) |
| 23h.5 | fuel cut, for coasting or overload | [fuel cut](dme_fuel_cut_code.md) |
| 23h.6 | *unidentified* — appears at 040D in the post-load routine | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |

### 24h - lambda control state

| Flag | Meaning | Covered in |
|------|---------|------------|
| 24h.0 | lambda watchdog enable; always set in the production code | [lambda](dme_lambda_code_walkthrough.md) |
| 24h.1 | the load threshold timer (3Fh) is running | [lambda](dme_lambda_code_walkthrough.md) |
| 24h.2 | watchdog countdown active; never set by reachable code | [lambda](dme_lambda_code_walkthrough.md) |
| 24h.3 | the lambda-neutral timer phase is running | [lambda](dme_lambda_code_walkthrough.md) |
| 24h.4 | the rich/lean timer phase is running | [lambda](dme_lambda_code_walkthrough.md) |
| 24h.5 | all lambda threshold conditions are met (1 = correction permitted) | [lambda](dme_lambda_code_walkthrough.md) |
| 24h.6 | previous value of 20h.2: 0 = previously lean, 1 = previously not lean | [lambda](dme_lambda_code_walkthrough.md) |
| 24h.7 | the current condition has persisted long enough to act on | [lambda](dme_lambda_code_walkthrough.md) |

### 25h - cranking temperature, region and altitude coding

| Flag | Meaning | Covered in |
|------|---------|------------|
| 25h.4 | NTC II was below ~14.7C while cranking; selects the lambda enable temperature | [lambda](dme_lambda_code_walkthrough.md) |
| 25h.5 | NTC II was below ~14.7C while cranking; selects between warmup maps 43 and 45 | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 25h.6 | region coding: 0 = US, 1 = RoW | see the flag setting logic below |
| 25h.7 | altitude sensor: 1 = above 1000M | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |

Both 25h.4 and 25h.5 are set during cranking against the same threshold (~14.7C), from two separate constants at 11CDh and 11CFh. They're only set at all when 20h.7 is set, i.e. on US cars.

### Port and SFR bits

| Bit | Meaning | Covered in |
|-----|---------|------------|
| p1.0 | fuel injector output (low = injectors on) | [post-ignition](dme_post_ignition_code_walkthrough.md) |
| p1.1 | ignition signal output (low = coil on) | [ignition timing](ignition_timing_code.md) |
| p1.6 | O2 sensor comparator, rich | [lambda](dme_lambda_code_walkthrough.md) |
| p1.7 | O2 sensor comparator, lean | [lambda](dme_lambda_code_walkthrough.md) |
| t0 | code plug input, selects lambda Maps 62-64 vs 65-67 | [lambda](dme_lambda_code_walkthrough.md) |
| int1 / ie1 | speed sensor pin state and edge flag | [ignition timing](ignition_timing_code.md) |
| ie0 / ex0 / ex1 | ref sensor edge flag and the two external interrupt enables | [ignition timing](ignition_timing_code.md) |

## Constants

Almost all of the DME's scalar constants live in a block starting at 1160h, and the code reaches them by loading 1160h into dptr and using a one-byte offset. Both forms are given below.

| Offset | Address | Value | Purpose | Covered in |
|--------|---------|-------|---------|------------|
| 00h | 1160h | 44 | ref sensor position in half-teeth (60 deg. BTDC on the 951) | [ignition timing](ignition_timing_code.md) |
| 01h | 1161h | 2 | ignition events per revolution; also used by the cranking load path | [post-ignition](dme_post_ignition_code_walkthrough.md), [load](dme_load_code_walkthrough.md) |
| 02h | 1162h | 252 | initial value for the KLR trigger counter 2Eh | [ignition timing](ignition_timing_code.md) |
| 03h-04h | 1163h-1164h | 66 | half-teeth added to the KLR counter for the next cylinder | [ignition timing](ignition_timing_code.md) |
| 07h-08h | 1167h-1168h | 132 | 180 degrees in half-teeth | [ignition timing](ignition_timing_code.md) |
| 0Bh-0Ch | 116Bh-116Ch | 5681 | timer1 ticks in one complete ISV PWM period | [ISV routine](isv_routine.md) |
| 10h | 1170h | 4 | rpm threshold for setting the cranking flag (160rpm) | see the flag setting logic below |
| 11h | 1171h | 162 | rev limit (6480rpm) | [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 12h | 1172h | | fixed load value used while cranking | [load](dme_load_code_walkthrough.md) |
| 13h | 1173h | | minimum clamp for the transformed load (x25 = 425) | [load](dme_load_code_walkthrough.md) |
| 14h | 1174h | | maximum clamp for the transformed load (x25 = 5500) | [load](dme_load_code_walkthrough.md) |
| 15h | 1175h | 8 | gain applied to the rpm delta in the timing damping routine | [timing damping](dme_acceleration_timing_damping.md) |
| 16h | 1176h | 1 | retard step written to 57h when rpm is rising | [timing damping](dme_acceleration_timing_damping.md) |
| 17h | 1177h | FFh | advance step written to 57h when rpm is falling (-1) | [timing damping](dme_acceleration_timing_damping.md) |
| 18h | 1178h | 40h | rpm ceiling for timing damping (2560rpm) | [timing damping](dme_acceleration_timing_damping.md) |
| 19h | 1179h | 5Ah | load ceiling for timing damping (90) | [timing damping](dme_acceleration_timing_damping.md) |
| 1Ah | 117Ah | 12 | injection count threshold for the cranking enrichment phase-out | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 1Bh-1Eh | 117Bh-117Eh | 128, 132, 124, 136 | fuel offset per FQS position | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 1Fh | 117Fh | A2h | coolant threshold selecting Map 40 vs Map 41 (~65C) | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 25h | 1185h | 3Ch | load threshold for the fastest timing change rate (60) | [fuel cut](dme_fuel_cut_code.md) |
| 26h | 1186h | 14h | rpm threshold for the fastest timing change rate (800rpm) | [fuel cut](dme_fuel_cut_code.md) |
| 27h-28h | 1187h-1188h | 8, 1 | 34h reload and timing step limit, normal case | [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 29h-2Ah | 1189h-118Ah | 1, 8 | 34h reload and timing step limit, 22h.4 set | [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 2Bh-2Ch | 118Bh-118Ch | 1, 2 | 34h reload and timing step limit, 22h.5 set | [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 2Dh-2Eh | 118Dh-118Eh | 1, 1 | 34h reload and timing step limit, 22h.6 set | [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 2Fh | 118Fh | 249 | timing step on return-to-throttle reactivation (-6) | [fuel cut](dme_fuel_cut_code.md) |
| 30h | 1190h | FFh | timing step on return-to-idle reactivation (-1) | [fuel cut](dme_fuel_cut_code.md) |
| 31h | 1191h | 9 | coasting rpm offset, 21h.6 clear | [fuel cut](dme_fuel_cut_code.md) |
| 32h | 1192h | 9 | coasting rpm offset, 21h.6 set | [fuel cut](dme_fuel_cut_code.md) |
| 33h-36h | 1193h-1196h | 36, 5, 1, 30 | prescale values for software counters 3Ch, 3Dh, 3Eh, 3Fh | [software timers](dme_software_timers.md) |
| 37h | 1197h | 62 | rpm split between the two acceleration enrichment paths (2480rpm) | [acceleration enrichment](dme_acceleration_enrichment_code_walkthrough.md) |
| 38h | 1198h | 4 | idle rpm error threshold for resetting the ISV correction (160rpm) | [ISV routine](isv_routine.md) |
| 39h | 1199h | 15h | minimum idle rpm when AC is on, normal path (840rpm) | [ISV routine](isv_routine.md) |
| 3Ah | 119Ah | 18h | ISV PWM correction for AC-on, normal path (24) | [ISV routine](isv_routine.md) |
| 3Bh | 119Bh | 00h | ISV PWM correction for AC-on, alternate path (does nothing) | [ISV routine](isv_routine.md) |
| 3Ch | 119Ch | 17h | ISV PWM value for idle setting mode (~30% duty) | [ISV routine](isv_routine.md) |
| 3Dh | 119Dh | C0h | ISV correction positive limit (divide by 2, add 128) | [ISV routine](isv_routine.md) |
| 3Eh | 119Eh | 27h | ISV correction negative limit (divide by 2, complement, add 128) | [ISV routine](isv_routine.md) |
| 3Fh | 119Fh | 02h | flare hold counter value, coasting return to idle | [ISV routine](isv_routine.md) |
| 40h | 11A0h | 01h | flare hold counter value, startup | [ISV routine](isv_routine.md) |
| 41h | 11A1h | 8Ah | ISV PWM scaling factor (138/256 = ~0.54) | [ISV routine](isv_routine.md) |
| 42h | 11A2h | 42h | ISV PWM offset term (66/256 = ~0.25) | [ISV routine](isv_routine.md) |
| 43h | 11A3h | 66 | lambda timer reload, neutral phase (~760ms) | [lambda](dme_lambda_code_walkthrough.md) |
| 44h | 11A4h | 9 | lambda timer reload, rich/lean phase (~103ms) | [lambda](dme_lambda_code_walkthrough.md) |
| 45h | 11A5h | FFh | lambda watchdog timer value; 255 disables the watchdog | [lambda](dme_lambda_code_walkthrough.md) |
| 46h | 11A6h | 147 | lambda correction upper clamp (~1.15x) | [lambda](dme_lambda_code_walkthrough.md) |
| 47h | 11A7h | 90 | lambda correction lower clamp (~0.7x) | [lambda](dme_lambda_code_walkthrough.md) |
| 48h | 11A8h | 58h | lambda temperature threshold, not at idle (~16.7C) | [lambda](dme_lambda_code_walkthrough.md) |
| 49h | 11A9h | 58h | lambda temperature threshold, at idle (~16.7C) | [lambda](dme_lambda_code_walkthrough.md) |
| 4Ah | 11AAh | 7 | hysteresis added to the lambda temperature threshold (~4.6C) | [lambda](dme_lambda_code_walkthrough.md) |
| 4Bh | 11ABh | 8Eh | lambda upper rpm threshold (6640rpm) | [lambda](dme_lambda_code_walkthrough.md) |
| 4Ch | 11ACh | 66h | lambda load threshold (102) | [lambda](dme_lambda_code_walkthrough.md) |
| 4Dh | 11ADh | 6 | 3Fh reload for the lambda load threshold timer (~2s) | [lambda](dme_lambda_code_walkthrough.md) |
| 51h | 11B1h | 50 | hysteresis below the Map 68 threshold for staying in overload | [fuel cut](dme_fuel_cut_code.md) |
| 52h | 11B2h | 1Ah | 58h reload for the ~3 second overload pre-timer (26) | [fuel cut](dme_fuel_cut_code.md) |
| 53h | 11B3h | 29 | 58h reload for the ~60 second overload lockout | [fuel cut](dme_fuel_cut_code.md) |
| 54h | 11B4h | 10 | 59h prescale, 21h.1 clear | [fuel cut](dme_fuel_cut_code.md) |
| 55h | 11B5h | 180 | 59h prescale, 21h.1 set | [fuel cut](dme_fuel_cut_code.md) |
| 6Bh | 11CBh | 78h | altitude fuel correction applied when 25h.7 is set (120) | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 6Dh | 11CDh | 55h | coolant threshold for setting 25h.4 (~14.7C) | see the flag setting logic below |
| 6Eh | 11CEh | 8Ch | alternate lambda temperature threshold when 25h.4 is set (~50C) | [lambda](dme_lambda_code_walkthrough.md) |
| 6Fh | 11CFh | 55h | coolant threshold for setting 25h.5 (~14.7C) | see the flag setting logic below |

## Maps

### Numbered maps

These are reached through the two-stage lookup described in [the Motronic map locations](dme_map_locations.md): the code puts a one-byte map number in r2 and calls 051D. The map number in hex is the same as the map number in decimal (Map 28 is 1Ch, Map 68 is 44h, and so on).

| Map | r2 | Address | Axes | Purpose | Covered in |
|-----|----|---------|------|---------|------------|
| 3 | 03h | 1447h | 13h | rpm threshold for clearing the cranking flag 23h.2 | see the flag setting logic below |
| 25 | 19h | 144Fh | 13h | coasting fuel cut rpm threshold | [fuel cut](dme_fuel_cut_code.md) |
| 26 | 1Ah | 1598h | 11h | injector dead-time by system voltage | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 27 | 1Bh | 159Eh | 37h | load low-pass filter coefficient by rpm | [load](dme_load_code_walkthrough.md) |
| 28 | 1Ch | 15DBh | 03h | low-rpm acceleration enrichment scaling (4Ch) | [acceleration enrichment](dme_acceleration_enrichment_code_walkthrough.md) |
| 29 | 1Dh | 15D3h | 13h | low-rpm acceleration enrichment temperature map (4Ch) | [acceleration enrichment](dme_acceleration_enrichment_code_walkthrough.md) |
| 33 | 21h | 15ACh | 03h | all-rpm acceleration enrichment scaling (3Dh) | [acceleration enrichment](dme_acceleration_enrichment_code_walkthrough.md) |
| 34 | 22h | 15B2h (US), 18D0h (RoW) | 13h | all-rpm acceleration enrichment temperature map (3Dh) | [acceleration enrichment](dme_acceleration_enrichment_code_walkthrough.md) |
| 38 | 26h | 15BCh | 37h, 49h | all-rpm acceleration enrichment rpm/load scaling (3Dh) | [acceleration enrichment](dme_acceleration_enrichment_code_walkthrough.md) |
| 40 | 28h | 1566h | 13h | post-start enrichment below 65C | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 41 | 29h | 1570h | 12h | heat soak enrichment above 65C | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 42 | 2Ah | 145Bh | 12h | intake air temperature fuel correction | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 43-46 | 2Bh-2Eh | 1465h, 17E8h, 1B14h, 1A00h | 13h | warmup enrichment; 43/44 by region, 45/46 for cold cranking | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 47 | 2Fh | 1473h | 37h, 49h | warmup enrichment scaling, part throttle and WOT | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 48 | 30h | 1486h | 37h | warmup enrichment scaling, idle | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 49 | 31h | 1538h | 37h | idle fuel map | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 53 | 35h | 15E5h | 13h | ISV cranking target rpm | [ISV routine](isv_routine.md) |
| 54 | 36h | 15EFh | 13h | ISV alternate path target rpm (800rpm throughout) | [ISV routine](isv_routine.md) |
| 55 | 37h | 15F9h | 13h | ISV normal target rpm | [ISV routine](isv_routine.md) |
| 56 | 38h | 1601h | 03h | idle correction I gain, rpm below target | [ISV routine](isv_routine.md) |
| 57 | 39h | 160Bh | 03h | idle correction I gain, rpm above target | [ISV routine](isv_routine.md) |
| 58 | 3Ah | 1615h | 03h | idle correction P gain | [ISV routine](isv_routine.md) |
| 59 | 3Bh | 161Fh | 37h | ISV PWM adjustment during coasting fuel cutoff | [ISV routine](isv_routine.md) |
| 60 | 3Ch | 1629h | 37h, 13h | base (feed-forward) ISV PWM | [ISV routine](isv_routine.md) |
| 62 / 65 | 3Eh / 41h | 1659h / 1659h | 37h, 49h | lambda correction step, condition unchanged | [lambda](dme_lambda_code_walkthrough.md) |
| 63 / 66 | 3Fh / 42h | 1694h / 1694h | 37h, 49h | lambda correction step, changed to lean | [lambda](dme_lambda_code_walkthrough.md) |
| 64 / 67 | 40h / 43h | 16BAh / 18ECh | 37h, 49h | lambda correction step, changed to not-lean | [lambda](dme_lambda_code_walkthrough.md) |
| 68 | 44h | 16E0h | 37h | overload load threshold by rpm | [fuel cut](dme_fuel_cut_code.md) |
| 75 | 4Bh | 1544h | 37h | WOT fuel map | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 79 | 4Fh | 148Ch | 37h, 49h | part throttle fuel map | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 83 | 53h | 157Ah | 13h | base cranking enrichment | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 84 | 54h | 1584h | 13h | rpm threshold starting the cranking phase-out (600rpm) | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 85 | 55h | 158Ah | 4Dh | cranking enrichment phase-out scaling, first term | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 86 | 56h | 1590h | 37h | cranking enrichment phase-out scaling, second term | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 87-90 | 57h-5Ah | 164Fh, 18E2h, 164Fh, 1AFAh | 13h | ISV target load by temperature, selected by code plug | [ISV routine](isv_routine.md) |

### Directly addressed tables

These aren't reached through the 051D lookup; the code loads their address into dptr directly.

| Address | Purpose | Covered in |
|---------|---------|------------|
| 10F4h | AFM transfer table 1, indexed by the raw value divided by 32 | [load](dme_load_code_walkthrough.md) |
| 10FCh | AFM transfer table 2, exponent for the left shift (2^n) | [load](dme_load_code_walkthrough.md) |
| 1104h | AFM transfer table 3, indexed by the remainder of the division by 32 | [load](dme_load_code_walkthrough.md) |
| 112Eh | FQS map, maps the ADC value in 17h to a switch position of 0-7 | [fuel enrichments](dme_fuel_enrichments_code_walkthrough.md) |
| 1140h | return-to-idle transient fuel correction, indexed by 4Dh | [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 1150h | return-to-throttle transient fuel correction, indexed by 4Dh | [post-ignition](dme_post_ignition_code_walkthrough.md) |
| 1296h | region and altitude coding map, indexed by 14h | see the flag setting logic below |

## Some flag setting logic

A few flags are set in places that don't have a walkthrough article of their own, so the details are recorded here.

### Region and altitude coding

=== 1-Axis Map ===
Address: 1296
Input variable: 0x14
Axis length: 4

```
        0x14 |    Value
-----------------------
           0 |        1
          46 |        3
         128 |        2
         200 |        0
```

In volts:

```
        0x14 |    Value
-----------------------
           0 |        1
           1 |        3
         2.5 |        2
         4.0 |        0
```

According to opendme, having the altitude sensor open should select 0 (open) and the 1.8k resistor should select 2. Altitude sensor shorted should give 1.

So,

```
	mov	dptr,#X1296
	lcall	X05cd
	rrc	a
	mov	25h.7,c
	rrc	a
	mov	25h.6,c
```

25h.7 = 0 for US and RoW if open (below 1000M on US cars), 1 if shorted (above 1000M)

25h.6 = 0 for US, 1 for RoW

Thus 20h.7 only gets set when 25h.6 is clear, i.e. US cars (o2 sensor).

### Setting 23h.2 (cranking flag) and 25h.4, 25h.5 (coolant temp thresholds)

* first tps
* then region coding
* then:

```
X1bf0:	
	mov	a,#10h
	movc	a,@a+dptr
	clr	c
	subb	a,37h
	jnc	X1c03
	mov	r2,#3
	lcall	X051d
	clr	c
	subb	a,37h
	jc	X1c21
	ret
;
X1c03:	
	setb	23h.2
	jnb	20h.7,X1c1c
	mov	a,#6fh
	movc	a,@a+dptr
	cjne	a,rb2r3,X1c0e
X1c0e:	
	cpl	c
	mov	25h.5,c
X1c11:	
	mov	a,#6dh
	movc	a,@a+dptr
	cjne	a,rb2r3,X1c17
X1c17:	
	cpl	c
X1c18:	
	mov	25h.4,c
	ajmp	X1c20
;
X1c1c:	
	clr	25h.4
	clr	25h.5
X1c20:	
	ret	
;
X1c21:	
	clr	23h.2
	ret
```

1160+10h = 1170 which contains 4, i.e. 160rpm.

Thus this code means

```
if rpm > 160:
	a = map_lookup(map 3)
	if rpm > a:
		clear 23h.2
		return
else:
	set 23h.2
	if 20h.7:
		a = dptr(1160+6F=11CF) # contains 55h, i.e. 85, or ~14.7C
		if ntc_ii < a:
			set 25h.5 # note that c is complemented so the logic is backwards
		a = dptr(1160+6D=11CD) # contains 55h, so still 14.7C
		if ntc_ii < a
			set 25h.4
		return
	else:
		clear 25h.4
		clear 25h.5
		return
```

Map 3:

| Engine Temperature (0x13) | Value |
|---|---|
| -34.61 | 18 |
| 2.24 | 20 |
| 45.66 | 20 |

So 720 and 800 are the thresholds for turning the cranking flag OFF, depending on temperature.
