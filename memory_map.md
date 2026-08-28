# Map of known variables

## Byte Variables
37h engine speed (rpm/40, see 0042)
49h load (high byte of the base fuel pulse, see 03FF)

2Bh ignition event counter (local to speed sensor interrupt routine)
2Ch previously calculated ignition event counter (based on ref sensor, overwrites 2B)
2Dh KLR trigger counter
2Eh previously calculated KLR trigger (based on ref sensor, overwrites 2D)
2Fh dwell angle (overwrites 30h in 0243)
30h dwell angle
31h base timing advance counter
33h counter to next TDC
35h cylinder firing index
3Dh acceleration enrichment (all rpm)
4Ah low byte of fuel pulse (timer ticks)
4Bh high byte of fuel pulse
4Ch acceleration enrichment (<=2480 rpm)
4Eh low byte of fuel adjustments
4Fh high byte of fuel adjustments
57h timing acceleration adjustment

## Flags
20h.0-6 local logic flags for ISV closed loop control
20h.2 re-used to indicate current lambda is lean (0=lean, 1=not lean)
20h.7 master switch for lambda control, 1=do lambda
20h.2 lambda condition 1=lean
24h.6 previous lambda condition
21h.4 loop flag for phasing out cranking enrichment
21h.7 latching flag for 4Ch (accleration enrichment, 1=pending)
23h.0 idle (1=TPS at idle, 0=TPS not at idle)
23h.1 WOT (1=WOT, 0=not WOT, where WOT is controlled by the KLR so that > 65 deg. = WOT)
23h.2 Cranking (1=rpm is < 160)
23h.3 Idle control code path (normal vs. alternate, set via ADC Ch. 5/DME pin 28)
23h.4 startup ??
23h.5 1=costing fuel cutoff
23h.6 ??
22h.0 half-tooth correct for ignition events
22h.1 the other half-tooth correction for ignition events
24h.0 unused lambda watchdog flag
24h.1 lambda timer flag for load threshold
24h.2 unused lambda watchdog flag
24h.3 lambda timer flag for neutral phase
24h.4 lambda timer flag for rich/lean phase
24h.5 lambda threshold flag, 1=all thresholds are met
24h.7 flag for lambda timer expiration, 1=ok to make a correction
24h.6 previous lambda measurement (i.e. 20h.2) - 0=previously lean, 1=previously not lean
24h.7 indicates if current lambda state has persisted long enough; 0=lambda ok, stop correcting, 1=lambda rich or lean, start correcting

25h.4 1=NTC II was below ~14.7C while cranking (used for lambda, and possibly used for timing?)
25h.5 1=NTC II below ~14.7C while cranking (used to select between warmup maps 43 and 45)
25h.7 Altitude sensor (1=altitude above 1000M)
26h.6 Region coding; 0=US, 1=RoW(1.8k) 0 20h.7 ON, 1 turns is off
20h.7 Appears to gate lambda (0=no lambda loop). Controls whether 25h.4 and 25h.5 get set (1=they do based on logic below, 0=they get cleared)

## Constants

| Location | Offset from 1160 | Hex | Decimal | Notes |
|----------|----------|----------|----------|----------|
11A3 | 43 | 42h | 66 | lambda timer for OK
11A4 | 44 | 9h | 9 | lamnda timer for rich/lean


## Maps
3 1447 13h rpm threshold for clearing 23h.2 cranking flag
40 1566 13h warmup enrichment, below 65C
41 1570 12h heat soak enrichment, above 65C

## Some flag setting logic

### Region coding stuff:

=== 1-Axis Map ===
Address: 1296
Input variable: 0x14
Axis length: 4

        0x14 |    Value
-----------------------
           0 |        1
          46 |        3
         128 |        2
         200 |        0
		 
In volts:
        0x14 |    Value
-----------------------
           0 |        1
          1  |        3
         2.5 |        2
         4.0 |        0
		 
According to opendme, having the altitude sensor open should select 0 (open) and the 1.8k resistor should select 2. Altitude sensor shorted should give 1. 

So,

```
	mov	dptr,#X1296
	lcall	X05cd
	rrc	a
	mov	25h.7,c
	rrc	a
	mov	25h.6,c
```
25h.7 = 0 for US and RoW if open (below 1000M on US cars), 1 if shorted (above 1000M)
25h.6 = 0 for US, 1 for RoW 

Thus 20h.7 only gets set when 25h.6 is clear, i.e US cars (o2 sensor)

### Setting 23h.2 (cranking flag) and 25h.4, 25h.5 (coolant temp thresholds)

* first tps
* then region coding
* then:

```
X1bf0:	
	mov	a,#10h
	movc	a,@a+dptr
	clr	c
	subb	a,37h
	jnc	X1c03
	mov	r2,#3
	lcall	X051d
	clr	c
	subb	a,37h
	jc	X1c21
	ret
;
X1c03:	
	setb	23h.2
	jnb	20h.7,X1c1c
	mov	a,#6fh
	movc	a,@a+dptr
	cjne	a,rb2r3,X1c0e
X1c0e:	
	cpl	c
	mov	25h.5,c
X1c11:	
	mov	a,#6dh
	movc	a,@a+dptr
	cjne	a,rb2r3,X1c17
X1c17:	
	cpl	c
X1c18:	
	mov	25h.4,c
	ajmp	X1c20
;
X1c1c:	
	clr	25h.4
	clr	25h.5
X1c20:	
	ret	
;
X1c21:	
	clr	23h.2
	ret
```

1160+10h = 1170 which contains 4, i.e. 160rpm. 

Thus this code means
```
if rpm > 160:
	a = map_lookup(map 3)
	if rpm > a:
		clear 23h.2
		return
else:
	set 23h.3
	if 20h.7:
		a = dptr(1160+6F=11CF) # contains 55h, i.e. 85, or ~14.7C
		if ntc_ii < a:
			set 25h.5 # note that c is complemented so the logic is backwards
		a = dptr(1160+6D=11CD) # contains 55h, so still 14.7C
		if ntc_ii < a
			set 25h.4
		return
	else:
		clear 25h.4
		clear 25h.5
		return
```

Map 3:

| Engine Temperature (0x13) | Value |
|---|---|
| -34.61 | 18 |
| 2.24 | 20 |
| 45.66 | 20 |

So 720 and 800 are the thresholds for turning the cranking flag OFF, depending on temperature. 
