# KLR cycling valve PWM calculation

This routine handles calculating the final cycling valve PWM output value. Basically this is the open loop value from the map (based on throttle position and rpm) combined with the closed loop correction. 

The closed loop correction consists of 63h (which is the sum of the P, I and D terms) and 67h which is a second integral/trim term that accumulates whenever the main I term (61h) is saturated. 

At this point these terms have [already been calculated](klr_pi_boost_control_code.md), and the remaining steps done here are:

* scale the main PID correction by the gain map value
* add the main correction to the open loop map value
* add the trim term 67h
* clamp the result to the allowed min/max rails
* set the main PWM variable 41h (used by the actual PWM signal generator routine elsewhere). 

The main variables used here are:

Location | Purpose
--------|--------
33h | error code, aka blink code location
41h | PWM pulse width for cycling valve (period=193)
63h | total PID correction sum
67h | trim
68h | open loop cycling valve PWM
6B | PID gain map value


```
0xf00 mov  r1,#$63
0xf02 mov  a,@r1
0xf03 mov  r6,a
0xf04 cpl  a
0xf05 jb7  $0F0A		;b7 means positive (underboost) since cpl
0xf07 inc  a
0xf08 mov  r6,a			;r6 = |63h|
0xf09 cpl  f0			;f0 now = 0, indicating negative correction
```

We load 63h (complete PID output), store in r6, but also invert in a. At this point, 63h is interpreted as a 2s complement signed value. We are going to multiply it by the gain value so we want an absolute value first.

If b7 of the complemented value is not set (i.e. original was negative) then we inc and store back into r6, and cpl f0 to indicate that it's a negative value. 

(Note that at DDA just before we call boost control, we clr f0 and cpl f0, therefore the defaut value is 1. Thus here f0=1 means positive). 

So this turns it into an unsigned absolute value with the direction in f0.

```
0xf0a mov  a,@r0		;6B
0xf0b orl  a,#$1F		;00011111
0xf0d mov  r3,a
0xf0e sel  mb0
0xf0f call $0300		;multiply r3*r6, i.e. 63h*6B
0xf11 sel  mb1
0xf12 mov  r3,#$B1		;177, high clamp value
0xf14 jf0  $0F19		;jump if correction is positive
0xf16 cpl  a			;~(63h*6B)
0xf17 mov  r3,#$0		;lower clamping value, 0
0xf19 mov  r4,a			;r4 = signed correction w/gain
```
Above, we take the top 3 bits of the 6B map value (masking the lower bits to 1), and multiply it by our |63h| value. So the top 3 bits of the gain map are over all PID gain. (See a visualization of this map [here](klr_boost_control_gain.md)).

We cpl the high byte of the result if the correction is negative, and then keep it in r4, so ```r4 = 63h*gain/256``` (signed). The gain values are represented as fractions, where 256 is the denominator, and they range from 0.5 to 1. 

We also set the clamping values here in r3: 0 for negative and 177 for positive. (Note that the PWM period is represented by 193, so 177 is about 92%). 

Next we handle the trim term 67h and the open loop term 68h:

```
0xf1a mov  r1,#$67
0xf1c mov  a,@r1
0xf1d clr  c
0xf1e rlc  a			;a = 67*2
0xf1f mov  r1,#$68		;CV open loop map value
0xf21 add  a,@r1		;a=68 + 67*2
0xf22 mov  r1,#$6F		;6F also stores unused ADC Ch. 2 ??
0xf24 mov  @r1,a
0xf25 add  a,r4
0xf26 mov  r4,a			;r4 = (63h*6B) + 68 + (67*2)
```

The trim value is doubled and added to the open loop value, and finally r4 (which holds 63h*gain). We also store 67h+68h in 6F, but this doesn't seem to be used anywhere. 

