# Acceleration enrichment

## Why acceleration enrichment?
Before getting into the 944's acceleration enrichment, it's worth discussing what acceleration enrichment even is, and why its needed. This is a well documented topic, so I won't go into too much detail. And I should probably add that unlike most of what you read in these articles, I don't know this first hand. I'm basically summarizing what you can read elsewhere. But this is fairly well establshed, uncontroversial science. So here goes:

The fuel sprayed by the injectors doesn't all go directly into the cylinders. Some of it sticks to the walls of the intake, and can even condense and form a liquid pool. Obviously this means there's less fuel going into the cylinders than intended. But a portion of the pool evaporates, and this evaporated fuel *does* get injested by the cylinders. Eventually the pool grows to the point where the evaporation matches the fuel that's being added to the pool, which is exactly the amount that the cylinders were missing. So the AFR ends up being correct, and the pool is in equilibrium. 

Let's say we have 80% of the injected fuel going directly into the cylinders, 20% going into the pool, and the same 20% evaporating from the pool, and being consumed by the cylinders. Then imagine that the throttle is increased quickly. If the DME responds in proportion to the new airflow, then the cylinder will only get 80% of the increased fuel. The rest will go into making the pool bigger.  What we'd like to happen is that the evaoporation of the pool should also increase to make up the remainder - and this will happen eventually. But it doesn't happen immediately - in fact it's worse than that, because the evaporation of the pool actually *decreases* now, just when we need it to increase, because we increased the pressure in the manifold, slowing evaporation. In effect, the pool acts like a low-pass filter, damping down any attempt to suddenly increase fueling. 

So the engine will run lean for a brief moment, causing a stumble. Eventually, the pool will get bigger and evaporation will catch up, and the engine will return to a new steady-state with the correct AFR. But the fundamental problem is that the DME can only control a proportion of the fuel entering the cylinder. It can't control the evaporation from the pool directly. 

This problem is universal in port injected and carburettor engines. It's why carburettors have an accelerator pump. When you tip the throttle in, extra fuel is added, beyond what the airflow rate would suggest is needed. People call this "acceleration enrichment" - but it's really more about preventing that brief lean stumble. 

You might be accustomed to thinking of acceleration enrichment as the really rich AFR you see under high load, or under boost etc. But that's really there to keep temperatures under control, prevent knock, and make power. This enrichment is generally handled by the fuel maps. The fuel maps can't help us with this transient tip-in problem though, because they only take account of fairly steady-state conditions, and not the suddenness with which we *got* to that state. 

## How the 944 handles it
Now that we know why we need acceleration enrichment, we can get into how the 944 Motronic system handles it. There are actually three sources of enrichment:

1. the natural spike in airflow during throttle opening
2. software based low-rpm enrichment added during warmup
3. software based all-rpm enrichment (added during warmup only for O2/car equipped cars, otherwise present at all temperatures)

The first of these deserves some explanation even though it's not part of the software we're analyzing here. When the throttle setting is low, the pressure in the manifold is low. When the throttle is opened, airflow into the manifold accelerates quickly, and the pressure starts to increase quickly. At the same time, the cylinders start getting increased airflow due to the increasing manifold pressure. After a brief time, the manifold pressure will stabilize at a new steady pressure, but until this happens, the airflow through the AFM is significantly higher than the eventual new steady-state flow. This extra airflow is not all being consumed by the cylinders - it's raising the pressure of the manifold. You can think of the manifold as a kind of reservoir that has to be filled up to a new level. 

So, for a brief time, the AFM is signalling more airflow to the DME than the cylinders are actually consuming, causing the base fuel calculation to run rich. And that's exactly what we need!

To the best of my knowledge, the fact that this works well is basically luck. Considering it from first principles, there's no obvious reason why the amount of overshoot should match what we need. Obviously it's *directionally* correct - it creates enrichment at the right time. And it's at least *vaguely* proportional too - the more agressive the throttle increase, the bigger the overshoot in airflow we'd expect to see, which feels right. But will the overshoot be the *just* right size? There doesn't seem to be any pricinple that guarantees this. There's probably some tolerance here - as long as we get enough extra fuel, getting a bit more probably isn't a big deal. 

