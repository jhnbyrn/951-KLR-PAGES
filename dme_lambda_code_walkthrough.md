# DME lambda correction code walkthrough

This is a detailed look at the complete closed loop fuel control routine. 

## Outline

Before we get into the details, a brief outline of what this code does might be helpful. I'll assume you understand the general idea behind closed loop fueling, and just concentrate on how the code achieves that. 

We can break this into stages:
1. look up the correction step values (from rpm/load maps)
2. update the current correction value using the step values from #1
3. apply thresholds
4. clamp the final correction value
5. apply the final correction

The size of the correction step used varies based on whether the current condition is lean or not lean, whether it has just changed, and also by rpm and load. 

In step #1, the rpm/load dependent step values are retrieved from three different maps. In step #2, these values are modified and combined according to the control strategy. The gist of that strategy is like this: if the measured condition just changed to or from a lean condition, then we make a very big correction step in the opposite direction. But if the latest measured condition is the same as the previous one, then we only add a small correction step. The correction accumulates until the condition switches. 

In step #3, various threshold conditions are allowed to temporarily block lambda correction. These are 

* various engine modes (WOT, cranking, coasting)
* rpm
* load
* temperature

In step 4 the final correction is limited to between 0.7x and 1.14x. 

Finally, step 5 applies the correction according to certain timer-based rules. In order for a correction to be applied, the condition it's correcting for has to exist for a certain minimum time, which is measured by the timer variable 3Eh. There are 2 possible actions that can happen in this final application:

1. make a rich/lean correction
2. neutralize the correction

* If the o2 sensor indicates that we're rich or lean, then we wait for the timer to expire, and make the correction.
* If the sensor indicates neither rich nor lean, then we wait for the timer to expire and neutralize the correction value (i.e. set it to 1x)

We'll call the latter situation the *neutral condition*. 

In all cases, the relevant AFR condition must hold *continuously* for the whole timer period. If the condition changes before the timer expires, then the timer gets reset. 

And the timer periods are different for actions #1 and #2! For a rich/lean condition, the timer period is short, and for the neutral condition, it's long. That is, in order for the correction to be neutralized, the AFR must remain neither rich nor lean for a long time. But in order for a correction to take place, the AFR need only be rich or lean for a short time. (For definitions of "long" and "short", watch this space!)

While the timer is counting down, whichever action was happening before simply continues, with any new addition or subtraction based on the control strategy. 

But note also that when the correction step is being calculated, no distinction is made between a *rich* condition, and a *neutral* condition. It's simply *lean* or *not-lean*. Therefore a neutral condition will generally provoke a correction in the lean direction, and so it's unlikely that the timer for neutralizing the correction will go for long without being reset. 

Now we'll get into those stages one by one. 

## The lookup
The looking up of the lambda correction maps starts at the end of the fuel adjustment routine:

```
X1de0:	mov	4eh,r6
	mov	4fh,r7
	ljmp	X1053
```

This 1053 jump just calls 1B39 where we check 20h.7, which is our master flag for closed loop fuel control, set only for appropriately equipped cars:

```
X1b39:	
	jnb	20h.7,X1b3f
	ljmp	X1d15
```

The code at 1D15 seems to be a replacment for the 0A5E (which is unreachable). It just expands on the conditions that select between Maps 62 and 65, although for out purposes this is irrelevant. Once the map is selected, we jump to 0A65 where the rest of the lookups/map selections happen:

```
X1d15:	
	mov	r2,#3eh
	jb	25h.6,X1d1f ; 25h.6=1 means RoW, so 20h.7 would not be set (see 1BEE)
	jnb	t0,X1d1f
	mov	r2,#41h
X1d1f:	
	ljmp	X0a65

...

X0a5e: ;UNREACHEABLE
	mov	r2,#3eh		;Map 62
	jnb	t0,X0a65
	mov	r2,#41h		;Use Map 65 if code plug set
X0a65:	
	lcall	X051d
	mov	18h,a		;18h, for unchanged
	lcall	X051d		;Map 63 or 66
	mov	19h,a		;19h, for changed/lean
	lcall	X051d		;Map 64 or 67
	mov	1ah,a		;1A, for changed/not-lean
	ret	
;

```

