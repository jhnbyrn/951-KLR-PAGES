# Exponential Smoothing

Contents

1. [Overview](#overview)

2. [The Code](#the-code)

3. [Usage](#usage)

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

With reference to the function definition from the Overview section, it's clear that we need 3 variables for this function:

1. previous output

2. input

3. smoothing factor

These values must be loaded into r0, r1 and r7 respectively. Actually, the value stored in r7 is not *quite* the smoothing factor, but it *controls* the smoothing factor. The smoothing factor in this routine is always a power of 2, and r7 controls *which* power of 2 it will be. For our purposes, let's assume that the r7 is set to 4 (which is a commonly used value in the KLR code).

So, now that we know what's in r0, r1 and r7, let's begin. We start by making a copy of r7, because it's going to be used as a loop-coutner, which is destructive, and we'll need it again afterwards:

```asm
0xe08 mov  a,r7
0xe09 mov  r4,a
```

Now we copy the high byte of the previous output variable into r2, and the low byte into r3, and then call 0xFCB:

```asm
0xe0a mov  a,@r0
0xe0b mov  r2,a
0xe0c inc  r0
0xe0d mov  a,@r0
0xe0e mov  r3,a
0xe0f call $07CB    ;0xFCB
```

So next, let's look at what happens in 0xFCB:

```asm
0xfcb mov  a,r2
0xfcc clr  c
0xfcd rrc  a
0xfce mov  r2,a
0xfcf mov  a,r3
0xfd0 rrc  a
0xfd1 mov  r3,a
0xfd2 djnz r7,$0FCB
0xfd4 ret
```

This is pretty trivial - we're just dividing our previous output variable by 2 several times (by rotating it to the right). The counter r7 controls how many times we do this. Since it was set to 4, we're dividing by 2^4, i.e. 16. Hopefully now you can see the importance of using the full 16-bit value even when we don't really care about the low byte elsewhere in the code. If we didn't use it here, we could never get a precise division by 16. 

After that, it's back to the main routine where we restore the counter r7 (since we decremented it to zero for the loop in 0xFCB): 

```asm
0xe11 mov  a,r4
0xe12 mov  r7,a
```

Next we convert our 16-bit value (which is now 1/16th of the previous output of the routine) into a negative number in [2's complement](https://en.wikipedia.org/wiki/Two's_complement) form, which we store in r4 (high byte) and r5 (low byte):

```asm
0xe13 mov  a,r3
0xe14 cpl  a
0xe15 add  a,#$1
0xe17 mov  r5,a
0xe18 mov  a,r2
0xe19 cpl  a
0xe1a addc a,#$0
0xe1c mov  r4,a
```

The code above is a pretty standard way of handing 16-bit 2's complement numbers in an 8-bit processor. The __addc__ instruction includes the value in the carry flag in the addition, in case it was set by an overflow in the add at 0xE15. 

Now we again do division by 16, this time on r1, which you'll recall was our input value. Note that we set r3 (the low byte) to zero, because the input value for this routine is only an 8-bit number:

```asm
0xe1d mov  a,@r1
0xe1e mov  r2,a
0xe1f mov  r3,#$0
0xe21 call $07CB
```

Next we subtract our r4, r5 value (prevous output * 1/16) from the original previous ouput value in r0, storing the result back into r4, r5:

```asm
0xe23 mov  a,@r0
0xe24 add  a,r5
0xe25 mov  r5,a
0xe26 dec  r0
0xe27 mov  a,@r0
0xe28 addc a,r4
0xe29 mov  r4,a
```

So now we have effectively taken 15/16ths of the previous output; this takes care of the (1 - a)*previous_output term of the function rule we looked at in the Overview!

Finally we add this to the value in r2/r3, which is 1/16th of the input:

```asm
0xe2a mov  a,r5
0xe2b add  a,r3
0xe2c mov  r3,a
0xe2d mov  a,r4
0xe2e addc a,r2
0xe2f ret
```

So, upshot of all this is that we end up with out final output value in the accumulator (high byte) and r3 (low byte), and this final output value is 1/16th of the input *plus* 15/16hths of the previous output. 

## Usage

This routine is called from various places in the KLR code, but we'll take a quick look at how it's called from the knock [threshold calulation](knock_detection.html#the-code), for an example of usage:

```asm
0xd7f mov  r0,#$7A    ;current knock threshold (high byte)
0xd81 mov  r1,#$46    ;most recent knock sensor output
0xd83 mov  r6,#$74    ;the first of 8 locations (4 16-bit values)
0xd85 mov  r7,#$4     ;this controls the smoothing factor 'a'
0xd87 call $07A9      ;0xFA9
```

The value in 7Ah is the current knock threshold for current cylinder. As discussed in the overview, and in the [knock detection code](knock_detection.md#the-code) this is only the high byte of a 2-byte (16-bit) value. The low byte is in 7Bh, and although it's not used for knock detection, it *is* used when calulating the new threshold, as you've seen in the previous section. 

The routine at 0xFA9 just calls the smoothing routine, and then calls the rotation routine 0xFAB twice:

```asm
0xfa9 call $0608    ;0xE08
0xfab call $07B0    ;0xFB0
0xfad call $07B0
0xfaf ret
```

The rotation routine just pushes the 8 locations around (4 16-bit values) to make sure that we're dealing with the correct cylinder threshold value each time:

```asm
0xfb0 xch  a,r6
0xfb1 mov  r0,a
0xfb2 xch  a,r6
0xfb3 xch  a,r3
0xfb4 mov  r7,#$4
0xfb6 xch  a,@r0
0xfb7 inc  r0
0xfb8 xch  a,@r0
0xfb9 inc  r0
0xfba djnz r7,$0FB6
0xfbc ret
```
