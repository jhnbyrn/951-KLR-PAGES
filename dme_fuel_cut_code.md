# DME fuel cut (coasting and overload) code walkthrough

This is a brief code walkthrough for the fuel cut off situations. The [overview is here](dme_fuel_cut_overview.md) and I highly recommend reading that first. 

## Overload
This is where we jump to after calculating the new timing value in __r5__. 

```
X0bfd:	
	jb	23h.2,X0c54
	mov	r2,#44h		;Map 68, load by rpm
	lcall	X051d
	mov	r3,a
	jb	21h.1,X0c38 ;21h.1 means we have overload already
	cjne	a,49h,X0c0c
X0c0c:	
	jc	X0c12 ; c means 49h>=max
	clr	21h.0
	sjmp	X0c54 ; clear flag and bail to coasting
;
X0c12:	; we have overload, start counting
	mov	a,#52h ; 11B2, contains 1Ah/26dec
	jb	21h.0,X0c21 ;we're already counting
	setb	21h.0 ;
	movc	a,@a+dptr
	mov	58h,a ; 26
	mov	a,#54h ; 11B4 contains 10 dec.
	movc	a,@a+dptr
	mov	59h,a ; 10  (26*10*11.5ms = ~3s)
X0c21:	
	mov	a,58h
	jnz	X0c54 ; bail out if not zero
	setb	21h.1 ;set overload flag
	mov	a,#53h
	movc	a,@a+dptr
	mov	58h,a ;11B3, contains 29
	mov	a,#55h
	movc	a,@a+dptr
	mov	59h,a ;11B5, contains 180 (29*180*0.0115=~60s)
	setb	23h.5 ;cut fuel
	mov	32h,r5 ;new timing target=latest calculation
	mov	31h,r5 ;current timing = latest calculation
	ret	
;
X0c38: ;we already have overload
	mov	a,58h
	jnz	X0c42
	clr	21h.0 ;release from overload jail
	clr	21h.1
	sjmp	X0c54
;
X0c42:	;we have overload and haven't served the sentence
	mov	a,#51h ;11B1, contains 50
	movc	a,@a+dptr
	cpl	a
	inc	a
	add	a,r3 ;Map 68 value - 50
	clr	c
	subb	a,49h
	jnc	X0c54 ;bail if current load <= Map 68 - 50
	setb	23h.5 ;stay in fuel-cut jail
	mov	32h,r5
	mov	31h,r5
	ret	
;
X0c54:	
	ljmp	X1059
```

In pseudo code, 

```
if cranking:
	return
r3 = map_68[current_rpm]
if 21h.1 (we have overload for > 3 sec already):
	if 58h=0 (30 sec timer expired):
		clear 21h.0 (3 sec timer flag)
		clear 21h.1 (30 sec flag)
		return
	else:
		if current load >= r3 - 50:
			set 23h.5 (cut fuel)
			31h = 32h = r5 (set timing to latest calculation)
			return
else: (we didn't already have overload for > 3 sec):
	if current load <= r3:
		clear 21h.0 (cancel 3 sec timer flag)
		return
	else:
		if 21h.0 (we had already started 3 sec count):
			if 58h=0 (timer expired):
				set 21h.1 (overload flag)
				58h:59h = 30s timer value
				set 23h.5 (cut fuel)
	    else:
		    # start counting 3 second timer now
			set 21h.0 (3 second timer flag)
			58h:59h = load 3 second timer value
```

The timer value 58h:59h is decremented in a short routine that's called via 103E at 0434 (end of post-load routine 040D):

```
;
X0c57:	
	dec	59h
	mov	a,59h
	jnz	X0c6c
	mov	a,#54h
	jnb	21h.1,X0c63
	inc	a
X0c63:	
	movc	a,@a+dptr
	mov	59h,a
	mov	a,58h
	jz	X0c6c
	dec	58h
X0c6c:	
	ljmp	X1056
```

## Coasting aka DFCO
After the overload routine, we jump to 1059 which just jumps to 0708, which is the routine that handles coasting fuel cut off, fuel reactivation (for both coasting and overload) and various ignition timing rules. 

This is a tricky routine and I don't think it makes a lot of sense to break it down, so I'll leave the whole thing as once snippet, but then we'll see a very simple pseudo code version:

```
X0708:	
	jb	23h.2,X0770
	jnb	23h.0,X0732
	mov	r2,#19h
	acall	X051d
	clr	c
	subb	a,37h
	jnc	X073e
	mov	r3,a
	mov	a,#32h ;1192, contains 9
	jb	21h.6,X071f
	mov	a,#31h ;1191, also contains 9
X071f:	
	movc	a,@a+dptr
	add	a,r3
	jc	X0770
	setb	22h.5
	mov	a,r5
	cjne	a,31h,X0770
	setb	23h.5
	clr	22h.5
	mov	32h,a
	mov	31h,a
	ret	
;
X0732:	
	clr	21h.6
	clr	22h.5
	jnb	23h.5,X0770
	mov	a,#2fh ;118F, contains 249, or -6 timing
	movc	a,@a+dptr
	ajmp	X0748
;
X073e:	
	clr	22h.5
	jnb	23h.5,X0770
	setb	21h.6
	mov	a,#30h ;1190, contins ff/255, i.e. -1 timing
	movc	a,@a+dptr
X0748:	
	add	a,31h
	mov	31h,a
	mov	32h,r5
	clr	c
	mov	a,r5
	subb	a,31h
	jnb	acc.7,X0761 ;31h > r5, timing is decreasing
	mov	34h,#1
	mov	4dh,#0
	setb	21h.5
	clr	23h.5
	ajmp	X0770
;
X0761:	
	mov	a,#2dh
	movc	a,@a+dptr ;118D, contains 1
	mov	34h,a
	setb	22h.6
	mov	4dh,#0
	setb	21h.5
	clr	23h.5
	ret	
;
```

The following section has some tricky boolean logic:

```
X0770:	
	clr	c
	mov	a,#25h		;1185, contains 3Ch/60
	movc	a,@a+dptr
	subb	a,49h
	jc	X077e		;jump if load > 60
	mov	a,#26h		;1186, contains 14h/20
	movc	a,@a+dptr
	subb	a,37h
	cpl	c		;now c=1 if rpm<800
X077e:	
	jnb	22h.4,X0782	
	cpl	c		
X0782:	
	jnc	X078f
	cpl	22h.4
```

Working out the effect on 22h.4, we get this

```
	if (49h > 60 or 37h < 800rpm) XOR 22h.4
		cpl 22h.4
```

But that's still kind of unclear, since it doesn't explicitly set 22h.4. But if you work through it, you'll see that this is actually equivalent to

```22h.4 = bool(load>60 or rpm<800)```

The rest of the routine is much easier to understand:

```
	jb	22h.6,X078f
	jb	22h.5,X078f
	mov	34h,#1
X078f:	
	mov	a,r5
	jnb	23h.4,X0798
	mov	31h,a
	mov	34h,#1
X0798:	
	mov	a,r5
	jnb	22h.6,X07a7
	clr	c
	subb	a,31h
	jnb	acc.7,X07a7
	clr	22h.6
	mov	34h,#1
X07a7:	
	mov	32h,r5
	ret
```

In very simple, high-level pseudo code, it's this:

```
if at idle and rpm is at least 360 above threshold:
	if timing has reached target:
		cut fuel
	else:
		return
else if at idle but rpm is below threshold:
	clear 8x timing change speed
	if fuel is currently cut:
		trigger the return-to-idle fuel correction (Map 1140)
		reduce current timing by 1 (half tooth)
		if the new timing target > new current timing:
			set 8x timing change speed
			re-activate fuel
		else:
			re-activate fuel
			jump to 0770
else if not idle:
	clear 16x timing change speed
	if fuel is currently cut:
		reduce current timing by 6 (half teeth)
		trigger return-to-throttle fuel correction (Map 1150)
		if new timing target > new current timing:
			set 8x timing change speed
			re-activate fuel
		else:
			reactivate fuel
			jump to 0770

0770:
	if load > 60 OR rpm < 800 and neither 8x nor 16x timing flags are set:
		set 64x timing flag
	if startup mode:
		set current timing to the new calculation immediatley
	if 16x timing speed is set and timing is decreasing:
		clear 16x timing speed
		
	update timing target (32h) with new calculation
```

That skips over a lot of details, so here's a more detailed version but still in pseudo code:

