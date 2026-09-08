# KLR master memory map

## Byte variables
Location | Purpose
---------|--------
24h | engine speed (complemented from r6; literally timer ticks per ignition event)
2Eh | battery voltage
2Fh | knock sensor (diagnostics)
39h | throttle position (power supply)
3Ah | throttle position (degrees)
3Ch | throttle position (raw)
3Fh | ??
38h | ??
46h | knock sensor (proper)
24h | engine speed (in timer ticks)
52h | MAP pressure
33h | blink code
22h | angle to begin ADC initialization routine
23h | angle to read ADC (after 22h - approx 15 deg.)
44h | rpm range (map axis)
43h | throttle position (map axis)
70h - 73h | per-cylinder timing delay
74h - 7Bh | per-cylinder knock threshold
60h | boost control PID error (target boost - actual boost)
61h | boost control PID I term (integral)
62h | boost control PID D term (derivative)
68h | boost control feedforward value (CV duty cycle)
41h | final CV duty cycle
57h | total boost reduction for knock control 

### Blink Code Error Counters

Location | Error Type
---------|-----------
30h|    knock/MAP
35h|    boost high/low
36h|    TPS/TPS power supply

## RPM Dependant Constants

These are loaded from a series of 2D maps (rpm only) located at 0x925. 

Location | Purpose
---------|---------
0x2A|    for calculating the angle to start ADC stuff (22h)
0x2B|    for calculating the angle for ADC read (23h)
0x47|    coefficient for knock threshold (comparison with 46h)
0x4A|    cycle count before restoring 0.3 deg. timing (49h)
0x50|    cycle count before restoring boost (15 to 37)
0x4E|    cycle count before pulling boost (31 to 125)
0x4B|    max timing retard (18 dec. for all rpm)
0x48|    throttle position threshhold for knock control
0x4C|    threshold for pulling boost
0x3E|    angle for WOT (set to 66 decimal for all rpm)
0x45|    minimum knock threshold value (10 for all rpm)
0x69|    counter for 6A (set to 4 for all rpm)


## Units

### Cycling valve PWM
The cycling valve PWM signal is handled by the timer interrupt routine, which runs at 87us ticks. Within the cycling valve logic in the timer interrupt routine, the on and off time are each maintained for a futher 4 counts. The period is 193, and ```193*4*87 = 67164us``` which corresponds to ~14.8Khz. So that's the frequency and the duty cycle values from the map can just be divided by 193. 

### MAP
There are two different MAP sensors used in the KLRs. The early version used a daughter board with a Motorola transducer (probably an [MPX200](reference/MPX201.PDF)) along with various other componenets. The later version used a __Bosch 0 273 003 204 200 (200kpa)__ sensor in a plastic case. 

As far as I can tell, the circuitry that relates to the ADC signal didn't change, so the two sensors should be interchangeable. There's presumably no datasheet for the early one, being a custom design, but there is a [datasheet](reference/0273 003 204.pdf) for the later Bosch one. It gives a formula for the output voltage:

```((4.55 * P_abs)/180) - 0.256```

(assuming a 5v reference; scale accordingly). 

So we should see ~2.271v for 100kpa. 

The early one appears to be close. For instance, on an early version, at rest, I saw ```2.21 - 2.24``` from the map sensor, when the ambient pressure should have been in the neighborhood of 100kpa.

With both versions, the signal is reduced by a voltage divider and  we see the value at Channel 4 (pin 2) at around ~0.945x the raw map sensor output. That would give us around ```2.145v``` at the ADC input, or around 109 units. 

Next, the MAP function of the ADC read process adds 10 units before storing the value in 52h. This is a little strange - directionally it tends to offset the -0.256 offset that the Bosch sensor (and presumably the early one) have, but it's a couple of units short. An offset of -0.256 would require +12 (after the 0.95x scaling I mentioned). However, if we assume that they wanted to make the middle of the available range match atmospheric pressure (~101.3kpa) as opposed to 100kpa (the nominal halfway point of the sensor's range), then it's pretty close to the right number. 

In any case, this +10 puts us at around 119 for 100kpa. Since we scaled everything at 0.95x, this is just under half of the available range. 

And ```119 * 1.75 = 208.25``` is almost exactly the max value found in the 1987 boost map (it peaks briefly at 209). Also the value it ends up with near the redline, 185, gives ```185/119 = 1.55``` and this is a nice match because the Technik document says "*as the engine speed rises the charging air pressure drops and reaches a value of 1.55 bar (absolute) at the rated speed of 5800rpm*".

Putting all this together gives us something very close to 1kpa = 1.2 units in the software. Here are some important numbers assuming that's true:

* overboost threshold - 32 - 0.26 bar
* underboost threshold - 64 - 0.53 bar
* boost reduction for knock - 5 - 0.042 bar