The above code only looks up the maps based on rpm and load, and stores the values for later. 

## Updating the correction
The beginning of the actual adjustment routine is called a little later, from 0419 in the post-load calculation routine, via the acall to 1B30:

```
X1b30:	jnb	20h.7,X1b36
	ljmp	X0a75
```

The first part of this routine is concerned with updating the current lambda correction value based on the values we just retrieved from the maps, and the current and previous states of the O2 sensor circuit. 

The previous correction is loaded from 1B:1C into r1:r0. Then we update r1:r0 and store it back into 1B:1C. Later when we actually apply the correction, we use r1:r0. If we end up neutralizing the correction, we overwrite 1B:1C with the neturalized version. 

```
X0a75:	
	jnb	23h.4,X0a7b
	mov	1bh,#80h
X0a7b:	
	mov	r0,1ch		;1Ch, low byte of final correction
	mov	r1,1bh		;1Bh, high byte of final correction
	mov	c,p1.7		;1=lean, according to opendme
	cpl	c
	mov	20h.2,c		;so now 20h.2=0 means lean
	jc	X0a94		;jump if not lean
	jb	24h.6,X0a8e	;24h.6 = previous 20h.2
	lcall	X0bcd		;unchanged/lean
	sjmp	X0aa1
;Changed from not-lean->lean:
X0a8e:	
	clr	a		; call 0BD4 with a=0
	lcall	X0bd4
	sjmp	X0aa1
;Not lean:
X0a94:	
	jnb	24h.6,X0a9c
	lcall	X0bcd		; unchanged/not-lean
	sjmp	X0aa1
;Changed from lean->not-lean
X0a9c:	
	mov	a,1ah		; call 0BD4 with a=1Ah, Map 64
	lcall	X0bd4
X0aa1:	
	mov	1ch,r0		;1Ch
	mov	1bh,r1		;1Bh
	mov	c,20h.2
	mov	24h.6,c		;store new 20h.2 value for next time
	ljmp	X105c 		;jumps to 1CB7, so the code immediately after this is an unreachable version
;
```

Here's the logic of the above section, in pseudo-code:

```
if cranking:
	1B = 1
r1:r0 = 1B:1C
if currently lean:
	if previously lean:
		r1:r0 = call 0BCD
	else if not previously lean:
		r1:r0 = call 0BD4 (with a=0)
else if currently not-lean:
	if previously lean:
		r1:r0 = call 0BD4 (with a=1A, the value from Map 64)
	else if not previously lean:
		r1:r0 = call 0BCD
1B:1C = r1:r0
previously lean = currently lean
```

The 0BCD/0BD4 routines are really one routine with two different entry points - here's the whole thing:

```
; Called when lambda is unchanged
X0bcd:	
	mov	a,18h		; 18h, from Map 62, lambda adjustment for unchanged state
	mov	b,#1
	sjmp	X0bdd
;
; Called when lambda has changed from/to lean.
; This is called with either a=0 or a=1Ah (from Map 64)
; if transition was LEAN->NOT-LEAN, then a=1Ah
; if transition was NOT LEAN->LEAN, then a=0
X0bd4:	
	cpl	a
	inc	a
	add	a,19h		; 19h; this subtracts a from 19h
	mov	b,#10h		; we'll be multiplying by 16, vs by 1 in the unchanged case
	clr	24h.4
;
; Arguments: A, B, R1:R0
; Returns: R1:R0
;
; common path, called either way
X0bdd:	
	mul	ab
	jnb	b.7,X0be4
	mov	b,#7fh		; clamp b to max 127
X0be4:	
	jnb	20h.2,X0bec	; jump if lean - if not lean, we complement b:a and c below
	cpl	c
	cpl	a
	xrl	b,#0ffh		; xor, effectively complements b in place (cpl only works on a)
X0bec:	
	addc	a,r0		; get here if lean or not lean, but b:a is complemented if not lean
	mov	r0,a
	mov	a,b
	addc	a,r1
	mov	r1,a
	clr	a
	jb	20h.2,X0bf8	; jump if not lean
	cpl	c
	cpl	a
X0bf8:	
	jc	X0bfc		; add overflowed
	mov	r0,a		; a=0 if not lean, 255 if lean
	mov	r1,a
X0bfc:
	ret
```

