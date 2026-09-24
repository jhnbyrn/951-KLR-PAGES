# 951 Boost control overview

The 951 KLR implements boost control by a combination of open loop (aka feed-forward) and closed loop (aka feedback) control. Most of the control comes from the open loop logic. The closed loop part handles fine tuning. But it's the part people get the most excited about, and of course it's where all the complexity is.

I'll assume you're familiar with the ideas of open and closed loop control - if not, there's a quick crash course in the appendix section at the end that should help. 

## A really quick hardware overview
We'll limit the scope of this mostly to the *logic* of boost control. You can read about the hardware setup in detail in many other places. But I'll say a little bit here just to make sure everthing is clear. 

For whatever reason - I think it's just one of the awkward translations in the original Porsche documenation - the boost control solenoid on the 944 has always been called the *cycling valve* or CV for short. So I'll keep calling it that. 

The default situation - when no current is flowing through the CV - is that it sends all the air pressure to the wastegate (WG), helping the valve to open so the exhaust can bypass the turbo. When current flows through the CV, all the air pressure gets recirculated back to the intake instead. Therefore, the CV has to be active (i.e. current flowing) to build significant boost. Of course, when boost is very low, then the WG valve doesn't open even when *all* the manifold pressure is sent there, so you can build a little boost even with the CV completely inactive - but the valve will start to open once you get to around 4psi. 

Like other boost control solenoids, our CV is controlled by a pulse width modulated (PWM) signal. It runs at a fixed frequency (about 15Hz) and the proportion of the time for which it's turned on determines the average air pressure that pushes on the WG valve. 

In this discussion, we mostly concerned with how the cycling valve is controlled. When we talk about increasing the duty cycle of the CV, that means decreasing the proportion of boost pressure thats allowed to push the WG valve, thus allowing boost to build up. 

There's a lot of complexity in the logic of the boost controller, but ultimately it all comes down to this one number: the PWM duty cycle that controls CV. In the sections that follow, we'll see how that number is generated. 

## Software
In a nutshell, we can summarize the boost control logic like this:

```duty cycle = open loop value + closed loop value```

The closed loop value can be positive or negative, so the final output can be more or less than the open loop value. 

Almost all the complexity is in how that closed loop value is calculated - the open loop part is very simple, it just gets looked up from a map. 

We can break the closed loop term down a bit more, like this:

```closed loop term = P + I + D + T```

The __T__ term here is a second integral term that normally doesn't do much, but if the I term reaches either of its limits (positive or negative) then this second term starts to grow in the same direction as the I term. I'll call it a *trim* term to distinguish it from the conventional I term. 

Now it's pretty common for the various terms in a controller like this to have *gain* - that is, a scaling factor that amplifies (or attenuates) a specific term. In the textbook PID controller, each term has its own gain. In practice, the 944 boost control logic has a fixed gain of 1 for the P and I terms, and a fixed gain of 2 for the trim term, T. Only the D term has variable gain. But after the three main terms are combined, a variable final gain factor is applied to all of them together (but not the T term; that gets added afterwards). 

We'll see how all that works in detail later, but for now we can expand our controller expression a little more into this:

```closed loop term = (P + I + D*d_gain) * final_gain + T*2 ```

Both the ```d_gain``` and ```final_gain``` factors here are variable, and are looked up from maps. The ```d_gain``` term depends only on rpm and ranges from 1 to 4, for lowest to highest rpm. The ```final_gain``` depends on both rpm and throttle position, and ranges from 0.5 to 1, with the greatest attenuation in the region where boost is highest. 

The trim term, T, is interesting. It only integrates while the I term is sautrated - but once it does start to grow, it has double the power of the I term. 

The D term is unconventional in terms of the textbook PID algorithm. Normally the D term works in both directions: if the delta is growing, it adds a positive correction, and if the delta is shinking, it adds a negative correction. In the KLR, the D term is zero if the delta is shrinking, and also if the system is overboosting. 


### Maps
Open loop control is handled by a 2-axis map that uses rpm and throttle position as inputs. The output is the baseline PWM duty cycle value. 