But another aspect of this solution that we shoudn't take for granted is: how long does this spike last? The load/base fuel pulse calculation is done in the timer routine that handles the idle stabilizer valve, during the low period of the ISV PWM signal. That means it runs at ~87Hz, or every ~11.5ms. At low rpm, that means that the base fueling is re-calculated multiple times between injection events (for instance at 1200rpm there's 50ms between injections, so up to 4 fuel calculations can happen). In fact we have to go above roughly 2600rpm to reach a point where only one fuel calculation can happen between injection events. So for this enrichment strategy to work, the AFM overshoot needs to last long enough that it can't practically be missed, and thus overwritten by a leaner calculation before it gets used. 

The code we're going to look at next does have the ability to help with these concerns, but apparently there is no real need for this on a fully warmed-up engine. 

Let's take a look at some real world data. This was captured while pulling away from a stop in first gear, at very low rpm. 

* Red is the raw AFM signal
* Blue is the fuel injector signal
* Green is the idle statbilizer valve (ISV) PWM signal

![](images/acceleration_enrichment/first_gear_low_rpm_afm_overshoot_2.png)

The reason that the ISV signal is relevant here is that the base fuel calculation happens during the same timer interrupt that controls the ISV, during the low period of the signal. So it provides some rough information on when the injector base pulse width is calculated, relative to the enrichment overshoot in the AFM signal. It's not precise because it's hard to say exactly when during the low period the calculation happens, but it's a useful hint. 

Zooming in to take some measurements, we can see a few interesting things:

![](images/acceleration_enrichment/first_gear_low_rpm_afm_overshoot_closeup_2.png)

I've positioned the AFM voltage cursors to measure the approximiate size of the overshoot, and the horizontal cursors roughly where the base fuel pulse calculation is happening for the two overlapping injection events. What does all this tell us? Well it clears up one thing: the overshoot clearly does last long enough to get picked up and factored into at least one fuel pulse calculation, even at low rpm. It only gets better at higher rpm, since there are more injection events in a given time. 

We can also get something from the magnititude of the overshoot. Here it's in the order of 190mv or so. That would be measured as ```255 * (0.19/5) ~= 10``` by the ADC. And we know that each such unit represents about a 1.9x increase in airflow (based on the curve fitting at the end of [this artcle on load calculation](dme_load_calculation.md)). Thus we can estimate the enrichment factor as ```1.019^10 ~= 1.2```. So this little bump could give us up to 20% enrichment for one injection, or a bit less than that for two successive injections. Of course one injection event provides only half the fuel for each cylinder due to the batch injection strategy, so we're probably looking at a ~10% enrichment here. This was light or moderate acceleration. If you give the throttle a good jab the overshoot can be quite a bit higher than this. 

Now that we have a good understanding of the basic enrichment strategy, let's look at a high level outline of how the software enhancements work. 

## Software based enrichments
Both of the software acceleration enrichments use a single measurement of vane speed. For this, the raw AFM signal (location 10h) is used, and it's rotated through a queue of 3 previous readings (not including the current reading). The current reading is compared with the last one in the queue. Since this code runs every 11.5ms (synchronized with the ISV) that means we're measuring the change in raw airflow roughly over a 35ms period. 

You might wonder why use the raw AFM signal, since this is the logarithm of the actual airflow. Wouldn't it make more sense to use the linearized measurement? Well it turns out the log measurement makes a lot more sense, because it represents a constant proportional change, regardless of airflow. That is, if we measure a change in vane position of say 16 units, then we know from ```1.019^16 ~=1.35``` that this represents a 35% increase in airflow *regardless* of the current baseline airflow. 

Both of our enrichment types use this proportional change in airflow as a scaling factor, which gets combined with a temperature map value. But that's more or less where the similarity ends. 

