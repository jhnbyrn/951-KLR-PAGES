# How the KLR Measures Engine Speed

In short, engine speed is measured by counting the number of timer interrupts between trigger events (see the [section on signal timing ](klr_signal_timing.md) if any of that sentence doesn't make sense). The timer runs in the background, counting up from a preset value (stored in register __r7__) until it reaches 255 and overflows. When the timer value overflows, it triggers an interrupt. 

Every time the timer interrupt runs, it decrements a counter (__r6__), and when the trigger routine runs, it stores the value from __r6__ for later, and resets __r6__ for the next measurement. The stored value is later used for everything rpm-related. 

If you just wanted a high-level description of how speed is measured, that should do it. However, if you plan to read the code, you will absolutely need to know the details of this this works, because the timer interval actually changes sometimes, and this affects many areas of the code. 

So let's look at the code for this in detail. It's pretty simple. When the trigger signal arrives, the 8048 is reset, and the first thing it does it start the timer (0x000). Next it jumps to 0x077. A few initialization tasks are done starting at 0x077, but the first part we're interested in is 0x0B4:

```asm
0xb5 mov  r1,#$24
0xb6 clr  a
0xb7 xch  a,r6
0xb8 cpl  a
0xb9 mov  @r1,a
0xba mov  a,@r1
```

This code takes the value from __r6__, complements it, and stores the result in __24h__, while also resetting __r6__ to zero for the next measurement. After this, value in __24h__ is used throughout the code whenever the current engine speed is needed. It's not strictly speaking *rpm*, i.e. revolutions per minute, but it is the engine speed - just in a different unit of measurement: *timer ticks per ignition event*. 

The corresponding code from the timer interrupt routine is fairly trivial:

```asm
0x09 mov  a,r7
0x0a mov  t,a
0x0c djnz r6,$0010
```

First, we reset the timer. The value for the timer interval is stored in __r7__ (we'll look at this in more detail a little later). Next we decrement the engine speed counter __r6__, and jump to the next timer-related task if __r6__ is not zero. In fact, __r6__ will never reach zero, but the way that this is guaranteed requires some explanation, which we'll look at next. 

## The Problem With Low RPM

What we've seen so far works perfectly for engine speed measurement as long as the speed is above a certain level. But let's take a closer look at some actual numbers. Let's say the engine speed is 6000rpm. That means there's 5ms between each ignition event, and hence 5ms between each trigger event. The timer period is 87us, so we'll count 5000 / 87 timer interrupts between trigger events, with the result that __r6__ will count down from 0 to 199 between trigger events. 

So far so good. But obviously at lower engine speeds, there's more time between trigger events, and so __r6__ will count down to a lower number. That's how engine speed measurement works! But how low could it get? Well if you do a little number crunching, you'll see that at 1500rpm, the counter will get down to 26. That's dangerously close to zero. If __r6__ gets to zero between trigger events, it will roll over to 255, and the measurement will be meaningless. That's unacceptable, and something must be done to account for it. 

One solution to the timer problem would be to use a 16-bit counter. This would allow us to count from 65536 to 0 without any problem; the downside to this is that keeping track of 16-bit numbers in a simple 8-bit processor is time-consuming. An alternative approach is to change the timer interval, and that's exactly what the KLR code does. Take a look at the code in the trigger routine immediately after r6 is stored and reset:

```asm
0xbc add  a,#$1A
0xbe jnc  $00CF
0xbf mov  a,r7
0xc0 clr  c
0xc1 rlc  a
0xc2 mov  r7,a
0xc3 inc  r1
```

The first instruction adds the hex value __1A__ (decimal 26) to the complemented __r6__ value. This means that if the complemented __r6__ value was 230 or higher, the result of the add will overflow, and the carry flag will be set. If there's no carry, we jump past all this and continue with the rest of the trigger routine. But if the add carries, then we know that __r6__ has got down to 26 or below, so the engine speed is 1500rpm or less. If it gets much lower, we'll have a problem, so to prevent that from happening, we *double* the timer interval __r7__ (by rotating it one step to the left). 

What this this means is that if the engine speed gets below 1500rpm, the timer is automatically adjusted to run every 174us instead of every 87us. In fact, the timer interval can be adjusted further if rpm gets much lower, but that's not usually a concern. This adjustment of the timer interval guarnantees that __r6__ will never count down past zero in the timer routine, and we'll always have meaningful speed measurements. 

This comes at a price though; the timer is used for other things besides speed measurement, and therefore there are many places in the code where it's necessary to take the current timer interval into account when making calculations. Most microcontrollers now have several timers. Even the 8051 used in the Motronic DME has 2. It's not unusual to have 7 or 8 timers in  modern, cheap 8-bit microcontroller. This would make life much simpler - but the poor old 8048 only has one timer, and if we change the interval, it affects other things. So this is a good time to take a look at the timer interval in more detail. 

## The Timer Interval in Detail

As mentioned earlier, the timer interval is stored in __r7__. It's normally set to the value 254. The timer counts up, and triggers an interrupt when it counts up past 255 - so, starting with 254 means that the timer will count twice before triggering an interrupt. Let's look at some timing values:

The 8048 runs on an 11Mhz crystal, which is divided by 15 to produce the instruction clock. This clock is then further divided by 32 to produce the timer clock. This gives 43.6us per timer "tick", so by loading the timer with 254, we get 2 ticks or 87us between timer interrupts. 

I mentioned earlier that the timer interval can be doubled by rotating __r7__ to the left. Here's what 254 looks like in binary:

```
11111110
```

If we rotate this to the left (assuming the carry flag is clear), we get

```
11111100
```

which is 252. So now the timer will count 4 ticks before overflowing (174us). The reason I'm showing the binary representation is that it leads to a convenient way to test what the timer interval is at any point, and you'll see things like this throughout the code:

```asm
0xdc mov  a,r7
0xdd jb1  $somewhere
```

As you can see, if bit 1 of __r7__ is set, that tells us immediately that the engine speed is higher than 1500rpm, and that the timer interval is 254. Conversely, if bit 1 is clear, then we're below 1500rpm and the timer inveral is 252 (it *could* be even lower still - 248 - but that would mean that rpm is below 750, which usually only happens during start-up). This is very useful, because simple microcontrollers generally don't have the ability to compare 2 numbers easily -instead you have to use tricks like this. 

Now that you know why the timer uses a variable interval, and how this is handled throughout the code, you should be in a good position to understand some more complicated routines, such as ignition signal generation PWM generation. 