And here's a pseudo code summary of that same routine. Note that __b:a__ is used as a 2's complement signed number. So before complementing, we must clamp to the middle value (high byte 127). After complementing into a negative number if necessary, we add it r1:r0, in which case we have to check for overflow and clamp to 0 or 65356 as appropriate.

```
if unchanged:
	b:a = 18h (from Map 62)
else if lean:
	b:a = (19h - 1Ah) * 16 (19h from Map 63, 1Ah from Map 64)
else if not-lean:
	b:a = 19h * 16
if b >= 127 then b=127 (clamp b:a to roughly 32767)

if lean:
	r1:r0 = r1:r0 + b:a
	if r1:r0 > MAX:
		r1:r0 = MAX
else:
	r1:r0 = r1:r0 - b:a
	if r1:r0 < MIN:
		r1:r0 = MIN
```

## Applying threshold conditions

The next section handles threshold conditions for lambda control, including temperature. Flag 24h.5 (not to be confused with 25h.4!) is a local master switch for all threshold conditions. If it's clear, lambda control is disabled:

```
X1cb7:
	jb	23h.2,X1d0b	; cranking -> clear 24h.5, causing no correction later
	jb	23h.1,X1d0b	; WOT -> clear 24h.5, causing no correction later
	jb	23h.5,X1d0b	; coasting fuel cutoff -> clear 24h.5, causing no correction later
	nop	
	org	1cc3h
	mov	a,#4bh		; 1160 + 4Bh = 11AB, contains 8Eh=166, so 6640rpm
	movc	a,@a+dptr
	cjne	a,37h,X1cc9
X1cc9:
	jc	X1d0b		; clears 24h.5, causing no correction later
	mov	a,#4ch		; 11AC, contains 66h or 102 decimal
	movc	a,@a+dptr
	cjne	a,49h,X1cd1
X1cd1:
	jnc	X1ce8		; c=1 if a < 49h, i.e. if 49h > 102, so jnc jumps if 49h <= 102
	jnb	24h.5,X1d0b	; clear 24h.5, no correction if load > 102
				; (this could probably happen at mid-range rpm/high throttle)
	jb	24h.1,X1ce2	; check the 3F timer if we were previously in this condition (load > 102)
	setb	24h.1		; we just hit load > 102 for the first time, this flag starts the timer
	clr	24h.2		; doesn't appear to be set by any reachable code
	mov	a,#4dh		; 11AD, contains 6
	movc	a,@a+dptr
	mov	3fh,a		; 3F <- 6

X1ce2:
	mov	a,3fh
	jz	X1d0b		; if the timer expired, clear 24h.5, so no correction
	sjmp	X1cea		; the timer hasn't expired yet, so don't cancel correction just yet
;
X1ce8:
	clr	24h.1		; jumped here from the load comparison - if load dropped below 102,
				; clear 24h.1 (results in the timer being reset next time)

X1cea:
	jnb	25h.4,X1cf1	; patched-in condition: if 25h.4 is clear, use normal temp threshold logic
	mov	a,#6eh		; patched-in alternate constant/table offset
	sjmp	X1cf8
;
X1cf1:
	mov	a,#49h
	jb	23h.0,X1cf8
	mov	a,#48h		; 48h and 49h (11A8 and 11A9) both contain 58h/88 dec., roughly 16.7C

X1cf8:
	movc	a,@a+dptr
	mov	r2,a
	jb	24h.5,X1d01	; if correction is already enabled somehow, don't add the other temp value
	mov	a,#4ah		; 11AA, contains 7 which is equivalent to an addition of around 4.6C
	movc	a,@a+dptr
	add	a,r2		; roughly 21C

X1d01:
	clr	c
	subb	a,13h		; 13h = coolant temperature
	mov	24h.5,c		; set 24h.5 if coolant temperature is above the threshold
	lcall	X0b50		; clamping routine for r1:r0
	sjmp	X1d0d       ; jumps to 0AFB (see below)
```