(The Technik document doesn't specify over/underboost thresholds but does say that boost reduction for knock is "*taken back in steps of 30 to 50 mbar (0.030 to 0.050 bar)....*".


## Maps

### Boost

* '86:
| Throttle% \ RPM | 0 | 1864 | 2041 | 2254 | 2446 | 2674 | 2948 | 3164 | 3415 | 3708 | 4057 | 4479 | 4724 | 4998 | 5653 | 6050 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 57.0 | 137 | 141 | 144 | 145 | 145 | 146 | 146 | 148 | 148 | 148 | 150 | 150 | 150 | 152 | 152 | 152 |
| 61.3 | 139 | 141 | 145 | 151 | 154 | 157 | 157 | 158 | 158 | 158 | 158 | 158 | 158 | 158 | 158 | 158 |
| 65.6 | 139 | 141 | 148 | 157 | 164 | 167 | 167 | 170 | 170 | 167 | 167 | 167 | 166 | 165 | 165 | 165 |
| 69.9 | 141 | 142 | 159 | 170 | 177 | 180 | 180 | 180 | 180 | 177 | 176 | 175 | 174 | 171 | 171 | 171 |
| 74.2 | 143 | 145 | 171 | 190 | 193 | 193 | 193 | 193 | 193 | 191 | 188 | 186 | 184 | 182 | 180 | 180 |
| 78.5 | 145 | 152 | 180 | 206 | 208 | 209 | 208 | 207 | 207 | 206 | 202 | 198 | 193 | 188 | 185 | 185 |
| 82.8 | 145 | 152 | 180 | 206 | 208 | 209 | 208 | 207 | 207 | 206 | 202 | 198 | 193 | 188 | 185 | 185 |
| 87.1 | 145 | 152 | 180 | 206 | 208 | 209 | 208 | 207 | 207 | 206 | 202 | 198 | 193 | 188 | 185 | 185 

* '89:
| Throttle% \ RPM | 0 | 1864 | 2041 | 2254 | 2446 | 2674 | 2948 | 3164 | 3415 | 3708 | 4057 | 4479 | 4724 | 4998 | 5653 | 6050 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 57.0 | 137 | 141 | 144 | 145 | 145 | 146 | 146 | 148 | 148 | 148 | 150 | 150 | 150 | 152 | 152 | 152 |
| 61.3 | 139 | 141 | 145 | 151 | 154 | 157 | 157 | 158 | 158 | 158 | 158 | 158 | 158 | 158 | 158 | 158 |
| 65.6 | 139 | 141 | 148 | 157 | 164 | 167 | 167 | 170 | 170 | 167 | 167 | 167 | 166 | 165 | 165 | 165 |
| 69.9 | 141 | 142 | 159 | 170 | 177 | 180 | 180 | 180 | 180 | 177 | 176 | 175 | 174 | 171 | 171 | 171 |
| 74.2 | 143 | 145 | 171 | 190 | 193 | 193 | 193 | 193 | 193 | 191 | 188 | 186 | 184 | 182 | 180 | 180 |
| 78.5 | 145 | 152 | 180 | 206 | 206 | 206 | 206 | 206 | 206 | 208 | 206 | 206 | 206 | 206 | 206 | 194 |
| 82.8 | 145 | 152 | 180 | 206 | 206 | 206 | 206 | 206 | 206 | 208 | 206 | 206 | 206 | 206 | 206 | 194 |
| 87.1 | 145 | 152 | 180 | 206 | 206 | 206 | 206 | 206 | 206 | 208 | 206 | 206 | 206 | 206 | 206 | 194 |

### Cycling valve duty cycle:
* all models:
| Throttle% \ RPM | 0 | 1864 | 2041 | 2254 | 2446 | 2674 | 2948 | 3164 | 3415 | 3708 | 4057 | 4479 | 4724 | 4998 | 5653 | 6050 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 57.0 | 38 | 38 | 38 | 38 | 38 | 38 | 38 | 38 | 38 | 38 | 38 | 38 | 38 | 38 | 38 | 38 |
| 61.3 | 57 | 57 | 57 | 57 | 57 | 57 | 57 | 57 | 57 | 57 | 57 | 54 | 54 | 48 | 48 | 48 |
| 65.6 | 76 | 76 | 76 | 76 | 76 | 76 | 76 | 76 | 76 | 73 | 73 | 69 | 67 | 61 | 58 | 58 |
| 69.9 | 115 | 115 | 115 | 115 | 115 | 109 | 108 | 106 | 104 | 100 | 96 | 90 | 84 | 81 | 81 | 81 |
| 74.2 | 154 | 154 | 154 | 154 | 154 | 146 | 142 | 138 | 134 | 131 | 127 | 123 | 119 | 115 | 115 | 115 |
| 78.5 | 191 | 191 | 191 | 191 | 191 | 182 | 173 | 169 | 165 | 161 | 157 | 150 | 146 | 142 | 146 | 150 |
| 82.8 | 191 | 191 | 191 | 191 | 191 | 182 | 173 | 169 | 165 | 161 | 157 | 150 | 146 | 142 | 146 | 150 |
| 87.1 | 191 | 191 | 191 | 191 | 191 | 182 | 173 | 169 | 165 | 161 | 157 | 150 | 146 | 142 | 146 | 150 |

### PID gain
* all models:
| Throttle% \ RPM | 1864 | 2254 | 2674 | 3164 | 3708 | 4479 | 4998 | 6050 |
|---|---|---|---|---|---|---|---|---|
| 57.0 | 227 | 227 | 231 | 234 | 230 | 230 | 233 | 233 |
| 65.6 | 227 | 195 | 167 | 138 | 134 | 166 | 169 | 201 |
| 74.2 | 227 | 131 | 103 | 106 | 102 | 134 | 137 | 169 |
| 82.8 | 227 | 163 | 103 | 106 | 102 | 134 | 169 | 201 |

