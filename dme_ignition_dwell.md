# Ignition dwell calculation

The dwell calculation is very simple - there's just one map (Map 24) that uses rpm and battery voltage as its inputs. 

The map lookup happens at 07b7, called directly from the main loop:

```
X07b7:	
	mov	r2,#18h
	acall	X051d
	mov	2fh,a
	ret
```

The dwell value is represented in half-tooth units of roughly 1.36 degrees. See the [timing signal code walkthrough](ignition_timing_code.md) for the exact details of this __2F__ is ultimately used. 

Its conventional to show dwell times in milliseconds rather than degrees, since the point is to charge the coil and the time that takes is indepenent of rpm:

| RPM \ V | 6v | 8v | 10v | 12v | 14v | 16v | 16.5 |
|---|---|---|---|---|---|---|---|
| 40 | 142.05 | 147.73 | 130.68 | 90.91 | 68.18 | 56.82 | 39.77 |
| 160 | 103.69 | 59.66 | 32.67 | 22.73 | 17.05 | 14.20 | 9.94 |
| 320 | 51.85 | 29.83 | 16.34 | 11.36 | 8.52 | 7.10 | 4.97 |
| 480 | 38.35 | 21.78 | 11.84 | 8.52 | 6.63 | 5.21 | 3.31 |
| 640 | 33.03 | 18.82 | 10.30 | 7.10 | 5.68 | 4.62 | 2.84 |
| 800 | 30.11 | 17.33 | 9.38 | 6.53 | 5.11 | 4.26 | 2.56 |
| 1440 | 16.73 | 15.31 | 8.36 | 5.84 | 4.42 | 3.79 | 2.21 |
| 2080 | 11.58 | 10.60 | 6.34 | 4.59 | 3.61 | 2.95 | 1.75 |
| 2280 | 10.57 | 10.57 | 6.28 | 4.59 | 3.59 | 2.99 | 1.79 |
| 3840 | 6.27 | 6.27 | 6.27 | 4.62 | 3.61 | 3.02 | 1.78 |
| 5240 | 4.60 | 4.60 | 4.60 | 4.60 | 3.60 | 2.99 | 1.82 |
| 6480 | 3.72 | 3.72 | 3.72 | 3.72 | 3.61 | 3.02 | 1.79 |

The behavior of the 944 ignition coil and its inductance and charging time have been the subject of some controversy in the past, with some people believing that the time it takes to reach its maximum current (9 amps) is signifncantly more than the available dwell time at higher rpms. The result would be that it doesn't charge fully at or above those speeds, and therefore a more modern, faster charging coil would be an updgrade even on an otherwise stock car, since it would have more energy to fire the spark. 

This is not true - [this thread on www.carpokes.com](https://www.carpokes.com/viewtopic.php?t=3574&hilit=stock+dwell+map+inductance&start=230) settles the issue definitively. 

The stock coil has an inductance of somewhere around 3 to 3.5mH, and at normal operating voltages (say 13.8) it takes in the order of 3.6ms to fully charge, which is less than the available 4.6ms at 6500rpm. 

That section of the thread is worth a read regardless. Joshua of Rogue Tuning explains some interesting facts about the system, including a great explanation for why the dwell values are so long at lower rpm despite the fact that voltage already has its own axis (rpm quantization error) and why we need more time for dwell than just the charging time (blanking time to let the coil finish ringing etc.). 


