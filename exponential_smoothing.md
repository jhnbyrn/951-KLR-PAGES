# Exponential Smoothing

## Overview

This routine, located at 0xE08, implements the exponential smoothing function described [here](https://en.wikipedia.org/wiki/Exponential_smoothing). 

Expressed as a mathematical formula, the function is very simple:

```
output = a*input + (1 - a)*previous_output
```

(where a < 1)

It might help to consider an example. Let's say __a__ is 1/16. Then the function will give us 1/16th of the input, *plus* 15/16ths of the *previous output*. You can see from this that the new output is mostly influenced by the *previous* output, and only slightly influenced by the input. So naturally, this function tends to dampen any sudden changes to the input value over time; it's a *low-pas filter*. The smaller __a__ is, the greater the smoothing effect.  

This smoothing function is used many times throughout the KLR code. It's used in the knock detection routine, both for calculating the per-cylinder knock thresholds, and for filtering the timing delay angle to control whether boost should be reduced or not. It's also used in the PID algorithm to filter out sudden changes in target boost. 

Knowing what the code does it more than half the battle in understanding it, in this case. It's actually very simple - the only thing that makes it a little more involved than you might expect is the fact that it uses 16 bit values. In most cases where this function is used, only the high byte of the result is actually used. But 16 bit values are necessary to avoid rounding errors. 

## The Code

TBD...

```asm
0xe08 mov  a,r7
0xe09 mov  r4,a
0xe0a mov  a,@r0
0xe0b mov  r2,a
0xe0c inc  r0
0xe0d mov  a,@r0
0xe0e mov  r3,a
0xe0f call $07CB
0xe11 mov  a,r4
0xe12 mov  r7,a
0xe13 mov  a,r3
0xe14 cpl  a
0xe15 add  a,#$1
0xe17 mov  r5,a
0xe18 mov  a,r2
0xe19 cpl  a
0xe1a addc a,#$0
0xe1c mov  r4,a
0xe1d mov  a,@r1
0xe1e mov  r2,a
0xe1f mov  r3,#$0
0xe21 call $07CB
0xe23 mov  a,@r0
0xe24 add  a,r5
0xe25 mov  r5,a
0xe26 dec  r0
0xe27 mov  a,@r0
0xe28 addc a,r4
0xe29 mov  r4,a
0xe2a mov  a,r5
0xe2b add  a,r3
0xe2c mov  r3,a
0xe2d mov  a,r4
0xe2e addc a,r2
0xe2f ret
```
