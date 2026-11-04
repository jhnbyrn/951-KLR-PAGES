# Porsche 944 Turbo cycling valve data

coil resistance 29ohms
coil inductance 80.9mH
peak current 420ma
rise time (95%) 10.7ms
decay time 4.7 - 5ms

duty cycle ~15Hz
max on % 177/193 = 91.7%

Thus the minimum off time is very close to (just slightly more than) the required current decay time of around 5ms. 

MAC coil resistance 26 ohms
coil inductance 45mH
peak current 450ma

## CV leagage

The cycling valve leaks air from the W line to the R line because the air pressure is able to push the piston up. Testing with an air compressor I found the pressure on the W side is maxed out at about 7psi. It will not go higher no matter how much I turn up the inlet pressure. 

In contrast the MAC valve will not leak as long as the barb fittings are proprerly sealed. I tried up to 25psi and there's zero leakage back to the return line. 

## WG air pressure behavior

With the CV, activating the valve not only pulses the WG pressure on and off, but it reduces the peaks too, apparently because of the CV inlet restriction. Here are some data points to get a sense of how much:

* CV with inlet pressure held at MAP voltage 2.827v:

|Pulse width | DC % | MAP voltage (at W) | MAP (kpa) |
| 0 | 0 | 2.827v | |
| 16ms | 24% | 2.62v | |
| 22ms | | 2.5v | |
| 31ms | | 2.288v | |
| 43ms | | 2.163 | |

* MAC with inlet pressure held at MAP voltage 3.348v:

|Pulse width | DC % | MAP voltage (at W) | MAP (kpa) |
| 0 | 0 | 3.348 v | |
| 14.5ms | | 3.265v | | 