```
if 23h.0 (idle):
	if rpm > threshold from Map 25:
		r3 = rpm diff (negative)
		if |r3| < 360rpm:
			bail to 0770
		set 22h.5 (timing change flag #2, medium speed)
		if 31h != r5 (current timing != new target):
			bail to 0770
		else:
			set 23h.5 (cut fuel)
			31h = 32h = r5 (current and target timing updated)
			return
	else: (rpm <= fuel cut threshold):
		clear 22h.5 (timing change flag)
		if not 23h.5 (fuel is not cut):
			bail out to 0770
		set 21h.6 (fuel reactivation correction flag)
		31h = 31h - 1 (immediately reduce timing)
		32h = r5 (set new target timing)
		if 31h > r5 (timing is decreasing):
			34h = 1 (trigger timing update)
			4dh = 0 (reset injection event counter)
			set 21h.5 (trigger fuel reactivation correction)
			set 23h.5 (re-activate fuel)
			bail out to 0770
		else:
			(timing is the same or increasing):
			34h = 1 (via 118D)
			set 22h.6 (top timing change flag)
			4dh = 0 (reset injection event counter)
			set 21h.5 (trigger fuel reactivation correction)
			clear 23h.5 (re-activate fuel)
			return
else (not at idle):
	clear 21h.6 (fuel reactivation correction flag)
	clear 22h.5 (second timing change flag)
	if not 23h.5 (fuel is not cut):
		bail out to 0770
	31h = 31h - 6 (immediately reduce timing)
	32h = r5 (set new target timing)
	if 31h > r5 (timing is decreasing):
		34h = 1 (trigger timing update)
		4dh = 0 (reset injection event counter)
		set 21h.5 (trigger fuel reactivation correction)
		set 23h.5 (re-activate fuel)
		bail out to 0770
	else:
		(timing is the same or increasing):
		34h = 1 (via 118D)
		set 22h.6 (top timing change flag)
		4dh = 0 (reset injection event counter)
		set 21h.5 (trigger fuel reactivation correction)
		clear 23h.5 (re-activate fuel)
		return
			
0770:
	if (49h > 60 or 37h < 800rpm):
		set 22h.4 (fastest possible timing change)
		if not 22h.6 and not  22h.5:
			34h = 1 (trigger the timing update)
	if 23h.4 (startup flag, usually not set):
		31h = r5
		34h = 1
	if 22h.6:
		if 31 > r5: (timing is decreasing)
			clear 22h.6
			34h = 1
	32h = r5
```

## Appendix: variables, flags, maps and constants

Everything the overload routine (0BFD), the timer decrement routine (0C57) and the coasting routine (0708) touch. See the [memory map](dme_memory_map.md) for the master list.

### Byte variables

| Location | Purpose |
|----------|---------|
| 31h | current ignition advance, reduced directly on fuel reactivation |
| 32h | target ignition advance |
| 34h | countdown to the next permitted timing step; forced to 1 to act immediately |
| 37h | engine speed (rpm/40) |
| 49h | load, compared against the Map 68 overload threshold |
| 4Dh | injection event counter, reset to zero when fuel is reactivated |
| 58h | overload timer, counted down by the 0C57 routine |
| 59h | prescale counter for 58h |

### Bit flags

| Flag | Purpose |
|------|---------|
| 21h.0 | the ~3 second overload pre-timer is running |
| 21h.1 | overload has been confirmed; the ~60 second lockout is running |
| 21h.5 | triggers the transient fuel correction after reactivation |
| 21h.6 | selects the return-to-idle correction rather than return-to-throttle |
| 22h.4 | fastest timing change rate |
| 22h.5 | medium timing change rate |
| 22h.6 | top priority timing change rate |
| 23h.0 | TPS at idle |
| 23h.2 | cranking — the overload routine returns immediately |
| 23h.4 | startup — applies the new timing calculation immediately |
| 23h.5 | fuel is cut (for coasting or overload) |

### Maps and constants

| Reference | Address | Purpose |
|-----------|---------|---------|
| Map 25 (19h) | — | coasting fuel cut rpm threshold, by engine temperature |
| Map 68 (44h) | — | overload load threshold, by rpm |
| 1160+25h | 1185h | load threshold for the fastest timing change rate (3Ch, i.e. 60) |
| 1160+26h | 1186h | rpm threshold for the fastest timing change rate (14h, i.e. 800rpm) |
| 1160+2Dh | 118Dh | value written to 34h (1) |
| 1160+2Fh | 118Fh | timing step on return-to-throttle reactivation (249, i.e. -6) |
| 1160+30h | 1190h | timing step on return-to-idle reactivation (FFh, i.e. -1) |
| 1160+31h | 1191h | coasting rpm offset, 21h.6 clear (9) |
| 1160+32h | 1192h | coasting rpm offset, 21h.6 set (9) |
| 1160+51h | 11B1h | hysteresis below the Map 68 threshold for staying in overload (50) |
| 1160+52h | 11B2h | 58h reload for the ~3 second pre-timer (1Ah, i.e. 26) |
| 1160+53h | 11B3h | 58h reload for the ~60 second lockout (29) |
| 1160+54h | 11B4h | 59h prescale, 21h.1 clear (10) |
| 1160+55h | 11B5h | 59h prescale, 21h.1 set (180) |
| Map 1140 | 1140h | return-to-idle transient fuel correction |
| Map 1150 | 1150h | return-to-throttle transient fuel correction |
	