In pseudo code:

```
if cranking or WOT or coasting:
	clear 24h.5
if rpm >= 6640:
	clear 24h.5
if load > 102:
	if 24h.1: # means we had previously entered this condition
		if 3F = 0: # check the timer
			clear 24h.5
	else: # we just entered this condition, set the timer
		set 24h.1
		clear 24h.2 # unused
		3F = 6 # timer value loaded from 11AD
else:
	clear 24h.1 # load went below 102 without the timer expiring, so cancel the whole business

if 25h.4: # if this is set, it means NTCII was < ~15C during cranking
	threshold = 50C # 11CE, contains 8Ch/140
else:
	threshold = ~17C
if not 24h.5: # lambda is currently blocked by some threshold
	threshold = threshold + 5C # hysterisis
if 13h > threshold:
	set 24h.5
else:
	clear 24h.5

call clamping routine
call main adjustment routine
```

A few notes about this:

The flags 25h.4 and 25h.5 are both set during the cranking phase. Each one corresponds to an engine temperature threshold, and is set if the engine temperature was below that threshold during cranking. But both thresholds are set to the same value, around 15C. Only 25h.4 is used here. The way that 25h.4 is used here means that there are two different temperature thresholds for enabling lambda control. If the temperature was below ~15C while cranking, then lambda control is only enabled above 55C. Otherwise it's enabled from around 22C. 

Also note the hysterisis logic: once lambda control is activated based on the initial temp threshold, it won't get deactivated unless the temp falls to around 5C below that temperature - this prevents it from switching on and off constantly if the temperature happens to be hovering around the threshold. 

The comments in the pseudo code above note that 24h.2 is unused; more on that later. 


The next section is where the correction logic is actually applied.


## Apply the correction

```
X0afb:	
	lcall	X105f		; 105F->1E36 (monitoring/debugging)
	jnb	p1.6,X0b18	; Lambda: jump if rich
	jb	p1.7,X0b18	; Lambda: jump if lean
	jb	24h.3,X0b10
; lambda is ok
	setb	24h.3		; this gets cleared when we go rich/lean at 0B18, so this one probably means lambda is OK
	clr	24h.4		; this gets set the first time we enter the rich/lean code at 0B18, clearing it means the timer will reset next time we go rich/lean
	mov	a,#43h
	movc	a,@a+dptr
	mov	3eh,a		; lambda timer
X0b10:	
	mov	a,3eh		; lambda timer
	jnz	X0b2e		; lambda is ok and the timer has NOT expired so keep doing the previous correction (?)
	clr	24h.7		; lambda is ok and the timer HAS expired, so we can stop correcting now
	sjmp	X0b2e
;
; rich or lean
X0b18:	
	jb	24h.4,X0b28	; 24h.4 seems to indicate that we *just* went rich/lean, so set up some flags and reset the lambda timer
	setb	24h.4		; presumably this block only needs to run the first time we go rich or lean
	clr	24h.3		; lambda not OK any more
	clr	24h.2		; doesn't appear to be set by any reachable code
	setb	24h.0
	mov	a,#44h
	movc	a,@a+dptr
	mov	3eh,a		; reset the lambda timer
X0b28:	
	mov	a,3eh		; lambda timer
	jnz	X0b2e
	setb	24h.7		; timer reached zero, so clear lambda-OK flag, otherwise 24h.7=0 will inhibit rich/lean correction below
X0b2e:	
	mov	c,24h.5		; we could get here with the timer expired or not expired
	anl	c,24h.7
	anl	c,24h.0
	mov	24h.5,c		; 24h.5 = master switch for correction 1=do correction 0=don't
	jc	X0b42		; if ALL flags are set, do a correction, otherwise the code below wipes it out to 1
	mov	r0,#0
	mov	r1,#80h
	mov	1ch,r0		; 1Ch, low byte of lambda correction
	mov	1bh,r1		; 1Bh, high byte of lambda correction
	clr	24h.2
X0b42:	
	ljmp	X1062   ; this just jumps to 0B45, below
;
X0b45:	
	lcall	X0455		; 16x16 bit multiply
	mov	a,#1
	lcall	X0509		; left-shift 24-bit value
	ljmp	X1065
;
```

