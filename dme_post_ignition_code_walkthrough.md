# The post ignition routine

This is a code walkthrough of the things that happen after the [spark fires](ignition_timing_code.md). The interesting post-ignition things start at 00F3. 

There's also [an overview](dme_post_ignition_overview.md) of this without the details of the code.

## Ignition timing update
This section updates the ignition advance according to certain rules. 

We start by moving the current spark advance value 31h closer to the new target value, which is stored in 32h. This only happens when the counter 34h reaches zero, and the counter can be initialized with different values to control the rate of change of timing. 

The size of the step that can be added or subtracted is also controlled in the following code. 

```
X00f3:	
	djnz	34h,X012c ; 34h--, bail out if not zero
	mov	r5,#2dh ; 1
	jb	22h.6,X0107
	mov	r5,#2bh ; 1
	jb	22h.5,X0107
X0100:	
	mov	r5,#29h ; 1
	jb	22h.4,X0107
	mov	r5,#27h ; 8
X0107:	
	mov	a,r5
	movc	a,@a+dptr
	mov	34h,a
	inc	r5
	mov	a,r5
	movc	a,@a+dptr
	mov	r5,a
```

The effect of this is simply:

```
34h--
if 34h == 0:
	if 22h.6:
		r5 = 2D
		34h = 1
	else if 22h.5:
		r5 = 2B
		34h = 1
	else if 22h.4:
		r5 = 29
		34h = 1
	else:
		r5 = 27h
		34h = 8
```

This results in the following pairing of 34h and r5:

flag  | 34 | r5
------|----|---
22h.6 | 01 | 01
22h.5 | 01 | 02
22h.4 | 01 | 08
None  | 08 | 01

These flags are set by the logic that controls fuel cut off and reactivation (coasting, gear changes, overload protection). 

As we can see, there's an an order of priority: if 22h.6 is set the the others are not consulted, and so on. The "none" row is the normal one. 

Next the value we put in r5 is used to limit the step change:

```
	mov	a,32h
	mov	r6,a ; r6 = new timing target value 32h
	mov	r7,31h r7 = current timing value
	clr	c
	subb	a,r7
	clr	c
	jnb	acc.7,X0124 ; jump if timing change is positive
	cpl	a
	inc	a ; a = |32h - 31h|
	subb	a,r5 ; r5 = timing change step limit
	mov	a,r6
	jc	X012a ; jump if r5 > delta, i.e. |32h - 31h|
	mov	a,r7
	subb	a,r5 ; a now = 31h - r5
	ajmp	X012a
;
X0124:	
	subb	a,r5
	mov	a,r6
	jc	X012a ; jump if r5 > delta
	mov	a,r7
	add	a,r5
X012a:	mov	31h,a ; 
```

This logic is:
```
	
delta = 32h - 31h
if |delta| < r5:
	31h = 32h
else:
	31h += delta
	
```

## Ref sensor reset and fuel injection
Next comes the "refreset" and checking the cylinder index to see if it's time to fire the injectors. 

```
X012c:	
	mov	a,#1
	movc	a,@a+dptr ; 1161h, contains 2
	inc	35h
	cjne	a,35h,X0143
	mov	35h,#0
	mov	dptr,#X0000
	movx	@dptr,a
	movx	@dptr,a
	movx	@dptr,a
	movx	@dptr,a
	mov	dptr,#X1160
	ajmp	X0166
;
```

We increment the cylinder index 35h, and if it's equal to 2 then we kow we have just fired the spark for the second cylinder in this rev, so we reset it to zero, and it's time to reset the reference sensor latch. That's what the sunsequent dptr instructions do. Then we jump 0166 to handle the fuel injection - but first let's look at some things we do if this *wasn't* the second spark event in the rev:

```
X0143:	
	jb	23h.2,X0166
	jbc	21h.7,X014b
	ajmp	X01e5
;
```
If cranking (23h.2), then we jump to the same fuel injection section that we use for the normal injection event (see above). 

### Acceleration enrichment (4C) - extra injection event
If not cranking, then we check (and clear) 21h.7 which is the latch flag for the [low-rpm cold acceleration enrichmement](dme_acceleration_enrichment_code_walkthrough.md) - this flag indicates that there's a pending one-time "pump-shot" stored in 4C. In this case, we perform a one-time extra fuel injection event even between the ignition events for the current rev. The idea is to get the acceleration enrichment as soon as possible after the extra air has been detected. 

