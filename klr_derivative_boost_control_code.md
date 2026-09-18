# KLR boost control spool assist/derivative routine (E30)

This routine uses the rate of change of the boost delta to create a big positive correction to the cycling valve PWM, with the output in 62h. The basic idea is that a sudden increase in the difference between target and actual boost causes a positive output, which then decays smoothly. 

The boost delta is calculated from the actual direct target boost value from the map, 51h. This is unlike the PI routine which uses the *filtered* target boost (53h). 

A peak detection technique is used, so when demand keeps increasing (i.e. throttle opening quickly), larger delta values can replace the previous one. 

The decay is achieved by having a value that chases the peak using the [exponential smoothing](exponential_smoothing.md) routine; the output is the difference between the peak and the chasing value. This way, the initial output depends on the speed of the delta increase, and decays exponentially afterwards. 

Additionally, if the boost delta falls below 1/4 of the peak, the output is neturalized immediately. 

The value is amplified by an exponential gain factor to produce the final output. The [routine for the P and I terms](klr_pi_boost_control_code.md) uses the output of this routine. 

Main variables:

Location | Purpose
--------|--------
52h | current boost
51h | target boost directly from the map
62h | the output of this routine
64h | boost delta
65h:66h | filtered, previous delta based on 64h
6B | PID gain map value (bits 2,3)

```
0xe30 mov  r1,#$52		;actual latest boost measurement
0xe32 mov  a,@r1
0xe33 cpl  a
0xe34 dec  r1			;51h target boost directly from map
0xe35 add  a,@r1 		;c=1 if 51h>52h
0xe36 mov  r1,#$64
0xe38 jnc  $0E56		;jump if c=0, i.e. 52h>=51h
```

We start by subtracting target boost 51h from current boost, 52h. If current boost is higher, i.e. we have an overboost situation, then we jump straight to the end where we effectively zero this term and return. 

Note that 51h is the raw target boost value read directly from the boost map; the other two main terms in the controller use 53h, which is the low-pass filtered target boost. 

```
0xe3a mov  r2,a			;positive delta
0xe3b cpl  a			;complemented delta
0xe3c add  a,@r1		;
0xe3d mov  a,@r1		;overwrites a with 64h, but c is kept
0xe3e jnz  $0E47

```

64h is our peak value as we'll see shortly. If it's zero, then we check 65, which is a low-pass filtered copy of 64h: 

```
0xe40 inc  r1			;65h
0xe41 mov  a,@r1
0xe42 dec  r1			;64h
0xe43 jnz  $0E4B
0xe45 mov  a,r2
0xe46 mov  @r1,a
```