Now, 67h is only allowed to accumulate when the main integral term 61h has reached it maximum or minimum value. But as we can see here, each count in 67h counts *double*, so it's really a faster I term than the main one. Note that there's no clamping applied here; 67h is 128-biased like 61h and 62h, so the maximum safe values are +/- 64 from the centre 128. Any further than that, and the sign will get flipped when we double it. This seems to be yet another place where the programmers assumed that the system would stay within safe limits without the need for clamping. 

There is some unwinding logic applied to 67h in the clamping section further below. 

Next we handle clamping the PWM output - this is probably the trickiest part of this routine:

```
0xf27 jf0  $0F2A		;jump if correction is positive
0xf29 cpl  c
0xf2a jc   $0F33		;if positive, we really overflowed
0xf2c cpl  a
0xf2d add  a,r3
0xf2e jf0  $0F31
0xf30 cpl  c
0xf31 jc   $0F3F
0xf33 mov  a,r3			;a = 0 or 171
0xf34 mov  r4,a
0xf35 mov  r1,#$67
0xf37 mov  a,@r1
0xf38 dec  a
0xf39 dec  a
0xf3a jb7  $0F3E
0xf3c add  a,#$4
0xf3e mov  @r1,a
```

You can certainly work through all the cases if you want, but here's the effect of the above section in simpler terms:

```
if positive and c=1:
	r4 = 177
	unwind 67h
else if positive and c=0:
	a = -a + 177
	if c=0:
		r4 = 177
		unwind 67h
else if negative and c=1:
	a = -a + 0   (essentially do nothing)
else if negative and c=0:
	a = 0 (r3)
	unwind 67h
```	

Even in this form it can be hard to follow what's going on! Remember that we need to know if we had an overflow when added all those terms together, but if we did, then we also need to know which direction the correction was supposed to have, in order to resolve the overflow correctly. 

If the correction was positive and we had an overfow, that's easy: clamp to the max value. If it was positive and we didn't have an overflow, then we might still need to clamp to the max - we need to check if we exceeded the max of 177. If so, we clamp, if not, we don't. 

In the negative case, the overflow flag actually works *backwards*! That is, a failure to overflow means we tried to subtract a big number from a small number. The negative correction was bigger than the open loop value. So in that case we clamp to the min. value of 0. 

For negative cases where we *did* overflow, that's actually the simple, happy path: we subtracted a smaller number from a bigger one, and all is well. 

In all cases where we clamp to either the min. or max. value, we also move 67h back towards its neutral value of 128, at a double rate. Continuing to "wind up" this term when the output is saturated would cause problems if the direction of the correction was to suddenly flip due to changing driving conditions. 

The remaining section is a bit messy and haphazard, but the important thing it does is set the final output in 41h, and possibly call the reset routine if necessary:

```
0xf3f mov  r2,#$22		;doesn't appear to be used anywhere
0xf41 call $07D5		;0xfd5, r0=41h, a=max(r4, 191)
0xf43 mov  r1,#$43
0xf45 mov  a,@r1
0xf46 jz   $0F81		;jump to reset if TPS < 53 deg. 
0xf48 add  a,#$FF		;add 255
0xf4a jc   $0F4F		;obviously can't carry if r1 was zero
0xf4c mov  a,@r0		;r0=41h
0xf4d jz   $0F81		;reset boost control variables if 41h=0
0xf4f inc  r1			;44h, rpm
0xf50 mov  a,@r1
0xf51 add  a,#$C4		;196
0xf53 jc   $0F81		;jump if rpm range = 60, i.e. <= ~1850rpm
0xf55 add  a,#$0
0xf57 jnc  $0F5C		;this clearly has to carry
0xf59 mov  a,@r0		;appears to be unreachable
0xf5a jz   $0F81
```

The call to 07D5 (i.e. FD5) just does some preparation with 41h - here's that routine:
```
0xfd5 mov  r0,#$41
0xfd7 mov  a,r4
0xfd8 add  a,#$40
0xfda jnc  $0FDE		;carries if 4f>=192
0xfdc mov  r4,#$BF		;cap to 191
0xfde ret
```
Clearly this just loads the address 41h into r0, and clamps r4 to a maximum of 191, then returns . 