And here's the logic:

```
if rich or lean:
	if not 24h.4: # 24h.4=1 means the rich/lean timer has already been started
		set 24h.4
		clear 24h.3 
		clear 24h.2 # unused
		set 24h.0
		3E = 9 # lambda timer, loaded with 11A4, which contains 9
	if timer = 0:
		set 24h.7
	if 24h.5 and 24h.7 and 24h.0:
		apply the change in r1:r0
	else:
		r1:r0 = 1B:1C = 32767
		clear 24h.2 (unused)
else: # lambda ok (not rich or lean)
	if not 24h.3: #24h.3=1 means the OK timer has already started
		set 24h.3
		clear 24h.4
		3E = 66 # lambda timer, loaded with 11A3, containing 24h/66
	if timer = 0:
		clear 24h.7
	if 24h.5 and 24h.7 and 24h.0: # this will now fail because 24h.7=0
		apply the change in r1:r0
	else:
		r1:r0 = 1B:1C = 32767, i.e 1
		clear 24h.2 (unused)	
apply the correction to the r7:r6 fuel value # via 16x16 mul routine
multiply by 2
```

So 24h.4 is the flag that indicates we're in the rich/lean timer phase. And 24h.3 indicates that we're in the lambda neutral timer phase. To see how these flags work, let's consider a a few hypothetical examples. 

Let's say there was previously a correction for a rich or lean condition, and 24h.7 is set. Suppose that we have entered the above code with the lambda condition having just changed to neutral. Then 24h.3 will get set, and the timer 3F will get initialized with the value 66. But until the timer reaches zero, 24h.7 remains set, so the ```jc	X0b42``` instruction will run and the correction will still happen, with whatever update was calculated earlier. Now suppose the neutral condition persists long enough for the timer to reach zero. Then 24h.7 gets cleared, and the correction will get neutralized at 0B38. 

But conversely, let's say the neutral condition *doesn't* last that long, and instead gets interrupted by a transition back to rich or lean. We don't care which at this point, since the direction of the correction was handled by the signed calculation earlier. But now we'll take the path at 0B18, which clears 24h.3. In this particular example, 24h.7 was still set, because the netural timer never expired, so the correction can start happening immediately. But in the case where the neutral timer *had* expired, and 24h.7 had been cleared, then it would only get set again after timer expires at 0B28. 

Note that *three* flags all have to be set in order for the correction to proceed: 24h.5, 24h.7 and 24h.0. If any of these are clear, then the correction is neutralized at 0B38. We have already seen that 24h.5 is the thresholds flag from earlier. 24h.7 is the rich/lean vs neutral indicator. But so far 24h.0 is unexplained. In fact it's not used - it's related to 24h.2, and both are part of a watchdog routine that is deactivated in the final version of the code. We'll see the details a little later. For now, just trust that 24h.0 is always set. 

Finally we multiply r7:r6 (the existing fuel adjustment) by r1:r0, and then multiply by 2. Recall that our lambda adjustment value is a signed 2's complement number, so the max value is half the 16-bit range, with higher values representing negative numbers. Multiplying it by 2 restores the scale to match the existing 16-bit fuel correction r7:r6. 

