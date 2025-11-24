# DME Fuel calculation

In this section we'll explore the details of how the DME decides how much fuel to inject. First, let's consider a very brief overview of the fuel system. 

Fuel is pumped from the tank to the rail in the engine bay and maintained at a constant pressure of about 2 bar above the intake manifold pressure. The injectors are opened briefly once per revolution by a signal from the DME and allow pressurized fuel to spray into the intake manifold. Because the pressure is contstant, the amount of fuel delivered for each pulse depends only on the duration of the pulse. The pressure in the manifold does vary quite a bit, depending on driving conditions, but this pressure is added to the fuel pressure regulator so that the fuel pressure in the rail is always at a constant 2 bar above manifold pressure. 

You might expect the injectors to operate individually, each one spraying fuel into its respective cylinder when the intake valve is open. And some systems do work that way (it's called sequential injection). But the Motronic system in the 944 uses *batch* injection, meaning that all 4 injections are fired at the same time. Since only one cylinder has its intake valve open at this time, the fuel for the other 3 cylinders gets sprayed onto the back of the intake valve. No problem; it'll be sucked into the cylinder when that intake valve opens.

If you are paying attention you may have raised an eyebrow when you read "once per revolution". Only two cylinders fire per revolution; it takes two revs for all four cylinders to fire. So that means each cylinder must get *two* pulses of fuel for every time it fires. So the injector pulse width is really calculated to deliver half the fuel that the cylinder needs. 

Next we'll consider a high level view of the fuel pulse calculation. 

## Calculation overview


