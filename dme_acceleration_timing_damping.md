# DME ignition timing damping

## Overview
In the [ignition timing real time](ignition_timing_code.md) code walkthrough, we saw that an acceleration adustment value (57h) is added to the main timing value 31h when calculating the final counter value. Here we'll see where 57h comes from. 

The idea is to detect if rpm is increasing or decreasing, and how quickly, and then make a small timing adjustment to create negative feedback - that is, if accelerating, we retard timing, if decellerating, we advance it. The likely reason for this is to reduce jitter at low rpm/light load. 

The possible outcomes of this routine are:

* accelerating: 57h = 1
* decellerating: 57h = -1
* neither: 57h = 0

Of course since 57h gets added to the main timing value in half-teeth form, a value of 1 represents ~1.36 degrees. 

This routine runs during the __timer1__ interrupt routine which controls the [idle stabilizer](isv_routine.md), during the low period of the PWM signal - so every 11.5ms. 

Just detecting whether rpm is increasing or decreasing is very simple. But this routine does more than that. It measures the *speed* of the change in rpm, and uses that to determine the *duration* of the adjustment. The code can be a little tricky to decipher, but it's a very elegant routine and a good way to think of it is that there's a previous rpm value (55h) that *chases* the current rpm (37h). While it's lagging, the timing adjustment is applied, and when it catches up, the adjustment is removed. But the speed at which 55h chases 37h is proportional to the size of the gap between them. The result is that the correction lasts for a duration that's roughly logarithmic with respect to the size of the gap - and since the code runs at regular intervals, the size of the gap is a measure of the speed of rpm increase. 

The correction is only applied at or below 2560rpm, and with load at or below 90, which is somewhere in the region of half the maximum load. For perspective, the maximum load value used in the part throttle timing maps is generally 142. 

## Code
```
X030c:	
	mov	a,#18h		;1178h, contains 40h/64
X030e:	
	movc	a,@a+dptr	;a=64, and 64*40=2560
	cjne	a,37h,X0312
X0312:	
	jc	X0378
	jb	23h.4,X0378
	mov	r5,55h
	mov	a,37h
	clr	c
	subb	a,r5
	mov	f0,c ; f0=1 if current rpm is lower (55h>37h)
	jnc	X0323 ; jump if current rpm is equal or higher
	cpl	a
	inc	a ; remove sign if negative
X0323:	
	xch	a,b
	mov	a,#15h ; 1175h, contains 8
	movc	a,@a+dptr
	mul	ab ; b:a = rpm_delta * 8
	mov	r6,a
	jb	acc.7,X0331
	xch	a,b
	jz	X0333
X0331:	
	mov	r6,#7fh ; low byte clamped to 127
X0333:	
	mov	a,56h
	jnb	f0,X0347 ; f0=0 if 37h>=55h 
	clr	c
	subb	a,r6
	jnc	X0353
	add	a,#80h
	cjne	r5,#0,X0343
	sjmp	X0353
;
X0343:	
	dec	55h
	sjmp	X0353
;
X0347:	; rpm is DECREASING
	add	a,r6 ; a=56h
	jnc	X0353
	add	a,#80h
	cjne	r5,#0ffh,X0351
	sjmp	X0353
;
X0351:	inc	55h
X0353:	
	mov	56h,a
	mov	a,#19h ; 1179, contains 5Ah/90 dec.
	movc	a,@a+dptr
	cjne	a,49h,X035b
X035b:	
	mov	a,#0
	jc	X0374
	mov	a,55h
	cjne	a,37h,X0366
	sjmp	X036d
;
X0366:	
	jc	X0371
	mov	a,#16h ; 1176h, contains 1
	movc	a,@a+dptr
	sjmp	X0374
;
X036d:	
	mov	a,#0
	sjmp	X0374
;
X0371:	
	mov	a,#17h ; 1177h, contains ffh/255, i.e. -1
	movc	a,@a+dptr
X0374:	
	mov	57h,a
	sjmp	X0381
;
X0378:	
	mov	55h,37h
	mov	56h,#80h
	mov	57h,#0
X0381:	jnb	23h.2,X03a7

```

In psedudo code, this is

```

if startup or rpm > 2560:
	55h = 37h
	56h = 127
	57h = 0
	[end of routine, continutes to 0381]
	
b:a = (37h - 55h) * 8
if a > 128:
	r6 = 127
else:
	if b = 0:
		r6 = a
	if b != 0
		r6 = 127

# so r6 is capped at 127 if the whole product was > 127. If a <= 127 then it's only used if b=0, otherwise if b !=0 then r6 gets clamped to 127. 

a = 56h
if 37h < 55h: # rpm is decreasing
	if r6 <= 56h:
		a = 56h - r6
	if r6 > 56h:
		a = 56h - r6 + 128
		if 55h !=0:
			55h--
else if 37h >= 55h: # rpm is increasing
	a = 56h + r6
	if (56h + r6) > 255:
		a = 56h + r6 + 128
		if 55h != 255:
			55h++

56h = a # now a equals either 56h - r6 or 56h + r6

if load > 90:
	57h = 0
if 37h = 55h:
	57h = 0
else if 37h > 55h:
	57h = -1
else if 37h < 55h:
	57h = 1
	
```

In even plainer terms, we could describe it like this:

```
Maintain a slowly-following RPM reference (55h).

If current RPM is above that reference:
    temporarily retard ignition by 1°.

If current RPM is below that reference:
    temporarily advance ignition by 1°.

Move the reference toward current RPM at a rate proportional
to the RPM difference (i.e. an exponentially slowing rate)
```

## Appendix: variables, flags, maps and constants

Everything the damping routine (030C) touches. See the [memory map](dme_memory_map.md) for the master list.

### Byte variables

| Location | Purpose |
|----------|---------|
| 37h | engine speed (rpm/40) |
| 49h | load, checked against the ceiling of 90 |
| 55h | the lagging rpm reference that chases 37h |
| 56h | fractional accumulator controlling how fast 55h chases 37h |
| 57h | the resulting timing adjustment (+1, -1 or 0 half-teeth) |

### Bit flags

| Flag | Purpose |
|------|---------|
| 23h.4 | startup — resets 55h, 56h and 57h and skips the routine |

### Maps and constants

| Reference | Address | Purpose |
|-----------|---------|---------|
| 1160+15h | 1175h | gain applied to the rpm delta (8) |
| 1160+16h | 1176h | retard step written to 57h when rpm is rising (1) |
| 1160+17h | 1177h | advance step written to 57h when rpm is falling (FFh, i.e. -1) |
| 1160+18h | 1178h | rpm ceiling above which the routine is skipped (64, i.e. 2560rpm) |
| 1160+19h | 1179h | load ceiling above which 57h is forced to zero (5Ah, i.e. 90) |

