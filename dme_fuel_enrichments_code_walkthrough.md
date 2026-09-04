# A Walkthrough of the Fuel Adjustment Routine

This is a detailed code walkthrough of the main fuel adjustment routine for the 944T DME. For a gentler overview that explains the process without getting into the weeds of the code, see [this overview article](dme_fuel_enrichments_overview.md)

The main fuel adjustments are done by the routine starting at 1D23 (note: the opendme annotations incorrectly call this routine "lookup_dwell_angle". 

We can summarize the adjustments made here like this:
1. FQS
2. Air temperature
3. Altitude
4. Post-start
5. Cranking
6. Warmup
7. Driving mode (idle/PT/WOT)

These are by no means *all* the fuel calculations! They're just the ones that are done in this routine. There is also acceleration enrichment, handled elsewhere, and various other adjustments that will need their own separate articles. But this is the closet thing to a "main" fuel adjustment routine, other than the [base pulse calculation](dme_load_calculation.md).

There's a general pattern in this code roughly like this:
1. look up a fuel adjustment multiplier from a map
2. multiply that by the current adjustment
3. repeat

But there are exceptions! The cranking enrichment in particular is very tricky. 

Throughout this process, the running total is stored as a 16-bit value in r7:r6, and at the end it's stored in 4F:4E

## Fractional values
Now there is one thing that can be hard to keep track of when reading fuel map related code, and I can't avoid explaining this before we get into the code. The fuel adjustment values are generally fractions, most commonly using a denominator of 128, but occasionally other values. Now there's no easy way to store fractions as individual values in a simple 8-bit system like the 8051. Instead, only the numerator is stored, and the division by 128 must happen in the code. But division is generally complicated in a system like this. Luckily, both division and multiplication by powers of 2 are relatively simple (for the same reason that powers of 10 are easy in our everyday decimal system). The way that division by 128 is typically achieved is by:

1. dividing by 256
2. multiplying by 2

The reason that division by 256 is used for this is that it's basically free. Let's say we do something like this:

```
mul ab
mov r4, b
```

The first instruction multiplies 2 8-bit numbers, a and b, producing a 16-bit result with the high byte in b and the low byte in a. Conventionally I usually write this number as __b:a__. But next we store only b for later, effectively discarding a. This is effectively a rough integer division by 256. It's subtle and easy to miss, because it's really something we *don't* do rather than something we do - we just don't bother to keep track of a. 

Having done this, all we need to do next is multiply by 2. This is very easy to do by shifting the bits to the left like this:

```
mov a, r4
rl a
```

Now we have effectively achieved division by 128 with a minimum of instructions. But these two steps can often be very far removed from each other in the code, making it really hard to keep track of things. 

To complicate matters further, our fuel value is stored as a 16 bit number, so instead of using the __mul__ instruction, we will often call the 8x16 multiply routine __04D9__, which  multiplies an 8-bit number with r7:r6, and produces a 24-bit result in r7:r6:r5 - and then we often later call it again, which effectively discards the low byte r5, again in a very subtle, easy-to-miss way. Think of it like this: if the routine takes r7:r6 as input, and returns r7:r6:r5 as output, then simply chaining multiple calls is going to result in a division by 256 each time!

In the fuel adjustment routine we're looking at here, the left-shifts are tracked using the variable 50h. This location keeps track of the number of times we need to multiply by two to get the denominator to come out right. But there are complications with that too, which are explained later. 

One more slight complication is that while most fuel adjustments are in this multiplier form, a few (including warmup enrichment) are represented as additive values. This doesn't really complicate most of the routine though, because the logic of combining all the adjustments together is hidden away in two helper routines, 1DF0 and 1DE7. You can think of 1DF0 as a routine that handles multiplier values, and 1DE7 as an extension of 1DF0 that handles additive values. You'll see one or the other of these routines being called after a map lookup throughout this routine, so knowing this in advance should help a bit. The actual details of these two routines are explained in the Appendix. 

## FQS, intake air temperature, and altitude
On to the routine itself - it all starts with this section:

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

Here's what this raw FQS map looks like:

| 0x17 | Value |
|---|---|
| 0 | 0 |
| 35 | 1 |
| 73 | 2 |
| 102 | 3 |
| 122 | 4 |
| 136 | 5 |
| 150 | 6 |
| 160 | 7 |


Let's render it in a slightly more readable form:

FQS voltage at ADC | 0 | 0.68 | 1.43 | 2.0 | 2.4 | 2.66 | 2.94 | 3.14
--|------|------|------|------|------|------|------|
FQS switch position | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7

This map takes the FQS value in 17h (read by the ADC) as input and maps it to the range 0-7, indicating which of the eight possible positions the switch is in. I've included actual voltage measurements made at the ADC input Channel 7 in the Appendix section. 

Clearing bit 2 has the effect of mapping the second four positions onto the first - in other words, for fueling purposes, positions 4-7 are identical to 0-3. (The only difference with these later 4 positions is that they also include an ignition timing change.)

Recall that the map lookup routine restores the dptr to it's "home" value of 1160, so adding our FQS map value to 1B before the dptr lookup gets us to __1160 + 1B + fqs_value__, that is, __117B+fqs_value__. The locations starting at 117B contain:

| Offset (FQS Position) | Hex value | Decimal value | Effect on fuel |
|--------------|--------------|--------------|--------------|
|0 |  80h |  128 | 0 |
|1 |  84h | 132 | + 3.1% |
|2 |  7Ch | 124 | - 3.1% |
|3 | 88h | 136 | + 6.25% |

So now we have stored our FQS value in b, and next we look up Map 42 (2Ah). Map 42 is the air temperature correction map and its raw form is

| Air temperature (C) | Value |
|---|---|
| -34.61 | 144 |
| -13.55 | 138 |
| 16.71 | 128 |
| 55.53 | 128 |

The value from this is multiplied with our FQS value in b and we store the result in r7:r6. 

Next, we check if 25h.7 is set. This bit being set indicates that the altitude sensor is active, which corresponds to an altitutde of > 1000M. If this is set, we do a dptr lookup for 1160+6B=11CB, which contains the value 78h, that is 120 decimal. 

The call to 1DF0 handles combining this adjustment with r7:r6. 

At this point, r7:r6 contains the product of the FQS, air temperature and altitude adjustments. 

## Cold start enrichments

Next we have:

```
X1d44:	
	jnb	23h.2,X1da9
	mov	r2,#28h
	mov	a,#1fh
	movc	a,@a+dptr
	cjne	a,13h,X1d4f
X1d4f:	
	jnc	X1d52
	inc	r2
X1d52:	
	lcall	X051d
	mov	3ch,a
```

The bit 23h.2 indicates that the engine is cranking; thus what follows is startup-specific code. There are 2 adjustment stages within this cranking-specific block: cranking enrichment, and post-start enrichment. 

The post-start enrichment is handled first. The result will end up in 3C, which is decremented in the main loop. The result is that this kind of enrichment is phased out within around 30 seconds after startup regardless of temperature or rpm. 

If the cranking bit is set, we load map 40 or 41 depending on the coolant temperature. The constant 1F points to location 117F, which contains A2h, or 162 in decimal. This corresponds to about 65C (using [value - 62.6]/1.52). 

If 13h >= this value, c will be set and we'll switch to map 41. Otherwise we stick with Map 40. 

Here is Map 40:

| Engine Temperature (0x13) | Value |
|---|---|
| -13.55 | 90 |
| 16.71 | 45 |
| 35.79 | 51 |
| 55.53 | 0 |

And Map 41:

| 0x12 | Value |
|---|---|
| 41.05 | 0 |
| 55.53 | 39 |
| 65.39 | 39 |
| 75.26 | 39 |

Note that Map 40 uses __13h__ (NTC II, i.e. coolant temperature) while 41 uses __12h__ (NTC I, i.e. intake air temperature). 

The switch over happens at 65C *coolant temperature*, but from the air temp values in the map we can see that Map 41 only makes corrections at very high intake air temps. This is therefore probably for heat-soak enrichment. So we can interpret this logic to mean that above 65C, no compensation is needed for the engine block's temperature, but heat soak is a possibility, to be determined by air temperature. When the block is below 65C presumably there's no risk of running lean from heat soak. 

Also note that these maps are additive, so 1DE7 will be called when 3C is added to the main adjustment a little later. That's all there is to the post-start enrichment, except for the logic that decrements 3C, which happens elsewhere. 

Next we have the cranking adjustment, which is by far the most complicated part of this entire routine. 

First we load Map 83, which looks like this:

| Engine Temperature (0x13) | Value |
|---|---|
| -31.97 | 182 |
| 16.71 | 28 |
| 36.45 | 18 |
| 58.16 | 12 |

These values are fractions with a denominator of 8 as we'll see soon. The value from this map is the base cranking enrichment - but it can be modified. 

There are really two paths through this part of the routine, a simple one and a complicated one. We'll cover the simplest one first: this is where the we have had 12 or fewer rotations, and have not hit 600rpm yet. 

```
	mov	r2,#53h
	lcall	X051d
	mov	r4,a
	mov	r3,#5
	mov	r1,#8
```

The value from Map 83 is stored in r4. Next we set two local variables. The first, r3, is used later as an exponent, so that the final cranking enrichment will be multiplied by 2^r3. Since r3=5, that means 32, which is why Map 83 values are really have a denominator of 8 (the usual division by 256 will happen later). 

There's a reason why the exponent of 5 isn't hard coded as 5 though - we'll see that very soon. Next, r1 represents the denominator of our cranking adjustment multiplier. This is used later to make sure that we don't ever reduce fuel, i.e. if the numerator is less than r1, we'll skip adjustment entirely. As with r3, you'll soon see why this is a variable. 

```
	jb	21h.4,X1d78
	lcall	X051d
	clr	c
	subb	a,37h
	jc	X1d73
	mov	a,#1ah
	movc	a,@a+dptr
	subb	a,4dh
	jnc	X1d95
X1d73:	
	setb	21h.4
	mov	4dh,#0
	
```
Initially, 21h.4 will be clear so we won't jump to 1D78. The section immediately after that flag check can be read as

```
a = read_map(84) # input engine temp, output rpm/40
if rpm > a OR 4D > 12:
	set 21h.4
	4D = 0
	start reducing cranking enrichment...
else: 
	apply the full cranking enrichment from Map 83/8
```

Thus 21h.4 just keeps track of whether the phasing out of this enrichment has been triggered or not. This is necessary because we might exceed the rpm threshold, but then dip back below it again. This flag ensures that the phase out will continue anyway. 

The counter 4D gets incremeted in the real time part of the code, when the fuel injectors are fired. 

Map 84 contains 15 (i.e. 600rpm) for all entries. You might think that if the rpm is this high, then the cranking flag 23h.2 wouldn't be set, so we couldn't even be in this section of the code at all (due to the 23h.2 check back at 1D44). But while 23h.2 is initially set when the rpm is measured at 160rpm, it's not cleared until the rpm exceeds a much higher temperature dependent threshold, which is at least 720rpm (determined by Map 3).

So we'll dig into that phase-out part next. It's based on the combination of two maps, 85 and 86, both of which are straight lines that slope downwards with increasing inputs (injection count and rpm respectively). 

```
X1d78:	
	mov	r2,#55h
	lcall	X051d
	mov	b,a
	lcall	X051d
	mul	ab
```

Don't forget that the map read routine 051D always leaves r2 incremented from its previous input, so the second map read here read map 86. 

The __mul ab__ instruction leaves the high byte in b and the low byte in a. 

Next, recall that the value from Map 83 was stored in r4 earlier, and also that r3=5 and r1=8. Now, our Map 83 value is *normalized* and the exponent is scaled appropriately:

```
	mov	a,r4
X1d84:	
	jb	acc.7,X1d8e
	rl	a
	xch	a,r1
	rl	a
	xch	a,r1
	dec	r3
	sjmp	X1d84
;
```
This is a hard loop to read, but what's happening is that the base value is being scaled up (multiplied by 2) as many times as needed to get it into the range of >128, *but* simultaneously, r1 is scaled in exactly the same way, and r3 is decremented. The end result is that:

```Map 83 * 2^r3```

will come out the same as before, and r1 will represent the new denominator, used for making sure that the adjustment doesn't ever fall below 1. 

The purpose of all this is to get greater precision in the multiplication and division that come next. 

Then

```
X1d8e:	
	mul	ab
	mov	r4,b
	jnb	acc.7,X1d95
	inc	r4
X1d95:	
	mov	a,r4
	cjne	a,rb0r1,X1d99
X1d99:	
	jc	X1da6
```

Recall that b has the high byte of the product of Maps 85 and 86, which decrease with temperature. So the code above multiplies our cranking adjustment value by b and rounds up if the low byte is 128 or higher, then stores the high byte of the result in r4.

Next we skip making the adjustment if our adjustment is less than the adjusted denominator. 

The final section:

```
	lcall	X04d9
	mov	a,50h
	add	a,r3
	lcall	X0509
X1da4:	
	mov	50h,a
X1da6:	
	ljmp	X1ddd
```

The 04D9 routine is the generic 8x16 multiply routine. This applies our final cranking adjustment to the main adjustment value r7:r6. 

Next, 0509 is the left-shit routine that doubles our value by the number indicated by a, if there is room on the left, and stores the number of pending shifts back in a if there isn't room. The explanations of 1DF0 and 1DE7 in the Appendices cover this in more detail.

That's it for the really complicated part! Everything since the test of 23h.2 up to this point applies only during cranking. In steady-state operation, the code will jump from that flag check to 1DA9, skipping all the cranking enrichment stuff, and now we're at 1DA9. This is the warm-up enrichment section, and it's also where the post-start enrichment we calcualted earlier (3C) is incoroporated. 

## Warmup enrichment
The warm-up enrichment is a 2-map process. First the basic temperature adjustment is looked up from one map (43 or 45) based on engine temperature. But then this adjustment value is scaled by the value from another map based on rpm and load (47 or 48). Here are the details:

```
X1da9:	
	jb	25h.5,X1db0
	acall	X1ff2
	ajmp	X1db3

X1db0:	
	lcall	X1d10	
```

Here we check the flag 25h.5 which is a coolant temperature threshold flag that's set to 1 if the coolant temperature is below around 15c. 

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

This map is a little different from the other fuel adjustments in that the values represent additive increases in fuel. That is, a value of 15 for example means "add 15/128". This logic is handled in the 1DE7 routine, which is explained in more detail in the Appendix. 

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

These two follow a slightly different rule from the fuel adjustment maps we've seen so far: with these, the denominator is 256. So a value of 255 (close enough to 1) indicates no effect, and 128 will reduce the warm-up enrichment value from map 43 by half. 

At this point we add the startup enrichment value 3C; this was calculated earlier, but it follows the same pattern as the warmup enrichment so it needs 1DE7 to be called:

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

This is pretty straightforward. We initialize r2 (the map number variable) with map 49 (31h) which is the idle fuel map. Then we check if we're at idle and if not, we replace it with 75 (4Bh) which is the WOT map. Then we check if we have the WOT condition (23h.1=1) and if not, we finally set r2 to 79 (4Fh) which is the part throttle fuel map. 

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

| FQS Position | ADC input voltate |
|--------------|-------------------|
| 0 |  0 |
| 1 | 1.143v |
| 2 | 1.754v |
| 3 | 2.281v |
| 4 | 2.516v |
| 5 | 2.839v |
| 6 | 3.048v |
| 7 | 3.254v |

## Appendix B: The Accumulation Routines 1DF0 and 1DE7

The fuel adjustment routine basically looks up a series of maps and combines the resulting values. That's what we discussed in details in the main article. But we glossed over how the values are combined, because it's complicated and messy. Here we'll discuss that code in detail. 

There are 2 routines here, 1DF0 and 1DE7. Strictly speaking they are different entry points to a single routine, in the sense that if we call 1DE7, then 1DF0 will run also (see the code below). 

The best way to understand these is to look at 1DF0 first. 


```
X1de7:	
	jz	X1dfb
	add	a,#80h
	jnc	X1df0
	rrc	a
	inc	50h
X1df0:	
	lcall	X04d9
	mov	a,50h
X1df5:	inc	a
	lcall	X0509
	mov	50h,a
X1dfb:	ret
```

Starting at 1DF0, first we call 04D9 which is the Motronic's 8x16 multiply routine. This routine multiplies __a__ by r7:r6, with a 24 bit result in r7:r6:r5. 

Generally the code that calls 1DF0 puts the fuel adjustment value in a, and the previous adjustment value is already in r7:r6 (see the start of this article). 

Next we increment 50h and call 0509 which is the left-shift routine. That routine shifts the bits of r7:r6:r5 to the left as many times as indicated by 50h. Crucially, this routine guards the case where the leftmost bit is 1. In that case, it stops shifting the bits, but leaves the number of outstanding shift steps in a. Here, after 0509 returns, we store that value back into 50h. 

Let's think about this for a minute. You know from earlier that the reason for shifting the bits to the left is to multiply by two, and this is needed because it's part of the division by 128. Generally, one map lookup requires one multiplication by two and one division by 256 to get an overall division by 128. But sometimes multiple adjustments are combined without calling 1DF0 (for example, see the beginning of the adjustments earlier). In that case, 50h must be "primed" with the number of such lookups. Thus when 1DF0 is called, 50h could contain 3. But it's quite possible that there isn't enough space to shift the bits of the resulting value to the left without running into the end. In that case, 0509 will stop but it will return a record of the number of shift steps that were omitted in a, and now we're storing that in 50h. 

Later, as we saw in the main article, at 040D, the fuel value is turned into a 32 bit number, which opens up more empty space on the left. At that point we perform the remaining outstanding bit shift steps using the value in 50h. 

This is a really confusing way of handling this. Why not just leave all the bit shifting until 040D? I really have no idea and it was pretty hard to figure out what was going on here. Maybe that was the idea!


Now let's take a look at 1DE7. This routine is used for the warm-up enrichment (which we covered earlier) and acceleration enrichment maps (which we didn't cover here). The difference with these maps is that the values they contain represent *additive* increases in fuel rather than multipliers. 

