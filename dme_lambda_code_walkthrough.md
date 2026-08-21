```
	mov	r2,#3eh		;Map 62
	jnb	t0,X0a65
	mov	r2,#41h		;Use Map 65 if code plug set
X0a65:	lcall	X051d
	mov	rb3r0,a		;18h, for unchanged
	lcall	X051d		;Map 63 or 66
	mov	rb3r1,a		;19h, for changed/lean
	lcall	X051d		;Map 64 or 67
	mov	rb3r2,a		;1A, for changed/not-lean
	ret	
;
X0a75:	jnb	23h.4,X0a7b
	mov	rb3r3,#80h
X0a7b:	mov	r0,rb3r4	;1Ch, low byte of final correction
	mov	r1,rb3r3	;1Bh, high byte of final correction
	mov	c,p1.7		;1=lean, according to opendme
	cpl	c
	mov	20h.2,c		;so now 20h.2=0 means lean
	jc	X0a94		;jump if not lean
	jb	24h.6,X0a8e	;24h.6 = previous 20h.2
	lcall	X0bcd		;unchanged/lean
	sjmp	X0aa1
;Changed from not-lean->lean:
X0a8e:	clr	a		; call 0BD4 with a=0
	lcall	X0bd4
	sjmp	X0aa1
;Not lean:
X0a94:	jnb	24h.6,X0a9c
	lcall	X0bcd		; unchanged/not-lean
	sjmp	X0aa1
;Changed from lean->not-lean
X0a9c:	mov	a,rb3r2		; call 0BD4 with a=1Ah, Map 64
	lcall	X0bd4
X0aa1:	mov	rb3r4,r0	;1Ch
	mov	rb3r3,r1	;1Bh
	mov	c,20h.2
	mov	24h.6,c		;store new 20h.2 value for next time
	ljmp	X105c ;jumps to 1CB7, so the code below is unreachable
;
```


My comments added to the alternate (actually used) version by chatgpt:
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
	subb	a,rb2r3		; rb2r3 = 13h = coolant temperature
	mov	24h.5,c		; set 24h.5 if coolant temperature is above the threshold
	lcall	X0b50		; clamping routine for r1:r0
	sjmp	X1d0d
```

```
X1d0b:	clr	24h.5
X1d0d:	ljmp	X0afb

```

```
X0afb:	
	lcall	X105f		; 0afb   12 10 5f   .._
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
	mov	rb3r4,r0	; 1Ch, low byte of lambda correction
	mov	rb3r3,r1	; 1Bh, high byte of lambda correction
	clr	24h.2
X0b42:	
	ljmp	X1062
;
X0b45:	
	lcall	X0455		; 16x16 bit multiply
	mov	a,#1
	lcall	X0509		; left-shift 24-bit value
	ljmp	X1065
;

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
	mov	rb3r4,r0	; 1Ch, low byte of lambda correction
	mov	rb3r3,r1	; 1Bh, high byte of lambda correction
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

```
; Called when lambda is unchanged
X0bcd:	
	mov	a,rb3r0		; 18h, lambda adjustment for unchanged state
	mov	b,#1
	sjmp	X0bdd
;
; Called when lambda has changed from/to lean.
; This is called with either a=0 or a=1Ah (from map 64)
; if transition was NOT LEAN->LEAN, then a=0
X0bd4:	
	cpl	a
	inc	a
	add	a,rb3r1		; 19h; this subtracts a from 19h
	mov	b,#10h		; we'll be multiplying by 16
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


Original code with no comments:
```
X0afb:	
	lcall	X105f
	jnb	p1.6,X0b18
	jb	p1.7,X0b18
	jb	24h.3,X0b10
	setb	24h.3
	clr	24h.4
	mov	a,#43h
	movc	a,@a+dptr
	mov	3eh,a
X0b10:	
	mov	a,3eh
	jnz	X0b2e
	clr	24h.7
	sjmp	X0b2e
;
X0b18:	
	jb	24h.4,X0b28
	setb	24h.4
	clr	24h.3
	clr	24h.2
	setb	24h.0
	mov	a,#44h
	movc	a,@a+dptr
	mov	3eh,a
X0b28:	
	mov	a,3eh
	jnz	X0b2e
	setb	24h.7
X0b2e:	
	mov	c,24h.5
	anl	c,24h.7
	anl	c,24h.0
	mov	24h.5,c
	jc	X0b42
	mov	r0,#0
	mov	r1,#80h
	mov	rb3r4,r0
	mov	rb3r3,r1
	clr	24h.2
X0b42:	
	ljmp	X1062
;
X0b45:	
	lcall	X0455
	mov	a,#1
	lcall	X0509
	ljmp	X1065
;
X0b50:	
	mov	a,#46h
	movc	a,@a+dptr
	mov	r3,a
	clr	c
	mov	a,r1
	subb	a,r3
	jc	X0b5d
	mov	r0,#0
	sjmp	X0b67
;
X0b5d:	
	mov	a,#47h
	movc	a,@a+dptr
	mov	r3,a
	clr	c
	subb	a,r1
	jc	X0b89
	mov	r0,#0ffh
X0b67:	
	mov	a,r3
	mov	r1,a
	mov	rb3r4,r0
	mov	rb3r3,r1
	jb	24h.1,X0b89
	jb	24h.2,X0b83
	mov	a,#45h
	movc	a,@a+dptr
	cjne	a,#0ffh,X0b7f
	clr	24h.2
	setb	24h.0
	sjmp	X0b89
;
X0b7f:	
	setb	24h.2
	mov	3fh,a
X0b83:	
	mov	a,3fh
	jnz	X0b89
	clr	24h.0
X0b89:	ret
```

```
X0bcd:	mov	a,rb3r0
	mov	b,#1
	sjmp	X0bdd
;
X0bd4:	cpl	a
	inc	a
	add	a,rb3r1
	mov	b,#10h
	clr	24h.4
X0bdd:	mul	ab
	jnb	b.7,X0be4
	mov	b,#7fh
X0be4:	jnb	20h.2,X0bec
	cpl	c
	cpl	a
	xrl	b,#0ffh
X0bec:	addc	a,r0
	mov	r0,a
	mov	a,b
	addc	a,r1
	mov	r1,a
	clr	a
	jb	20h.2,X0bf8
	cpl	c
	cpl	a
X0bf8:	jc	X0bfc
	mov	r0,a
	mov	r1,a
X0bfc:	ret
```
