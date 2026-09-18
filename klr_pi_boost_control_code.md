# KLR boost control PI routine (E82)

This is the routine responsible for calculating the __P__ and __I__ terms for the boost contol logic, and also collecting those along with the __D__ term into one output at the end. 

There are actually *two* integral terms here, the "main" one in 61h, and a kind of trim term in 67h. Here, 67h is only moved when 60h is saturated to one of its rails. But in the final cycling valve control routine, 67h is adjusted according to other rules. 

The principal values this routines works with are

Location | Purpose
--------|--------
52h | current boost
53h | low-pass filtered target boost
60h | boost delta, i.e. P-term
61h | main integral term
62h | spool assist/D-term (used here,calculated at E30)
63h | total PID correction sum
67h | trim, i.e. slow I-term
6A | counter to slow down 61h when delta is < 4
6B | PID gain map value

The code starts by jumping away to the CV control routine if b3 of the scheduler value was set - this ensures that each of the 4 boost control routines gets called 1/4 of the time (see E00):

```
0xe82 jb3  $0EF6		;bail out, call CV adjustment routine
0xe84 mov  r1,#$52		;boost measurement from ADC
0xe86 mov  a,@r1
0xe87 cpl  a
0xe88 inc  r1			;53h
0xe89 add  a,@r1
0xe8a mov  r4,a			;
0xe8b jc   $0E8F		;c=1 if 53h >= 52h
0xe8d cpl  f0
0xe8e cpl  a
```

If b3 wasn't set, we calculate the difference between current boost 52h and filtered target boost 53, convert it to an absolute value and track the sign with f0. The default for f0 here is 1 (from DDA), so now we set f0=0 if current boost is higher than the target.

```
0xe8f add  a,#$FC		;252 (a = (52h - 53h) - 4)
0xe91 mov  r1,#$6A
0xe93 mov  r0,#$61		;possibly integral term
0xe95 jc   $0E9B		;c=1 if delta >= 4 (~3.3kpa)
0xe97 mov  a,@r1
0xe98 inc  @r1			;6A++
0xe99 jnz  $0ED0
```
Above, we check if the delta is < 4 (around 3.3kpa). If so, then we inc 6Ah and check if it's zero. If it's not zero, we skip all the I term code and go straight to the P term code at ED0. 

In other words, integral term logic only runs if either the delta is >= 4 or 6Ah has overflowed. If delta >=4, we don't care about 6A, but jump straight to E9B below:

```
0xe9b dec  r1			;69h (rpm constant, always #4)
0xe9c mov  a,@r1
0xe9d cpl  a
0xe9e inc  r1
0xe9f mov  @r1,a		;intialize 6A to 252
```
Here we initialize 6A to 252 (i.e. -4). This happens if either it overflowed or we didn't check it because the delta is >=4.

Next we handle the integral term, 61h (r0=61h now). At this point we know that either the delta is >=4, or it's less but 6A has counted 4 times:

```
0xea0 inc  @r0
0xea1 jf0  $0EA7		;f0 tracks if 52h is <= or > 53h
0xea3 mov  a,@r0
0xea4 add  a,#$FE		;254
0xea6 mov  @r0,a		;61h -= 2
0xea7 mov  r1,#$62		;derivative term?
0xea9 mov  a,@r1
0xeaa add  a,#$60		;96
0xeac jnc  $0EB0		;jump if 62h<=160
0xeae mov  @r0,#$80		;61h = 128
```
We increment 61h, and then check if the direction is negative (i.e. overboost) and if so, decrement 61h twice - thus we either inc or dec once in total depending on the direction. 

Then we check the derivative-based spool assiset term 62h, and if it's 160 or more (that is, 32 above the zero-bias 128), we neutralize our integral term 61h. 

The next section handles clamping 61h, and adjusting 67h which is the slow integral term:

```
0xeb0 mov  a,#$BB		;187 (+59 based on 128)
0xeb2 mov  r3,a
0xeb3 cpl  a
0xeb4 add  a,@r0
0xeb5 jc   $0EBE		;jump if 61h > 187 (59 effective)
0xeb7 mov  a,#$44		;68 (-60 based on 128)
0xeb9 mov  r3,a
0xeba cpl  a
0xebb add  a,@r0
0xebc jc   $0ED0
0xebe mov  r1,#$67
0xec0 mov  a,@r1
0xec1 jnz  $0EC5
0xec3 clr  c
0xec4 cpl  c
0xec5 cpl  a
0xec6 jz   $0EC9
0xec8 inc  @r1
0xec9 jc   $0ECE
0xecb cpl  a
0xecc dec  a
0xecd mov  @r1,a
0xece mov  a,r3
0xecf mov  @r0,a
```
This limits 61h to between 68 and 187, that is -60 to +59 around our pseudo-zero value of 128. If we're at either rail, we inc or dec 67h accordingly. So 67h carries on integrating in the same direction as 61h when 61h has saturated. 

That covers the integral terms 61h and 67h (although 67h is adjusted separately in the cycling valve routine, back towards its centre value 128 whenever the final cycling valve PWM output is saturated). 