There are some minor differences but the really big one is what the final calculation represents. In the all-rpm enrichment (ultimately stored in 3Dh), it's unsurpisingly a fractional multiplier, just like the warmup and other enrichments discussed [here](dme_fuel_enrichments_overview.md). But the low-rpm enrichment (4Ch) is just added to the fuel pulse in the real time code, just before the injector is turned on. It's scaled by a constant (64), but the value of the current main fuel pulse plays no role. In this regard it's a lot like a carburettor "pump shot" - it represents a bigger proportional increase at low load/rpm conditions. 

Some other differneces in the two enrichment strategies:

* the all-rpm 3Dh version uses a load/rpm map for scaling in addition to the vane-delta and temperature maps
* both have mechanisms for ensuring that the enriched fuel pulse won't get overwritten before it's used, but they're different:
  * the 3D version is based around the [software counters](dme_software_timers.md), so it gets phased out over time, but new calculations can replace 3D if they are larger, extending the duration
  * the 4Ch (low-rpm) version is never integrated into the main fuel pulse. Instead a latch flag is used (21h.7) to ensure that 4C gets added to the final fuel pulse just before the injectors fire, but only once. Once this is done the flag is cleared and 4C gets calulated again from scratch. 
* the 4Ch version is only active above a vane-delta value of 16, that is ~35% increase in airflow within the last 35ms. 
* while both use temperature based maps that phase out the enrichment with increasing temperature, the all-rpm 3Dh version remains active for non O2/cat equipped cars at all temperatures. 

## The code
The acceleration enrichment routine is located at 1F8E. There are two kinds of enrichment implemented here, both based on the speed of the AFM vane, among other variables:

* low rpm only (<=2480)
* all rpm

This code is called from the timer interrupt routine that controls the idle stabilizer (during the low period of the ISV signal), so it's called at ~87Hz, or roughly every 11.5ms. The vane-delta measurement is made from the 3rd value in a queue (locations 51, 52 and 53), so from that we can see that the value r3 ends up getting is roughly "change in airflow per ~35ms". 

Also, base on the curve fitting at the end of [this artcle on load calculation](dme_load_calculation.md), we know that an increase of one unit (as read by the software from the ADC) corresponds to a roughly 1.9% increase in airflow. We can use this to put some meaning on these vane-delta values. 


```
X1f8e:	
	jb	23h.2,X1fe1
	jb	23h.0,X1fe1
	clr	c
	mov	a,rb2r0		; rb2r0 = 10h = AFM voltage
	subb	a,53h
	jc	X1fe1
	mov	rb0r3,a		; rb0r3 = 3
	mov	a,#37h		; 37h = engine speed (teeth per 1/87.6th sec)
	movc	a,@a+dptr	; look up some map value for engine speed?
	clr	c
	subb	a,37h
	jnc	X1faa
	mov	b,#0
	ajmp	X1fb7
```
If cranking or idle, jump away to 1FE1. 

The locations 51, 52, 53 form a queue of previous raw AFM wiper values. 