```
X1de7:	
	jz	X1dfb
	add	a,#80h
	jnc	X1df0
	rrc	a
	inc	50h
X1df0:
	...
X1dfb:	ret
```

Firstly, if __a__ is zero, we short-circuit and return. 

Next we add 128 (80h) to the input value, which has the effect of biasing it to match the existing multiplicative fuel adjustments. For example if the input in __a__ was 15, this step would turn that into 15+128, which is the correct value to multiply the existing fuel adjustment by. In other words it has the same effect as having the value 143 in one of the other maps. Why not just represent it as a multiplicative value of 143? Honestly I don't know. 

Anyway, if this addition doesn't overflow, then we simply call 1DF0 and everything proceeds as before. If there is an overflow, we divide the result by 2 and increment 50h which will cause the final value to get doubled later when there's more room. 

This might seem strange, but when we rotate right, the carry bit (which is set from the overflow) rotates in from the left, leaving us with the overflow value *plus* 128. Thus the effect of this code is to leave us with (a+128)/2, which will be restored to the full value by doubling later. 
An example might make it clearer. Let's say the intput is 166, the highest value from Map 32, corresponding to the lowest temperature. When we do 

```
128 + 166 = 294
```

...we get an overflow, leaving us with a=38 and the carry bit set. Then the rrc instruction turns this into 

