# A Walkthrough of the Fuel Routine

The main fuel adjustments are done by the routine starting at 1D23 (note: the opendme annotations incorrectly call this routine "lookup_dwell_angle". 

It starts with this section:

```
X1d23:	
	mov	dptr,#X112e
	lcall	X05cd
	clr	acc.2
X1d2b:	
	add	a,#1bh
X1d2d:	
	movc	a,@a+dptr
	mov	b,a
	mov	r2,#2ah
	lcall	X051d
	mul	ab
	mov	r7,b
	mov	r6,a
	mov	50h,#2
```

We start by loading the FQS map location into dptr and then calling the map lookup routine 05CD. Bit 2 of the resulting value is cleared (that bit is used only for timing adjustments). 

Here's what this FQS map looks like:

FQS voltage at ADC | 0 | 0.68 | 1.43 | 2.0 | 2.4 | 2.66 | 2.94 | 3.14
--|------|------|------|------|------|------|------|
FQS switch position | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7

This map takes the FQS value (read by the ADC) as input and maps it to the range 0-7, indicating which of the eight possible positions the switch is in. 

Clearing bit 2 has the effect of mapping the second four positions onto the first - in other words, for fueling purposes, positions 4-7 are identical to 0-3. (The only difference with these later 4 positions is that they also include an ignition timing change.)

Recall that the map lookup routine restores the dpts to it's "home" value of 1160, so adding our FQS map value to 1B before the dptr lookup gets us to __1160 + 1B + fqs_value__, that is, __117B+fqs_value__. The locations starting at 117B contain:

| FQS Position | Hex value | Decimal value | Effect on fuel |
|--------------|--------------|--------------|--------------|
|0 |  80h |  128 | 0 |
|1 |  84h | 132 | + 3.1% |
|2 |  7Ch | 124 | - 3.1% |
|3 | 88h | 136 | + 6.25% |

Recall from XX that fuel adjustment values are generally fractions with a denominator of 128, so 128 means "multiply the fuel pulse by 1" and 132 means "multiply the fuel pulse by 132/128, that is ~1.031. More on this shortly. 

So now we have stored our FQS value in b, and next we look up map 42 (2Ah). Map 42 is the air temperature correction map and its raw form is

| Air temperature (C) | Value |
|---|---|
| -34.61 | 144 |
| -13.55 | 138 |
| 16.71 | 128 |
| 55.53 | 128 |

The value from this is multiplied with our FQS value in b and we store the result in r7:r6. 

At this point we should take a moment to consider how this fraction based interpretation is implemented in the code. Otherwise the code we're about to walk through would be more confusing that it needs to be!

The most efficient way for the 8051 to divide by 128 is to divide by 256 and multiply by 2. The reason for this is that dividing by 256 is very easy - almost free, and multiplying by 2 is also very easy. 

The routine at 1DFO takes care of this, and uses 50h to keep track of how many times the value should be doubled. This is why 50h is set to the value 2 at the end of the code above: we performed 2 lookups that use this /128 pattern. 

Returning to the code at hand, we check if 25h.7 is set. This bit being set indicates that the altitude sensor is active, which corresponds to an altitutde of > 1000M. If this is set, we do a dptr lookup for 1160+6B=11CB, which contains the value 78h, that is 120 decimal. 

The call to 1DF0 multiplies r7:r6 by the value in a and shifts to the left (i.e. doubles) the number of times specified in 50h. The multiplication or r7:r6 with a will result in a 24-bit value r7:r6:r5, but the next time we call 1DF0, it will again use just r7:r6, discarding r5, thus effectively dividing by 256. 

At this point, r7:r6 contains the product of the FQS, air temperature and altitude adjustments. 

Then:

```
X1d44:	jnb	23h.2,X1da9
```

The bit 23h.2 indicates that the engine is cranking; thus what follows is startup-specific code that we'll skip over for now. In steady-state operation, the code will jump to 1DA9, so we'll pick things up there. This is where warm-up enrichment is incoroporated. 

The warm-up enrichment is a little complicated - it's a 2-map process. First the basic temperature adjustment is looked up from one map based on engine temperature. But then this adjustment value is scaled by the value from another map based on rpm and load. We'll get into the details now but I just wanted to give a brief overview of this first. 

```
X1da9:	
	jb	25h.5,X1db0
	acall	X1ff2
	ajmp	X1db3

X1db0:	
	lcall	X1d10	
```

Here we check the flag 25h.5 which is a coolant temperature threshold flag that's triggered at around 70C. [TODO: does 1 mean above or below 70C?]

Recall that the last map we looked up was 42. The map lookup routine uses r2 for the map number, and it generally incrememnts this location after a lookup. So right now r2=43. 

If the 25h.5 flag is set, then we call 1D10 which just adds 2 to r2. That gets us map 45. Otherwise, we call 1FF2 which selects a map based on region coding - this will just be 43 for US cars, 44 for RoW, and 45 or 46 for certain specific countries. 

These maps are very similar - they take engine temp (NTC II) as input and return fuel adjustment multipliers. Here's Map 43 (location 1465h):

| Engine Temperature (C) | Value |
|---|---|
| -34.61 | 166 |
| -13.55 | 90 |
| -3.03 | 67 |
| 11.45 | 45 |
| 16.71 | 15 |
| 69.34 | 0 |

Next:

```
X1db3:	
	lcall	X051d
	mov	b,a
	mov	r2,#2fh
	jnb	23h.0,X1dbe
	inc	r2
X1dbe:	
	lcall	X051d
	mul	ab
	mov	a,b
	acall	X1de7
```
Here we get the value for map 43 and then we load 47 (2Fh) into r2 for the next map lookup. But if the TPS is at the idle position, then we incremenent r2 so that we'll be looking up map 48 instead. 

These maps contain scaling factors for the temperature adjustments. Here's what they look like:

Map 47 (part throttle and WOT, location 1473h):

| RPM (0x37) \ Load (0x49) | 40 | 80 | 140 |
|---|---|---|---|
| 1000 | 255 | 255 | 255 |
| 3000 | 255 | 255 | 192 |
| 5000 | 255 | 179 | 128 |

Map 48 (idle, location 1486h):

| RPM (0x37) | Value |
|---|---|
| 520 | 255 |
| 1520 | 255 |

These two follow a slightly different rule from the fuel adjustment maps we've seen so far: with these, the denominator is 255. So a value of 255 indicates no effect, and 128 will reduce the warm-up enrichment value from map 43 by half. This rule is implemented by the routine 1DE7, which in turn calls 1DF0 which we discussed earlier. 

At this point we add the startup enrichment value 3C; this was calculated in the part we skipped over, but it follows the same rule as the warmup enrichment in that the denominator is 255, so it needs 1DE7 to be called:

```
	mov	a,3ch
	acall	X1de7
```

Next we handle the main driving mode maps: idle, part throttle, and WOT. 

```
	mov	r2,#31h
	jb	23h.0,X1dd6
	mov	r2,#4bh
	jb	23h.1,X1dd6
	mov	r2,#4fh
X1dd6:	
	acall	X1ff2
	lcall	X051d
	acall	X1df0
```

This is now pretty straightforward. We initialize r2 (the map number variable) with map 49 (31h) which is the idle fuel map. Then we check if we're at idle and if not, we replace it with 75 (4Bh) which is the WOT map. Then we check if we have the WOT condition (23h.1=1) and if not, we finally set r2 to 79 (4Fh) which is the part throttle fuel map. 

Next we call the region-based map selection routine 1FF2 (discussed earlier), then the map lookup routine, and finally our accumulation routine 1DF0 which we discussed earlier. 

Finally, we store our complete fuel adjustment values in 4Fh:4Eh. 

```
X1ddd:	
	ljmp	X1050 ; this ultimately just jumps to 1DE0 below 
X1de0:	
	mov	4eh,r6
	mov	4fh,r7
	ljmp	X1053
```

And that's pretty much it for this particular fuel adjustment routine. But I think it's helpful to jump away to another routine to see where these values actually get used. So, the code below is run just after the base pulse width is calculated, as discussed [here](dme_load_calculation.md).

What this code does, in brief is:
* multiply the base pulse width in r7:r6 by the adjustment value we just calculated in 4F:4E
* look up the injector dead-time map based on battery voltage and store the result in 54h
* store the final fuel value into 4B:4A - these will be the timer high and low bytes for the routine that controls the injectors

The routine at 0455 is a 16x16 bit multiply routine that produces a 24 bit result (the lowest byte is discarded). 

The next part is a little tricky to understand. Recall that earlier we saw how 50h was used to keep track of how many times our fuel calculation needed to be multiplied by 2, and also that these multiplications were done by shifting the bits to the left. But the routine that handles that (0509, both here and in 1DF0) stops in its tracks if the value in the leftmost bit is a 1. Otherwise we'd lose information when we shift that bit out to the left. That can happen sometimes in 1DF0 because we're working with 24 bit values. Here, the 16x16 multiply produces a 32 bit result, which opens up more space, so if there are any outstanding multiplies needed, 50h will have a record of that and we can do it here. 

This is a pretty complicated way of doing it - why not leave all the bit shifting until this point? Honestly I don't know, but that's how it works. 

The reason for the __pop 50h__ instruction is that 50h was previously pushed onto the stack because the acceleration enrichment routine uses its own copy of 50h. We'll cover that in another article though. 

```
X0405:	
	ljmp	X1032
X0408:	
	push	50h
X040a:	
	ljmp	X1035 ; call acceleration enrichment routine
```

```
X040d:	
	mov	r0,4eh
	mov	r1,4fh
	acall	X0455
	mov	a,50h
X0415:	
	acall	X0509
	pop	50h
	lcall	X1038
	mov	r2,#1ah
	acall	X051d
X0420:	
	mov	54h,a
X0422:	
	clr	ea
	mov	4bh,r7
	mov	4ah,r6
	clr	ie0
	setb	ea
	lcall	X103b
	jnb	23h.6,X043a
	mov	r1,#50h
```

## Appendix A: FQS Measurements

Actual voltages measured at the FQS channel on the ADC:

0 - 0
1 - 1.143v
2 - 1.754v
3 - 2.281v
4 - 2.516v
5 - 2.839v
6 - 3.048v
7 - 3.254v

## Appendix B: The Accumulation Routines 1DF0 and 1DE7

First, dividing by 256 is handled by simply discarding the lowest byte of a multi-byte product. Let's say we have a 16-bit value (like the base fuel pulse for instance) stored in r7:r6. If we multiply this by an 8-bit value, the result will be a 24-bit value in r7:r6:r5. Now suppose that some time later we need to do another multiplication by another 8-bit value. If we treat r7:r6 as a 16-bit number, and just repeat the multiplication process we did before, then we have discarded the lower byte of the first result (r5), effectively performing a rough division by 256. It can be hard to spot this in the code, because there's no explicit step to discarding r5 - we simply don't use it in subsequent multiplications!

Next, mutiplying by 2 is nothing more than shifting the bits to the right. 

In the fuel adjustment code that we're looking at, there are helper routines that take care of this division by 128. We won't get into every detail here, but for now, just remember that:

* 1DFO multiplies the value in __a__ by r7:r6 and later code effectively divides by 256 by simply ignoring the lower byte __r5__. 
* 50h keeps track of how many times to we need to multiply by 2.