There are 16 rpm ranges and 8 throttle position ranges. The throttle position input covers a fairly small range of throttle movement: there is actually no CV PWM output at all below about 53 degrees. From there upwards, the map values are spaced out at 4 degree increments up to 81, with the final row applying for everything above 81 degrees. 

The closed loop target boost map uses the same inputs. Both maps use linear interpolation like the DME maps. 

The target boost is used directly for the D term, but for the P and I terms, it's filtered using the [exponential smoothing](exponential_smoothing.md) routine. 

Both maps are read from the housekeeping function table at the end of the program. 

### Closed loop code structure
The control logic uses propotional (P), integral (I) and derivative (D) components, but it's a little different from a text book PID controller. As I mentioned earlier, there are two separate integral terms, and the derivative term is only used to add a positive correction. 

The controller logic is divided into four main routines that are called alternately on every trigger event, so that they each run 1/4 of the time, i.e. a round-robin schedule. 

The scheduling routine is located at E00 and is called at the end of the knock detection code. 

The four routines are:

Location | Purpose
---------|-------
E82 | calculate P, I and T terms, collect all terms
E30 | calculate D/spool assist term
DDE | filter target boost
F00 | generate final PWM output

The scheduling logic is derived from the counter variable 2C. This conunter is used for this kind of scheduling in various parts of the program. The knock routine loads __a__ with a value derived from this that has bits 3 and 4 set in such a way that the four possible combinations occur 1/4 of the time. In the actual scheduling routine, we only see three states being checked; if bit 4 is set then we jump to the PI routine at E82. But that routine calls F00 if bit 3 is also set - this saves a few instructions compared to having it all done in the scheduler!

It will make sense to explain these in a slightly different order.

### Derivative spool assist term (E30)
This term influences the I term a little, so it makes sense to discuss this one first. This term handles the transient case where the boost delta grows suddenly. 

The basic idea is to take the difference between the current boost delta and a previous version, and add a big positive correction to the PWM signal based on the difference, which then decays away smoothly over the next few seconds. But there are a few tweaks:

* the "current" delta is really based on peak detection - that is, a higher value can replace the "current" one
* the "previous" value is simply a filtered version of the current one, passed through the exponential filtering routine to create a low-pass filter effect.