If 10h (AFM raw value) < 53h (#3), i.e. airflow is DECREASING:
	jump to 1FE1 (same location as idle/cranking jump)
	
r3 = airflow delta
Look up 1160+37=1197=3E (62)
if rpm <= 62*40 (2480):
	jump to 1FAA
else:
	b = 0
	jump to 1FB7
	
```
X1fb7:	
	jb	21h.7,X1fbd ; don't overwrite 4C with a new value (including zero) if there's a pending value
	mov	4ch,b
```

Since we jumped here with b=0, now we have 4C = 0.

```
X1fbd:	
	mov	r2,#21h ; Map 33, rpm delta based on r3
	lcall	X051d
	jz	X1fe1 ; bail out (same exit point as idle/cranking etc.)
	mov	b,a
	mov	a,4ch
	jz	X1fcc
	setb	21h.7 ; set if 4Ch !=0, which only happens if rpm <= 2480, prevents 4C from being overwritten before being used
X1fcc:	
	acall	X1ff2 ; alternate map selection
	lcall	X051d ; Map 34 (13h, zero above 55C for US map, for RoW 55C->19)
	mul	ab ; b contains Map 33 value, based on airflow delta in r3
	mov	r2,#26h ; Map 38, rpm/load, fractions /256
	lcall	X051d
	mul	ab
	mov	a,b
	cjne	a,3dh,X1fdd ; 
X1fdd:	
	jc	X1fe1
	mov	3dh,a ; 3Dh = max(a, 3Dh)
X1fe1:	
	mov	53h,52h
	mov	52h,51h
	mov	51h,rb2r0 ; 10h (current airflow signal). So we're comparing current with 3 measurements ago, or 11.5*3 ~=35ms ago. 
	mov	a,3dh
	lcall	X1de7
	ljmp	X040d		; post-load routine
```

So the value in 3D is the combined map values for airflow delta, temperature, and load/rpm. 


If we had rpm <= 2480, then we jumped to 1FAA:

```
X1faa:	
	mov	r2,#1ch ; Map 28, airflow delta based on r3
	lcall	X051d
	mov	b,a
	acall	X1ff2 ; select alternate
	lcall	X051d ; Map 29, 13h based, zero above 41C for US and RoW
	mul	ab
X1fb7:	
	jb	21h.7,X1fbd
	mov	4ch,b
X1fbd:	
	mov	r2,#21h
	...
```
	
So Maps 28 and 29 give the 4C value (airflow delta and temp). This value is applied in the real time routine just before the injectors fire. Then 21h.7 is cleared. This way, 21h.7 prevents 4C from being overwritten in a subsequent call to this routine before it's used. Assuming this routine is called at 87Hz (post-ISV routine), we calculate 4C at least twice per rpm up to 2640rpm. Above that, 4C would get used before the next call to here, so 21h.7 wouldn't be needed. 

The 3Dh value is phased out by the prescaled counter routines and the max clamping at 1FDD prevents it from being reduced faster than that. 

What's the significance of the queue of 3 previous AFM values? If this code runs every ~11.5ms, that means we're comparing the current measurment to the one from 35ms ago, regardless or rpm or load. 

Also, why do we use the raw (log) signal for this and not the linearized load signal? Suppose we used a linear scale. Then an increase of say 35 units (in r3) from 40 to 80 would be a 100% increase in raw airflow. But the same 40 unit increase from 100 to 140 would only be a 40%A increase. With the logarithmic scale, an increase in 40 units would always mean that the airflow has doubled. So a given value of r3 always represents the same proportional increase, regardless of the baseline airflow. From the transfer curve function, it looks like each 8-bit ADC unit is worth a ~1.92% increase, so we can visualize the r3 deltas as 1.092^r3:

Map 28:
1	1.9% | 0
3	5.9% | 0
16	35.7% | 0
32	84.0% | 64
48	149.7% | 255

So it takes more than a 35% increase in raw airflow to wake up Map 28 for the low rpm (4C) enrichment. 

Map 33:
2   3.8% | 0
51	164.4% | 255


If rpm > 2480, then it's at least 2520, which is 42 revs/second, so each rev takes 23.8ms. At 2480, it's 24.1ms. That means there's enough time to calculate 4Ch twice before the injector fires, overwriting the previous value. The lowest rpm where this not the case is 2640, which is 66 in /40 units. This explains why 4C needs to be applied in the real time routine instead of being integrated into the main fuel adjustment, and why 21h.7 is necessary. 

It seems that at lower engine temps (<= 40C) the mechanical overshoot of the vane is not enough at least partly because at or below 2480rpm there is a high chance that the enrichment will be overwritten before being applied. 

But then why isn't the all-rpm value in 3D enough? The value in 3D gets decremented every 58ms

### Scale of 4C vs 3D

4C is Map 28 * Map 29, then /256, so basically has the same scale as Map 29 at max vane delta. Say 44 for 11C for example. This gets multiplied by 64 later in the real time routine, then added to the 16-bit fuel pulse. 