We can think of 65h as following 64h but lagging behind (we'll see how that happens later). Here, we initialize 64h with the delta value from r2 *if* 65 was zero. If 65 it not zero, it means that a previous term is still decaying; we don't calculate a new peak value for 64h in this case. 

```
0xe47 mov  a,r2			;positive delta
0xe48 jc   $0E4B		;
0xe4a mov  @r1,a		;64h = max(64h, delta)
```
This section is what happens if 64 was *not* zero when we checked earlier at E3E. Recall that c was determined earlier when we added 64h to the complement of our delta - thus this section sets 64h to itself or the new delta, whichever is higher. This is the "peak detection" part. 

Next is where we rejoin the main path in the case where 64h was zero but 65h was not - in that case, a will contain 65h, the remaining, decaying term from some previous peak calculation. But as we'll see below, we will end up not using it. 

```
0xe4b clr  c
0xe4c rlc  a
0xe4d jc   $0E58		;
0xe4f rlc  a
0xe50 jc   $0E58
0xe52 cpl  a
0xe53 add  a,@r1		;a = -(delta * 4) + 64h
```
This strange looking code jumps if either bit 7 or bit 6 are set, so it's effectively an "if a < #64" test, and a multiplication by 4 at the same time. In the main path, where 64h is not zero, a contains our positive delta value. So the last part of the above section sets a to 64h - 4*delta. This is just a test though:

```
0xe54 jnc  $0E58
0xe56 mov  @r1,#$0
0xe58 mov  a,@r1
0xe59 jz   $0E73
```

If E53 produced a carry, then we set 64h to zero. In other words, if the current boost delta is less than one-querter of the latest peak, we zero out 64h, and the accumulator, and jump to the end, where our final term will be neutralized. 

But note also that regardless of what happened with the calculation at E53, at E59 we will bail out with a neturalized term if 64h is zero. This is why I said earlier that the decaying value from 65h won't be used. 

Next, we use the value from the gain map, previously loaded into 6Bh based on throttle and rpm:

```
0xe5b mov  r0,#$6B
0xe5d mov  a,@r0
0xe5e rr   a
0xe5f rr   a
0xe60 anl  a,#$3
0xe62 add  a,#$1
0xe64 mov  r7,a			;6B gain map value/4 mod 4 + 1
```

This code rotates 6B twice to the right and then masks off all but the 2 lowest bits. In other words, it selects bits 2 and 3 as the actual value we want, giving us a range of 0-3. Then we add 1, giving us 1, 2, 3 or 4. 

In this way, the gain map that 6B is loaded from is really multiple maps packed into one - each byte contains many smaller independent values, some 2 bits, some 3 and one of them is just 1 bit!

Next we'll finally calculate our derivative term and apply the gain:

```
0xe65 mov  r0,#$65
0xe67 mov  a,@r0
0xe68 cpl  a
0xe69 inc  a
0xe6a add  a,@r1		;a = 64h-65h
0xe6b clr  c
0xe6c rrc  a
0xe6d clr  c
0xe6e rlc  a
0xe6f jb7  $0E7E
0xe71 djnz r7,$0E6E	       ;a = a * 2^{r7}, capped at 127
```

The basic derivative term is the current peak minus the previous, filtered version of itself. The key idea here is that at first, the filtered version will be zero. In subsequent iterations, it will start to catch up with the original peak. At any time new boost delta values that are higher than the peak can replace it. But the filtered value is chasing all the time, catching up with the peak. The difference between the two is a *derivative* in the sense that it's a measure of how quickly the demand for boost spiked, but it's not used in the way that the textbook D term of a PID controller is used. 

The code above doubles our derivative for every count in r7, that is, it multiplies by 2^n where n is the gain value from 6B. 

If at any point we hit 128, we jump to E7E which will cap the value at 127. 

```
0xe73 add  a,#$80		;
0xe75 mov  r0,#$62
0xe77 mov  @r0,a		;output is 62h
0xe78 mov  r7,#$6
0xe7a mov  r0,#$65
0xe7c jmp  $05F1		;DF1 smoothing with factor 6, input 64h, previous output 65h:66h (stores result in 65h:66h and issues ret instruction)
0xe7e mov  a,#$7F		;127
0xe80 jmp  $0673		;E73
```

In this final section we add 128 to our final term, which is intended as a *bias* - that is, 128 means zero, 129 means 1 and so on. Since we calculate an output for a positive boost deficit in this routine, there's no negative value; 128 is the lowest we can output. 

We store the output in 62h and then call the exponential smoothing/filtering routine using 6 as the smoothing factor, 64h as the new value, and 65h:66h as the previous output. The routine at DF1 stores the filtered result into 65h:66h. 

The whole thing in pseudo code is like this:

```
if target_boost_51 <= current_boost_52: (i.e overboost)
	64h = 0
	62h = 128 #full negative
	65:66 = exp_smooth(64h)
	return

if 64h == 0:
	if 65h == 0:
		64h = delta
else:
	64h = max(64h, delta)

if delta < 64:
	if delta < 1/4 * 64h:
		64h = 0
gain = 6B_lower_2_bits + 1
d = |64h - 65h|
62h = d * 2^{gain} (capped at 127)
62h += 128
65h:66h = exp_smooth(64h, 65h:66h, smoothing_factor=6)
return
```

So 64h is a peak detector, and it gets zeroed out when the latest delta is 1/4 of the peak, or less. Higher peaks replace 64. 

65h trails 64h by the filter mechanism; 62h is derived from the difference, and so it naturally decays as the filtered value catches up. When 64h goes to zero, 62h is abruptly neutralized to 128, but 65h continues to trail off, following 64h. As long as 65h > 0, the loop is locked out - i.e no new peak detection happens. 
