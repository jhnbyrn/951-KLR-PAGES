# DME software timers

The 8051 has two asynchronous hardware timers. This isn't really enough or all the things that need to be timed, so they are just used for the most critical things: fuel injection control and spark timing. 

For other things that are more tolerant of small errors, there's a set of four software controlled timers: 3C, 3D, 3E and 3F. 

The basic idea is that these timers are prescaled by constants, and decremented during the Timer 1 interrupt, just after the ADC read routine. Since that routine runs at a frequency of ~87Hz, our software timers have a base period of ~11.5ms. 

The prescale values are stored startingat 1193. 

| Location | Prescale |  Unit | Purpose |
|----------|----------|----------|----------|
| 3C | 36  | 414ms | post-start enrichment |
| 3D | 5 | 58ms | acceleration enrichment |
| 3E | 1 | 11.5ms | lambda timer |
| 3F | 30 | 345ms | load threshold to disable lambda |

Each of these timers can be loaded with different values depending on various conditions, but we can use this table to figure out what those values mean in terms of time. 

For instance the value at 11AD is loaded into 3F when load exceeds 102 to determine if lambda control should be disabled. Now 11AD contains 6, so now we can see that this means 6 * 345ms = ~2 seconds.

As another example, here's Map 40 which contains the post-start fuel enrichment values that are loaded into 3C, along with the time it will take for 3C to reach zero, and thus phase out the correction:

| Engine Temperature (0x13) | Value | Seconds to zero |
|---|---|
| -13.55 | 90 | 37 |
| 16.71 | 45 | 18 |
| 35.79 | 51 | 21 |
| 55.53 | 0 | 0 |