```
128 + 19 = 147
```

...because the rrc divides 38 by 2 but also puts the carry bit on the left. 

Now because we incremented 50h, we will eventually double our final value, which restores us to 294. 

## Appendix C: variables, flags, maps and constants

Everything the fuel adjustment routine (1D23) touches, along with the post-load section at 040D. See the [memory map](dme_memory_map.md) for the master list.

### Byte variables

| Location | Purpose |
|----------|---------|
| 11h | system voltage, the axis for the injector dead-time map |
| 12h | intake air temperature (NTC I) |
| 13h | coolant temperature (NTC II) |
| 17h | FQS switch position, as read by the ADC |
| 37h | engine speed (rpm/40) |
| 49h | load |
| 3Ch | post-start enrichment, phased out by the software counter |
| 4Dh | injection event counter, used to phase out cranking enrichment |
| 4Ah | low byte of the final fuel pulse, in timer ticks |
| 4Bh | high byte of the final fuel pulse |
| 4Eh | low byte of the accumulated fuel adjustment |
| 4Fh | high byte of the accumulated fuel adjustment |
| 50h | count of outstanding left shifts (pending multiplications by 2) |
| 54h | injector dead-time |

### Bit flags

| Flag | Purpose |
|------|---------|
| 21h.4 | latch marking that the cranking enrichment phase-out has been triggered |
| 23h.0 | TPS at idle |
| 23h.1 | WOT |
| 23h.2 | cranking |
| 25h.5 | coolant temperature was below ~15C during cranking |
| 25h.7 | altitude above 1000M |