This way, the "previous" value chases the current one exonentially. This kind of chasing or tracking filter is really common in the 944 system. Similar patterns are used for the [throttle position sensor](klr_tps_processing.md) and in the [DME's ignition timing damping](dme_acceleration_timing_damping.md). 

Once this term has been calculated and applied, it's not overridden again as long as the previous one is still decaying. But the decay can be cut short by a few conditions:

* overboost - any time the current boost (52h) exceeds the direct target boost value (51h), this term is neutralized
* any time the boost delta gets smaller than 1/4 the size of the peak, the term is immediatley neutralized. 

This term is 128-biased, so 128 means zero, more than 128 means positive, and less means negative (but it's never allowed to go negative, it's clamped to between 128 and 255). The way this biasing works is that the I term has the same 128 bias, so when they're added together along with the P term, the biases cancel each other out. It might help to work through a few examples in your head - the important thing to remember is that if either or both values are less than 128, then their sum will be between 128 and 255, which is negative in the conventional 2's complement interpretation, as we would expect. If their sum overflows, then the final value will be between 0 and 127, representing a positive number, again just what we need. 

### Integral and trim terms (E82)
The main integral term (61h) is very simple and conventional. Any time the current boost is different from the filtered target boost (53h), this term accumulates at a rate of 1 unit in the direction needed to correct the error. If the error is less than 4 units (i.e. roughly 3kPa) then it only accumulates every 4th count (controlled by the counter 6Ah, which is theoretically rpm-depdendent, but happens to be set to 4 for all rpm). Recall from earlier that this routine runs every 4th cycle, that is every 2nd revolution. 

This term is 128-biased, just like the D term. It's also clamped to be between 68 and 187, which correspond to -60 and +60 respectively, once the bias is removed. 

If this term does reach one of its rails, but the error persists, then the trim term 67h starts accumulating, at a rate of 1 unit. But as discussed earlier, 67h is not added to the final term at the end of this routine. Instead it gets doubled and added to the total in the main CV routine, after the P, I and D terms are added. 

### Proportional term (E82)
The proportional term is also very straightforward like the integral term. It's basically just the boost delta. In theory it can be amplified by a gain factor, but in the actual gain map, the setting for this is always a gain of 1. 

This is a 1s complement signed value, with no 128-bias like the other terms we discussed above. The 1s complement means that it's biased a little negative - in other words, if actual boost and target boost are equal, then the P term will end up as -1. There's another bias of -1 introduced later, for a total of -2. The result is that the P term will always try to pull the boost down a little when it reaches equilibrium. 

Interestingly, the P term calculation lacks any rigorous overflow detection and clamping. It seems that the OEM engineers decided that they could assume the actual boost delta would always be within safe limits as far as overflow is concerned. And that does seem to be the case based on the target boost maps, but it's surprising to see this all the same. 

It is clamped to 64 on the positive side. The maximum safe range is actually +68 to -68 (in literal terms, that is from 0 to 68 on the positive side and from 255 down to 188 on the negative side). 

I discussed these overflow issues in more detail in the main P-term code walkthrough. 




## Appendix - closed loop control

If you're not familiar with closed loop control, I'd definitely recommend reading up on the concept, but I'll outline a few key concepts here that are probably enough. 

The idea is to make some variable (in this case, boost pressure) track a specific target. The system measures this variable continuously and compares it to the current target value. The difference is often called the *error* or *delta*. 

Anyway, once the error between the current state and the target state is known, a closed loop controller tries to correct the mismatch by steering the variable in the right direction - that is, it tries to minimize the error. 

How big a correction should it make? Obviously we want to get the system to the target state as quickly as possible. But we can't just make the strongest possible correction all the time; the error might be small, and we could end up overshooting the target. The natural thing to do is to make a *proportional* correction. That means the bigger the error, the bigger the correction. As the system's state gets closer to the desired target state, and error shrinks, the correction gets smaller, minimizing the risk of overshooting. 

The proportional approach works well - it's fast when the error is big, and automatically avoids overshoot, but it has a limitation: it gets slow as the error gets small, and in fact it can't ever completely eliminate the error. That's where the *integral* term comes in. The integral component doesn't care how big or small the error is - it only ever corrects at one speed: *slow*. But it has one cool trick up its sleeve - it keeps accumulating as long as there's an error. This means that an integral term can completely close the small gap left by the proportional term, and get the system's state all the way to the target. Putting the two together gets you a way to track a target variable quicklyand accurately. 

This is actually pretty close to how we do things manually. Suppose you have to fill a glass with water, right to the top. When it's empty, you pour quicky, because you don't want to take all day, and there's not much risk of spilling it. But as it gets more full, you slow down. Eventually it gets to the point where it's not worth trying to pour at a rate that's proportional to the remaining space any longer. It's too tedious, and you switch to a very slow, steady, consistent pour to top it off. That's proportional and integral control! In practice, the integral control part doesn't wait - it accumulates all the time, but it typically doesn't become very noticeable until the error is small. 

Or, if you prefer we can just say: __the P term is the hare and the I term is the tortoise.__

Now closed loop controllers often go further than this and take into account whether the error is currently growing or shrinking, and how quickly. To make sure this discinction is clear: the P and I terms *do* take account of the direction of the error, so if the system is below the target, they are positive and if it's above the target, then they are negative. But they are only concerned with the error as it stands *right now*. They don't take account of how the error is changing, i.e. how quicky and in which direction. This is what the derivative (i.e. rate of change) term is for. I'm sure you can come up with suitable analogies from real life to see why a D component can be useful!

In practice though, lots of closed loop controllers don't bother with a D component. The 944 KLR does use one, but only in very specific cases as we'll see later. 

So that's a quick crash course in closed loop control. One final comment to round it off: going back to the water pouring analogy, you probably had a pretty good idea of how much to tip the jug up in order to get the effect you wanted, even before you saw the rate of pouring. You knew that from experience. So if you already know roughly what to do, to within a pretty close margin of error, why not just start with that, and then only consider feedback and small adjustments if the result deviates from what you expected? That's easier and faster right? And *that's* open loop control, sometimes called *feed forward*, because in a sense its the opposite of feedback. Most control systems work exactly this way, and the KLR boost control is no exception.