```
X014b:	
	mov	b,#40h
	mov	a,4ch
	mul	ab
	mov	r6,a
	mov	r7,b
	jnb	21h.2,X01bb ;21h.2 means injection is ON, so jump if OFF
	clr	tr0
	clr	c
	mov	a,tl0
	subb	a,r6
	mov	tl0,a
	mov	a,th0
	subb	a,r7
	mov	th0,a
	ajmp	X01d0
;
```

The above logic multiplies the 4Ch value by 60, which is the scale used for 4Ch maps. Next, if the injectors are not current on, we jump to __01BB__, the section that adds the injector latency (aka dead-time), complements the final pulse, loads it into the timer registers, and starts injeciton. It's complemented because the timer counts *up*, and when it overflows it triggers the interrupt that turns the injectors off. So we always want to load the timer with ```65336 - injector_pulse_ticks```. 

In that branch, we are delivering *just* the 4C pump shot. 

But if injection is already on, then instead of jumping to that routine, we just pause the timer briefly to add our 4C value. Of course, that really means subtract, because we want to *increase* the time before the timer overflows. 

The section at __01D0__ is just a late entry point to __01BB__ - it turns the injectors on (they'll already be on in this case) and starts the timer, but skips adding the injector latency value, since we're adding to an already running injection pulse without actually turning the injectors off. 

It's quite possible that injection would already be happening from the previous normal injection cycle - the 4C enrichment is limited to 2480rpm or less, where there's ~12ms between ignition events, and the fuel injector pulse is capped at around 11.5ms by the load routine. Still, that's close - the final pulse can be much longer than the base pulse, especially during warmup which is when this kind of acceleration enrichment would apply. Additionally, that rpm limit might have been subject to change, so having this logic in place seems prudent. 

Then 01D0 returns from the interrupt, so in this path, we don't do any of what follows. Instead the following stuff will happen after the next ignition event, that is, the normal injection event. 

### The normal injection cycle
So the following section is only reached during the normal injection cycle, i.e. just after the second cylinder spark is fired for this revolution, or while cranking (via __0143__ from earlier):

```
X0166:	
	clr	c
	mov	a,#11h ; 1171h, contains 162, and 40*162 = 6480
	movc	a,@a+dptr
	subb	a,37h
	orl	c,23h.5
	jc	X01de
	
```

This __0166__ section is where the rev limit and other fuel cuts are implemented. The flag 23h.5 is set elsewhere if fuel needs to be cut for either coasting or overload protection. Note that hitting the rev limit doesn't set 23h.5 - but if it is hit, or 23h.5 is already set, we bail out to the end of the interrupt routine without doing anything else really. 

```
	mov	r6,4ah
	mov	r7,4bh
	ljmp	X102c ; just jumps back to 0177 below. 
;
X0177:	
	jb	23h.2,X01bb

```

Now we load the previously calculated fuel pulse 4B:4A into r7:r6. This is the base pulse previously modified by all relevant enrichments (except 4C). 

Next, if cranking, then we proceed to __01BB__ which you might recall from a little earlier is the section that adds injector latency, fires the injectors, starts the timer etc. That means we do an extra injection event while cranking, using the full fuel value from 4B:4A. 

### Transient fuel correction
Next we apply a brief fuel correction if fuel was just reactivated after a shut off for coasting, gear changes etc. The flag 21h.5 gates this entire correction, and 21h.6 indicates whether the condition is return-to-idle or not.

In either case the fuel pulse is modulated for a few injection events, tracked by the injection counter variable 4D. 

For return-to-idle, we apply Map 1140, which pulls the mixture rich, then lean, then a little less rich, and then settles down to neutral. For the other case, we use Map 1150 which just pulls the mixture a little lean and gradually walks it back to 100% over the course of 10 cycles or so. 

```
	jnb	21h.5,X01aa
	mov	a,4dh
	cjne	a,#10h,X0182
X0182:	
	jc	X0190 ; jump is 4D < 16
	clr	21h.5
	jnb	22h.6,X018e
	clr	22h.6
	mov	34h,#1
X018e:	ajmp	X01aa
;
X0190:	
	mov	dptr,#X1140
	jb	21h.6,X0198
	add	a,#10h
X0198:	
	movc	a,@a+dptr
	cjne	a,#40h,X01a4
	jnb	22h.6,X01a4
	clr	22h.6
	mov	34h,#1
X01a4:	
	acall	X04d9
	mov	a,#2
	acall	X0509
```
This means:
```
if 4D >=16:
	clr 21h.5
	if 22h.6:
		clear 22h.6
		34h = 1
	jump to 01AA
if 21h.6:
	a = Map 1140[4D]
else:
	a = Map 1150[4D]
if a !=64:
	if 22h.6:
		clr 22h.6
		34h = 1

# multiply by 2, divide by 256, so really /64
r7:r6:r5 = r7:r6 * a
r7:r6:r5 << 2
```
As usual, the division by 256 comes from the fact that we simply don't use r5, but rather treat r7:r6 as our final result. Thus a value of 64 in Maps 1140/1150 means 1. 

In the above section, if 4D gets to 16 or higher, then we consider the correction to have run it's course and we clear some flags and bail out of this fuel correction section. The flag 22h.6 is the highest priority timing slew regulator, and it's set when 21h.5 and 21h.6 are set (these are the flags that control this fuel correction condition). All that happens in a different routine where the fuel cut off logic is implemented. 

So in summary, we modulate the fuel pulse by the map cell indicated by 4D until 4D reaches 16. Then we clear the ignition slew limiter 22h.6. We also clear that limiter if the map value is 64 (i.e. 1). In these cases we also reset 34h to 1 which will enable the timing slew change to take effect immediately. In plain terms: ignition timing rate of change is temporarily limited while we're making this fuel correction. 

### Acceleration enrichment (4C) - normal injection event
Next we apply the 4Ch acceleration enrichment if the 21h.7 latch flag indicates we should - this is very similar to the 4C logic from earlier, but there we were doing it outside the normal ignition cycle. Now we're in the normal cycle and we need to check the flag again. Last time, we cleared this latch flag, so it will only be set again if the acceleration enrichment routine has commanded another pump shot based on the AFM signal. 

```
X01aa:	
	jnb	21h.7,X01bb
	clr	21h.7
	mov	b,#40h
	mov	a,4ch
	mul	ab
	add	a,r6
	mov	r6,a
	mov	a,b
	addc	a,r7
	mov	r7,a
```
Nothing surprising there; it's multiplied by 64 as before, and added to the fuel pulse. We subtracted it last time, because the timer was already loaded with the main pulse value. But for now we're still working with positive values. Soon we'll complement r7:r6 before loading it into the timer. 

### Injector latency and activating the injectors
```
X01bb:	
	ljmp	X102f ; just jumps to 01BE below
;
X01be:	
	mov	a,54h
	mov	b,#5
	mul	ab
	clr	tr0
	add	a,r6
	cpl	a
	mov	tl0,a
	mov	a,b
	addc	a,r7
	cpl	a
	mov	th0,a
X01d0:	
	clr	ea
	clr	p1.0
	setb	21h.2
	setb	tr0
	setb	et0
	clr	ie0
	setb	ea
```

The first part here just adds the injector latency value from 54h (multiplied by 5) to the main fuel pulse value r7:r6, then __complements__ the final value before setting the timer high and low bytes. The timer counts up so the value we need to load is ```65336 - injector_pulse_ticks```. 

Then we:

* temporarily disable interrupts
* turn the injectors on
* set 21h.2 (used earlier to check if injection was on)
* start timer0
* enable timer0 interrupt (this is where the injector will get turned off)
* clear the external interrupt ext0 flag
* enable interrupts

The timer0 interrupt routine located at __000B__ will turn the injectors off by setting p1.0 and also clears 21h.2:

```
X000b:
	setb	p1.0
	clr	21h.2
	reti	
```

### Wrapping up - incrementing injection event counter 4D
```
X01de:	
	mov	a,4dh
	jb	acc.7,X01e5
	inc	4dh
```

This is where 4D is incremented. It's capped at 128, which is probably just a convenient way of making sure it does't overflow and cause problems when it gets back to zero. It most places where it matters, 4D is initialized to zero when needed. 

```
X01e5:	
	pop	b
	pop	dpl
	pop	dph
	pop	psw
	pop	acc
	ret
```
Finally we restore all the things we pushed at the beginning and return to wherever the interrupt was triggered from. We're using ret and not reti here because earlier in the interrupt routine, we use call/reti to get out of the interrupt context. 