### Maps and constants

| Reference | Address | Purpose |
|-----------|---------|---------|
| FQS map | 112Eh | maps the ADC value in 17h to a switch position of 0-7 |
| 1160+1Bh+FQS | 117Bh-117Eh | fuel offset per FQS position (128, 132, 124, 136) |
| Map 42 (2Ah) | 145Bh | intake air temperature correction |
| 1160+6Bh | 11CBh | altitude correction applied when 25h.7 is set (78h, i.e. 120) |
| 1160+1Fh | 117Fh | coolant threshold selecting Map 40 vs 41 (A2h, i.e. ~65C) |
| Map 40 (28h) | 1566h | post-start enrichment below 65C, by coolant temperature |
| Map 41 (29h) | 1570h | heat soak enrichment above 65C, by intake air temperature |
| Map 83 (53h) | 157Ah | base cranking enrichment, by coolant temperature |
| Map 84 (54h) | 1584h | rpm threshold that starts the cranking phase-out (600rpm) |
| Map 85 (55h) | 158Ah | cranking phase-out scaling, first term |
| Map 86 (56h) | 1590h | cranking phase-out scaling, second term |
| 1160+1Ah | 117Ah | injection count threshold for the cranking phase-out (12) |
| Maps 43-46 | 1465h, 17E8h, 1B14h, 1A00h | warmup enrichment by coolant temperature; 43/44 by region, 45/46 for cold cranking |
| Map 47 (2Fh) | 1473h | warmup enrichment scaling, part throttle and WOT (by rpm and load) |
| Map 48 (30h) | 1486h | warmup enrichment scaling, idle (by rpm) |
| Map 49 (31h) | 1538h | idle fuel map |
| Map 75 (4Bh) | 1544h | WOT fuel map |
| Map 79 (4Fh) | 148Ch | part throttle fuel map |
| Map 26 (1Ah) | 1598h | injector dead-time by system voltage, stored in 54h |

