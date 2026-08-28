# DME ignition timing calculation

```
X1c24:	
	mov	r5,#0
	clr	c
	jnb	23h.2,X1c32 ; cranking
	mov	r2,#49h ; Map 73 (rpm)
	acall	X1cae
	acall	X1cae ; r2=Map 74, engine temp
	ajmp	X1c8c
```
This accumulates the values from Map 73 and 74 into r5. 1C8C ends up in the clamping routine, which is the end of the calculation for this condition. 

```
;
X1c32:	
	jnb	23h.0,X1c47
	mov	r2,#4 ; Map 4 engine temp
	jb	25h.4,X1c3e ;25h.4=1 means NTCII <= ~15C during cranking
	acall	X1ff2 ; region based alternate map selection
	ajmp	X1c41
;
X1c3e:	
	lcall	X1d10; just adds 2 to r2, selecting +2 alternate map
X1c41:	
	acall	X1cae
	mov	r2,#8
	ajmp	X1c88
;
```
If we're at idle, this code looks up Map 4 (or 6 if we had a cold start, but Map 6 is identical to 4 anyway) and accumulates the result into r5, then intializes r2 with Map 8 which is the idle timing map, and jumps to 1C88, which is where the main idle/PT/WOT map lookup is done. 

```
X1c47:	
	jnb	23h.1,X1c50
	mov	r2,#0ch
	acall	X1cae
	ajmp	X1c69
;
X1c50:	
	mov	r2,#12h
	jb	25h.4,X1c59
	acall	X1ff2
	ajmp	X1c5c
;
X1c59:	
	lcall	X1d10 ; just adds 2 to r2, selecting +2 alternate map
X1c5c:	
	acall	X1cae
	mov	a,#20h
	movc	a,@a+dptr
	subb	a,49h
	jc	X1c69
	mov	r2,#5bh
	ajmp	X1c88
;
X1c69:	
	mov	r2,#0dh
	acall	X1cae
	jb	23h.1,X1c72
	mov	r2,#5bh
X1c72:	
	mov	dptr,#X112e
	lcall	X05cd
	jnb	acc.2,X1c88
	mov	a,#21h
	movc	a,@a+dptr
	clr	c
	subb	a,37h
	jnc	X1c88
	mov	a,#22h
	movc	a,@a+dptr
	add	a,r5
	mov	r5,a
X1c88:	
	acall	X1ff2
	acall	X1cae
X1c8c:	
	ljmp	X104a ;this just jumps back to 1C8F (below)
;
X1c8f:	
	mov	r2,#48h
	acall	X1cae
	mov	r0,a
	mov	c,acc.7
	mov	a,#23h
	jnc	X1c9b
	inc	a
X1c9b:	
	movc	a,@a+dptr
	mov	r1,a
	jnc	X1ca0
	xch	a,r0
X1ca0:	
	clr	c
	subb	a,r0
	jnc	X1ca6
	mov	a,r1
	mov	r5,a
X1ca6:	
	mov	a,r5
	mov	c,acc.7
	rrc	a
	mov	r5,a
	ljmp	X104d
;

```
X1cae:	
	lcall	X051d ; map lookup routine, input in r2, output in a
	add	a,r5
	clr	c
	subb	a,#14h
	mov	r5,a
	ret	
```

This routine simply does:

```
r5 += map_lookup(r2) - 20

```


## Maps

Map 4:

**1-Axis Map** (address `13bc`, input variable `Engine Temperature (0x13)`)

| Engine Temperature (0x13) | Value |
|---|---|
| -34.61 | 38 |
| 16.71 | 13 |
| 75.26 | 20 |

Map 6 (identical to Map 4)

Map 73:

**1-Axis Map** (address `13cc`, input variable `Engine RPM (0x37)`)

| Engine RPM (0x37) | Value |
|---|---|
| 120 | 28 |
| 400 | 50 |
| 920 | 50 |

Map 74:
**1-Axis Map** (address `13d4`, input variable `Engine Temperature (0x13)`)

| Engine Temperature (0x13) | Value |
|---|---|
| -31.97 | 27 |
| 19.34 | 20 |
| 75.26 | 13 |