## Clamping

The clamping routine is called earlier, at the end of the threshold section. I mentioned earlier that there is an unused watchdog algorithm that involves 24h.2 and 24h.0. The implementation of that routine can be seen here, but it's not used because the ```cjne	a,#0ffh,X0b7f``` instruction uses the value 11A5, which is 255, so the jump to 0B7F will never happen. The code at 0B7F is the only place that 24h.2 ever gets set. 

Since the upper limit here is high byte=147, that gives a maximum lambda adjustment of around 1.15x. The lower limit is 90, giving around 0.7x. 

```
; This routine short circuits if r1 is between 90 and 147.
; If outside that range, then it's clamped to that range.
; So this is the lambda clamping routine, and the limits are presumably
; 90/128 and 147/128, i.e. 0.7x - 1.14x
; Arguments: R1:R0

X0b50:	
	mov	a,#46h		; 11A6, contains 93h/147 dec.
	movc	a,@a+dptr
	mov	r3,a		; r3 <- 147
	clr	c
	mov	a,r1		; r1 is the high byte of the current lambda correction factor
	subb	a,r3
	jc	X0b5d		; jump if r1 < 147 (probably 147/128, i.e. 1.14x)
	mov	r0,#0		; r0 is the low byte, set to zero if r1 >= 147
	sjmp	X0b67		; set 24h.0, check timer, clr 24h.0 if expired, return
;
X0b5d:	
	mov	a,#47h		; 11A7, contains 60h, 90 dec. (presumably 90/128, i.e. 0.7x)
	movc	a,@a+dptr
	mov	r3,a
	clr	c
	subb	a,r1
	jc	X0b89		; jump if r1 > 90, this returns
	mov	r0,#0ffh	; set low byte to 255
; if we get here then either r1 > 147 or r1 < 90
X0b67:	
	mov	a,r3		; a <- 147 or 90 depending on how we jumped here
	mov	r1,a
	mov	1ch,r0		; 1Ch, low byte of lambda correction
	mov	1bh,r1		; 1Bh, high byte of lambda correction
	jb	24h.1,X0b89	; return. 24h.1 was previously noted as flagging that lambda correction is load-inhibited (49h > 102)
	jb	24h.2,X0b83	; check timer, clr 24h.0 if timer=0, return
	mov	a,#45h		; 11A5, contains FFh, 255
	movc	a,@a+dptr
	cjne	a,#0ffh,X0b7f	; this will never jump since 11A5 does contain 255
	clr	24h.2
	setb	24h.0
	sjmp	X0b89
;
X0b7f:	
	setb	24h.2		; unreachable?
	mov	3fh,a
X0b83:	
	mov	a,3fh
	jnz	X0b89
	clr	24h.0
X0b89:
	ret
```

Here's the logic that actually happens here - it could hardly be simpler:

```
if r1 < 147 and r1 > 90: 
		return
else if r1 >= 147:
	1C = r0 = 0
	1B = r1 = 147
else if r1 <=90:
	1C = r0 = 255
	1B = r1 = 90
return
```

For completeness here's a brief explantion of the unused watchdog logic too:

```
if 24h.1=1: # this indicates that timer 3F is busy with load threshold
	return
	
if 11A5 != 255:
	set 24h.2
	3F = 11A5
else:
	clear 24h.2
if 3F = 0:
	clear 24h.0 # this neutralizes lambda correction (see above)
```

First note that the timer, 3F, is the same one used for the load threshold earlier. If its currently being used for that, we skip this watchdog logic entirely. 

Next we check the constant 11A5, and if it's anything other than 255, then we use it as a timer value for 3F. We set 24h.2 so that indicates that we're in the watchdog countdown mode. 

But recall that 24h.2 is cleared earlier when the lambda state transitions. So this logic, if active, would detect when the correction is pegged to the rails for a certain time, and neutralize the lambda correction in that case. 