After that we check throttle position and RPM. If throttle is below 53 degrees, or RPM is below around 1850, we call the reset routine, which wipes out all the boost control variables, re-initializes them, and sets the cycling valve PWM 41h to zero. 

The final actual assignment of our calculated PWM value r4 to 41h appears buried in this next block, which is a confusing piece of code that checks the timing retard values for each cylinder, and sets a special error code if any of the have reached the max. This really has nothing to do with boost control directly, but this code does call the reset routine if there's a real error code, thereby putting the KLR into limp mode, with no cycling valve output no matter what the throttle position or rpm are:

```
0xf5c mov  r1,#$4B		;4Bh = max timing retard from the rpm map at 0x925
0xf5e mov  a,@r1
0xf5f mov  r2,a
0xf60 mov  r1,#$33		;33h is current blink code
0xf62 mov  a,@r1
0xf63 jz   $0F69
0xf65 add  a,#$EF		;EFh+11h=0
0xf67 jnz  $0F81		;jump to limp mode if 33h has anything other than 1-1
0xf69 mov  a,r4
0xf6a mov  @r0,a		;41h = r4 (final CV PWM value)
0xf6b mov  r0,#$6F
0xf6d mov  r4,#$4
0xf6f inc  r0			;70h (start of timing delays for each cylinder)
0xf70 mov  a,@r0
0xf71 cpl  a
0xf72 add  a,r2			;c=1 if r2>timing_delay
0xf73 jc   $0F7E		;no carry means we set blink code 1-1 (unless there's already a code set)
0xf75 mov  a,r2
0xf76 mov  @r0,a
0xf77 mov  r1,#$33
0xf79 mov  a,@r1
0xf7a jnz  $0F7E
0xf7c mov  @r1,#$11		;33h <- 11 (blink code 1-1)
0xf7e djnz r4,$0F6F		;loop 4 times
0xf80 ret
```

Here's the reset/limp mode function we saw being called in various cases earlier. In summary, this is called any time the cycling valve PWM value is zero, and also any time we have an error code stored in 33h *unless* it's the special error code 11h, which doesn't really seem to be used for anything meaningful. 

```
	;; boost control reset/limp mode function
0xf81 clr  a
0xf82 mov  r3,#$10
0xf84 mov  r1,#$57		;boost reduction
0xf86 mov  @r1,a
0xf87 inc  r1
0xf88 djnz r3,$0F86		;57h to 67h are all boost control locations
0xf8a mov  @r1,#$80		;67h
0xf8c mov  r1,#$61
0xf8e mov  @r1,#$80
0xf90 mov  r1,#$52
0xf92 mov  a,@r1
0xf93 inc  r1
0xf94 mov  @r1,a		;53h filtered target boost initialized to current boost
0xf95 clr  a
0xf96 jmp  $076A		;F6A (sets cv pwm 41h to a, i.e. zero)
	;; END limp mode function
```

A few interesting things to note about this section: 

* all the values from 57h to 67h are zeroed, then 61h and 67h are both set to 128; these terms are both 128 biased so this is the equivalent of zero. 
* 62h is not set to 128, but that term is always set to 128 if necessary in its own routine
* 53h (filtered target boost) is actually initialized to the *current* boost value here. 

This last point deserves some more explanation. The way the filtering routine works is that it moves a variable *gradually* towards a target. If the target starts at say 10, and the variable starts at zero, then the target will approach 10 exponentially on each iteration of the filter routine. 

Now suppose that 53h was initialized to zero. Then it would be moved towards the actual target boost value from the map gradually, but initially the boost delta between 52h and 53h could be very big. And as explained in the [PI routine article](klr_pi_boost_control_code.md), the P term is written with the assumption that the boost delta will always be limited to +/- 68. 

Having 53h start *equal* to 52h has the effect of making very large boost deltas unlikely or maybe even impossible, which helps to justify the lack of overflow checking in the P term calculation. 