Next we handle the proportional term:
```
0xed0 mov  r1,#$6B
0xed2 mov  a,@r1
0xed3 jb4  $0ED9		;none of the map values actually have b4 set. 
0xed5 mov  a,r4			;r4=signed delta from earlier
0xed6 clr  c
0xed7 rrc  a
0xed8 mov  r4,a
0xed9 mov  a,r4
0xeda clr  c
0xedb rlc  a
0xedc mov  r4,a
```
The value from our gain map is stored in 6Bh. Here we check bit 4, and multiply r4 value by 2 if it's set, otherwise we leave r4 alone. But bit 4 isn't set in any of the values in this map, and in fact the code that follows that check wouldn't be safe if it did! Because there are no checks in place to make sure we don't move a non-zero bit into or out of the MSB position. Thus we could accidentally negate our value here and we wouldn't now. This kind of thing is very rare in Motronic code generally, but its typical of the latter half of this routine. They must have been in a hurry!

Since bit 4 is always zero, we'll rotate right and then left again, losing only the LSB. 

Now earlier we calculated the delta by complementing 52h, but we didn't increment it to create a true 2s complement value. Instead it was used as a 1s complement. That means if the target and current boost values were equal, we would get 255 i.e. -1 as our delta instead of 0. That gives the P term a bias of -1. In the code above, we also lose any LSB that was present, ensuring a total bias of -2. 

So any time that boost is exactly equal to target boost, the P term will pull it back down every so slightly, triggering more correction activity. 

```
0xedd jb7  $0EE5
0xedf add  a,#$C0		;192
0xee1 jnc  $0EE5
0xee3 mov  r4,#$40		;64 - cap r4 to 64
0xee5 mov  a,r4
```
Recall that the value we stored in r4 earlier was the raw delta (target boost minus actual boost) - positive if boost is below target, negative otherwise. But we also kept track of the carry flag in f0. That flag (and *only* that flag) reliably indicates whether the boost delta is positive (i.e. below target) or negative. But instead of using that f0 flag now, we treat bit 7 as though it was an indicator of the sign of the delta. This is only true as long as the magnitude of the delta was less than 128. Luckily this is pretty much guaranteed, but only because the lowest map value is 137, and the highest possible boost value is 255, and the difference is indeed less than 128. But this is still a strange thing to do when the reliable sign flag f0 is available for exatly this purpose. 

In any case, here we keep the value as-is if its negative (based on bit 7), and cap to 64 if it's positive. 

```
0xee6 mov  r1,#$60		;boost delta
0xee8 mov  @r1,a		;60h = r4
0xee9 add  a,@r0		;r0=61h
0xeea inc  r0
0xeeb add  a,@r0		;add 62h
0xeec inc  r0			;r0=63h
0xeed jnc  $0EF1
0xeef jb7  $0EF3
0xef1 mov  @r0,a		;63h = sum of all terms
0xef2 ret
0xef3 mov  @r0,#$7F		;cap 63 to 127 if the add carried
0xef5 ret
0xef6 jmp  $0700	     ;CV routine (0xf00)
```
Finally, we collect all our control terms. Our signed boost delta goes into 60h - this is later used in the error checking routine. 

This is yet another example of very poor practice: now we're treating 60h as a 1s complement signed byte, and we have two terms to add to this - 62h and 63h that are both signed values, but are 128-biased. The idea here seems to be that the two biases will cancel - for instance, suppose both values were 128, meaning zero. Then they will sum to zero. If one was 129, and the other 128, they'll sum to one and so on. So far, so good. 

What about 60h? Suppose that we have an overboost situation, and 60h and 61h are both somewhat negative. Let's say, -60 each. For 60h, that means a literal value of 196 and for 61h, a literal value of 68. Added together, we get an overflow, and a final value of 8. That doesn't look negative, but when we add 62h (which is generally 128 in the case of overboost) we'll have 136, which means -20 in the usual signed 2s complement form. That's what the cycling valve routine expects, so all is well. 

But if 60h was just a bit more negative than that, say, -69 then we'd be adding 187 and 68 to get 255. Now when we add the 128 from 62h, we get 127. But 127 is *positive* in 2s complement! We should have a negative number. 

This means that if 61h is saturated negative, and 60h is growing in the negative direction, when it exceeds -68 (relative), the overall correction value will flip from -128 to +127 instantly. So -68 is the most negative safe value for 60h. 

And as we saw previously, 60h has clamping to 64 on the positive side, but no clamping on the negative side. 

The code above does catch the case where a large positive sum overflows after ading 62h, and it correctly caps the value to 127. But because it ignores the carry flag from the first addition (60h + 61h) it's impossible to tell if the value is correct in the negative case. 

There are cases where this flipping could be acceptable: 62h is calculated based on the instantaneous target boost value from the map (51h). But the 60h and 61h are based on the slow-changing filtered version 53h. If 62h says "we need a big positive kick *now*" then it's probably right, since its based on more up to date information, and maybe it's a good thing that the PID output flips into the positive range. But as we saw in the example above, 62h was 128, which means zero since it's a 128-biased value, and we still got the flip, when it's clearly wrong!
