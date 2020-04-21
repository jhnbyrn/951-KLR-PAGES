# Reading 8048 Series Code

Here are a few notes and (hopefully) helpful pointers for anyone looking to make sense of Intel MCS48 series code. All this info and more can be found in the [Intel MCS48 User's Manual](references/mcs48.pdf) and the [MCS48 Assembly Language Reference Manual](9800255D_MCS-48_and_UPI-41_Assembly_Language_Reference_Manual_Dec78.pdf).

If you have any experience with 8051 microcontrollers, the 8048 should be fairly familiar. However, it's not an 8051; it has fewer resources, and a simpler instruction set. This tends to result in more complicated code for a given task. 

## Resets and Interrupts

Program execution starts at location 0 as you'd expect. The 8048 has 2 interrupt sources: the external interrupt pin and the timer. Here are the 3 most important addresses to memorize:

Address|Function
-------|--------
0x000| start/reset
0x003| external interrupt
0x007| timer

The timer counts __up__ and triggers an interrupt when it counts up from 255. 

The external interrupt is triggered on the __falling__ edge of the INT pin. 

The instruction __retr__ signals the end of an interrupt routine; this causes the program coutner to be restored from the stack. 

A __reset__ (triggered by pulsing the RESET pin) sets the program counter to 0. The reset feature doesn't erase any RAM or special registers. It does disable interrupts, and it sets all port pins to high-impeadence output. It can be used as a pseudo-interrupt - you just have to make sure to set up all the port pin outputs and interrupt configuration bits in the reset routine. 

A complete list of what the reset does can be found in the manual (linked above).

## Special Registers and Register Banks

The 8048 has a set of general purpose registers known as __r0__ - __r7__. These registers can be used for several important tasks that you can't do on general RAM locations directly. 

Of these __r0__ and __r1__ are special: they can be used to load values from RAM indirectly. For example:

```asm
mov  r0,#$24
mov  a,@r0
```

This code loads the value 0x24 into __r0__, and then loads the *value from RAM location 0x24* into the accumulator. The register __r1__ can be used in the same way, but the others  (__rb2__ to __rb7__) cannot. 

All 8 of these registers (including the special __r0__ and __r1__) can also be used for arithmetic with the value in the accumulator, and can also be incremented, and decremented directly. They can also be used for the all-important __djnz__ instruction, which makes them useful as counters:

```asm
0x1a djnz r2,$0036    ;dec. r2, and jump to 0x36 if the result isn't zero
0x1d mov  r0,#$26
0x1e mov  a,@r0
...                   ;(more instructions, not shown)
...
0x36 jmp  $005E       ;do something else if the r2 did reach zero
```

There are actually two completely separate sets of registers, known as __register banks__. The progam must select which register bank is to be used.

By default, register bank 0 is selected. The register bank can be explicitly selected using the __sel__ instruction:

```asm
sel  rb0
...
sel  rb1
```

The idea behind this is that one bank can be used for the main program, and the other can be used for interrupt routines. One of the first instructions in an interrupt routine should be to select the alternate register bank. This way, the interrupt routine has it's own dedicated registers for loading variables from RAM, it's own counters etc. When an interrupt calls __retr__, the previously selected register bank is restored automatically. 

The register banks are memory-mapped; this means that they can be accessed directly instead of through the special names __r__*x* - but that results in a program that's hard to understand and maintain, so it's probably not a good idea unless there's a compelling reason to do it. 

## Memory Banks

The 8048 variations have different amounts of program memory; this section is about the 4K version. I'm not sure about the 2K versions. 

In the 4K version, program memory is divied into 2 __banks__ of 2K each. Furthermore, each bank is divided into __pages__ of 256 instructions. These boundaries matter when using any instruction that makes the program counter jump - that is, __call__, __movp__ and the various jump instructions. 

In the following subsections we'll look at how each type of instruction is affected by these memory boundaries. 

### Call and Unconditional Jump

The call and unconditional jump instructions are limited to the current bank. The current bank is determined by the __sel__ instruction:

```asm
sel mb0    ;select memory bank 0
...
sel mb1    ;select memory bank 1
```

The confusing thing about this is that the addresses specified by __call__ and __jmp__ instructions are *relative* to the current bank. So, for instance, you might see something like this:

```asm
call $0608
```

...and when you look at program memory location 0x608, it makes no sense:

```asm
0x608 nop
```

That's because the __call__ instruction is in a part of the code that uses __mb1__, so the location 0x608 is interpreted relative to the start of __mb1__. Since the banks are 2k, the first location of __mb1__ is 0x800 (2048 in decimal). When you add 0x608 to 0x800 you get 0xE08, and *that* is the true location of the subroutine that this call instruction references. 

Sometimes you'll see a subroutine call being bracketed within __sel__ instructions like this:

```asm
0xf0e sel  mb0
0xf10 call $0300
0xf11 sel  mb1
```

This is necessary when we are in __mb1__ but we want to call a subroutine that's located in __mb0__. We switch to bank 0, call the subroutine, and then switch back to bank 1 again. 

Note: changing program memroy banks does __not__ affect the register banks; switching register banks is done with __sel rb0__ or __sel rb1__ and it completely seprate from program memory banks. 

### Conditional Jumps

Conditional jump instructions (__jb*x*__, __djnz__ etc.) use absolute addresses *but* they're limited to the current page (256 instructions). This can be a little confusing to think about, but it actually makes code very easy to read. When you see something like this:

```asm
jb1 $0A7C
```

...you can assume 2 things: 

1. the address 0xA7C is the true address that this instruction refereces - you don't need to translate it based on the currently selected memory bank (as you would for __call__, or an unconditional __jmp__).

2. the location is always nearby; conditional jump instructions are used for the equivalent of __if__ statements from high-level languages, but never to call subroutines or jump to a completely different area of the prgram. 

### Movp

The __movp__ instruction allows program memory to be read as data. This is how __lookup tables__ (also sometimes known as __maps__) are implemented. 

A __movp__ instruction looks like this:

```asm
movp a,@a
```

Assume that when this instruction is about to run, the accumulator contains a program memory address. This instruction then loads the value stored at that address *into* the accumulator. It's up to the programmer to make sure that the address pointed to by the accumulator contains meaningful data. The really important thing to note here is that the address stored in the accumulator before this instruction is executed is __relative to the start of the current page__. 

For example, let's say the above instruction occurs at progam memory location __0xA72__, and let's assume that the accumulator contains the value __4__. The page that location 0xA72 lives in starts at the previous multiple of 256, which is 0xA00 (2560 decimal). So the instruction above will add __4__ to 0xA00 to get 0xA04, and then put the value found in 0xA04 into the accumulator. 

For this reason, maps or lookup tables are almost always stored at the beginning of a page - this allows them to be read using addresses that start at zero, which makes life easy for the programmers. 

## Arithmetic

The 8048 has a simple intruction set that doesn't include multiply or divide instructions. That means we have to get clever to do basic arithmetic, and if you haven't worked with very simple instruction sets before, it can be hard to grok what's going on. So in this section we'll take a look at a few common tricks used in the KLR code. 

### Modular Arithmetic

You might know that modular arithmetic (aka clock arithemetic) involves dividing a number using integer division, and then discarding the answer (or *quotient*) and just taking the remainder (or *modulus*) instead. I won't get into why this is a useful thing in microcontroller programming - that will speak for itself when you read the code. I just want to show you how it's actually done. 

In general, you can take the modulus of a number with any power of 2 by simply ANDing the number with one less than that power of 2. So for example:

```asm
anl  a,#$7
```

This effectively divides the value in the accumulator by 8 and stores the *remainder* in the accumulator. 
