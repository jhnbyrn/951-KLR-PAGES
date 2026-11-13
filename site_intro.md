# A deep dive into the Porsche 944 engine management system

## First principles

It's best to start with energy. The energy to power a petrol engine comes from the petrol. But in order to extract that energy, we have to mix the fuel with air in a certain ratio, and burn it. It takes a lot of air. 

You might expect that we could control the power of an engine by controlling how fuel we give it, since that's where the energy comes from. But for reasons we won't get into here, petrol engines are actually controlled primarily by limiting (i.e. throttling) the amount of air entering the engine. The rate of air flow is then measured, and based on that measurement (and a few other variables), an appropriate amount of fuel is mixed with the air.

When you push or release the accelerator pedal, you're just controlling the rate of air flow entering the engine. Somehow the rate of air flow must be measured and the fuel metered out appropriately based on that measurement. In the old days, that *somehow* was a carburettor. They eventually became very sohpisiticated and complicated, but they have their limits. One problem in particualr is that the fuel requirements don't depend solely on airflow. Its really much more complciated than that: engine block temperature plays a huge role, and the amount of fuel needs to be increased for starting, for cold conditions and many other cases. This fuel increase above the usual ratio is known as *enrichment*. And the need for various enrichments at different times greatly complicates mechanical fuel delivery systems. But later those systems were replaced with electronic systems that give us far greater control, which is the subject of this discussion. 

Next I'll say just a little about sparks. The mixture of fuel and air has to be ignited in order for it to burn. That's achieved by a spark plug; as far as I know this fact hasn't changed since the earliest petrol engines. 

But control of the spark plug - i.e. the timing of the spark - that has changed a lot! 

If you you have ever cycled a bicycle, you'll know that it doesn't pay to push equally hard at all points in the pedal's rotation. For instance, you don't push with all your strength when the pedal is at the top of its travel, i.e. 12 o clock. Or when it's at 6 o clock (the bottom). That's clearly a waste of effort. You might think the 3 o clock position is optimal. But note that you push for a certain minimum length of time, and you don't want to be still pushing when the pedal is at the bottom. So you probably want the 3 o clock position to be in the *middle* of the push, and that means you want to start somewhere around the 1 or 2 position. You might not have thought about in that kind of detail before, but you're probably doing something like that intuitively. 

It's similar for piston engines. When the air/fuel mixture burns it expands and creates a force that grows to a peak and then dies away, and we want that force to peak at a point in the crankshaft's rotation that makes the best use of it. It turns out that this is around 14 degrees past the 12 o clock position (the 12 o clock position is commonly called top-dead-centre or TDC).

The air/fuel mixture burns at a rate thats dictated by chemistry, and doesn't really depend on the engine's speed. So if we want the force to peak at a certain angle after TDC, then we need to fire the spark a certain fixed amount of time before that. If we measure the *angle before TDC* at which we fire the spark, clearly this needs to be a bigger angle at higher engine speeds, in order for the peak force to coincide with the 14 degree angle after TDC that we want. 

So, measured as an angle, our spark timing must depend on engine speed. But wait, it's even more complicated than that! It turns out that we actually don't *always* want peak force at this mechanically optimal angle. For complicated reasons, we need to be able to vary the angle at which peak force occurs, and this means that spark timing needs to be influened by other variables besides engine speed. In the old mechanical systems, this ability was very limited. As with fuel, computerized management of spark timing gives us total control. 

## Engine management systems generally

We're concerned with petrol/gasoline powered piston engines in this discussion. The main task of an engine management system is to make sure that the engine gets the right amount of fuel, and the right spark timing. A third, less critical goal is maintaining a stable and accurate idle speed. 

Up until the late 70s all this was generally done mechanically on virtually all cars. Fuel was metered by a carburettor, and spark timing was controlled by a mechanical distributor. 

Around that time electronic fuel injection systems started to appear. At first, they were electronic but not really computerized, and only handled metering the fuel. Ignition was still handled mechanically, and often there were still some relatively crude fuel adjustments for cold start enrichment etc. 

For a system to be called a true electronic engine management system, I'm going to decree that it must handle fuel and spark timing, and further it must handle the fuel situation *completely*. That is, all enrichments for cranking, cold starting, warmup etc.

The Bosch Motronic system used in the Porsche 944 was certainly an early example of a true engine management system - maybe the first. 

Modern engine management systems are really complicated, with operating systems, networks, over-the-air updates etc. But let's consider the simplest system that can be called a true engine management system. Such a system needs these inputs at an absolute minimum:

* the crankshaft angle (relative to TDC)
* the rate of mass airflow entering the engine

As outputs, it must produce (again, at an absolute minimum):

* a fuel injection signal
* a spark signal

In practice though, even the simplest systems use more inputs and outputs than these. Here's a better (but still not really complete) list:

__inputs__
* crankshaft angle
* engine speed (this can be calculated from the angle at different times)
* mass airflow
* engine temperature
* approximate throttle position (idle, part throttle, wide-open throttle)

__outputs__
* fuel injection
* spark signal
* idle control signal

So the software for any engine management system must process these critical inputs and produce the three outputs listed above. Everything else is relatively minor optimizations and improvements. 

In very broad strokes, this processing is done in softare by making extensive use of lookup tables or maps. These maps will typically have either one or two axes, and provide an output value that can be readily converted into the appropriate signal. Inputs into these maps are typically engine speed, airflow, and temperature, but often the map inputs are other values that are calcualted from these basic inputs. Most outputs are not simply generated from one such map lookup, but by a series of map lookups. The outputs of each map are combined, scaled etc. and turned into quantities that can be used to control the output signals.

Let's consider these signals briefly. The inputs are naturally analog quantities; the sensors that measure them generally produce varying analog voltages, which are converted to digital values in order to be read and procssed by the computer (more on that shortly). 

The outputs are fundamentally analog quantities too; we need to be able to vary the fuel quantity, spark timing etc. in very fine increments. But generating varying analog voltages as outputs is troublesome and not really needed in most cases. Instead, the outputs usually take advantage of a very simple form of digital-to-analog conersion called *pulse width modultion*, or PWM for short. You can think of this as a kind of hybrid signal in the sense that it's natively easy to produce from a digital source, and yet at the same time it can control a device with analog precision. The idea is that the output is switched on and off (digitally) at some fixed freuqncy, i.e. it's *pulsed*. But the *duration* of these pulses is variable from some very small percentage of the total period, to the entire period (or very close to it). 

Let's consider these outputs one by one:

* fuel injectors - these are simply on or off. When they're on, they allow pressuried fuel to spray into the engine intake. The longer the on-pulse is, the more fuel we get. The fuel pressure is held at a constant value above the air pressure in the intake, so that the rate of spraying is always predictable - it depends only on the duration of the fuel pulse (which we commonly call the pulse *width*). 
* spark timing - this signal controls the ignition coil, which is a kind of transformer that powers the spark plugs, and it's mostly just a question of timing. The coil needs to be charged for a short time (this period is known as *dwell*) and then it's simply turned off to fire the spark. So there's no real analog conversion needed here - the timing thats done within the software is the "analog" quantity
* idle control - the engine is kept at a stable idle speed by means of a valve that controls how much air is allowed in when the accelerator pedal is all the way up. This idle valve allows air to bypass the closed throttle valve, so that the engine can remain running. The amount of bypass air is controlled by a valve, and the valve is controlled by a PWM signal. 

So the software creates output signals mostly by calculating appropriate pulse widths, and/or by timing the digital switching of things precisely. 

With this in mind, it should make sense that the inputs are mostly fed into an analog-to-digital converter (ADC) before getting to the software, but the outputs are generally *not* sent to a digitial-to-analog converter (DAC), because the devices that are contolled by these output signals are designed to be controllable by on/off voltages, and the precision just comes from fine timing, which the software can do on its own. 

## Bosch Motronic ML1.x

Now we're finally in a position to get into the specifics of the system at hand, the Bosch Motronic system. This system is based on the legendary Intel 8051 microcontroller. The 8051 is paired with an ADC0809 ADC which has 8 input channels and converts various analog sensor inputs into 8-bit values. In early versions, the program logic was in masked ROM in the 8051, and the maps were generally stored on a removeable 24-pin 4K EPROM. Starting in 1988, the DME configured the 8051 to read the program itself from the EPROM, and the EPROM was replaced with a 28-pin 8K version which contained the program and maps, all in one image. The 8051 presumably still contained the original code in its masked ROM - but with the EA pin tied low, it's not accessed. 

These devices form the heart of the DME. The rest is mostly input signal conditioning, and output buffering/power amplification etc. Most of it has little to no bearing on the logic that we're concerned with, but there are a few things worth noting:

* this system uses a custom Bosch IC to convert the crank sensor signals from analog waves into digital pulses. These signals are generated by VR sensors and are tricky to process via an ADC. 
* one of the ADC channels is dedicated to an 8-way switch on the DME circuit board known as the fuel quality switch (FQS). This is normally left in one position



## Turbocharging and knock control - first principles

Earlier I mentioned that in order to get the energy from fuel, it has to be mixed with air. I commented that "it takes a lot of air.". Now let's examine that comment in a bit more detail. It takes around 14-15 parts air to one part fuel. It does vary but this is a good starting point for our discussion.  But this ratio is by *mass*, not by volume. Fuel is much heavier than air. Considering mass, a pound of fuel (that is a few cups) is equivalent to about a refrigerator's volume of air. And we need almost 15 times that weight of air to burn the pound of fuel - so basically a small room full of air. But look at the engine - it's tiny! Somehow we have to get all that air into that tiny engine, burn it, and get the burned exhaust out again. Therefore getting an engine to make more power isn't simply a case of giving it more fuel. You do have to give it more fuel, of course - that's where the energy comes from. But that's the easy part. The hard part is getting the extra air you need in and then out again, quickly enough. And I really do mean *the* hard part; this is the central problem of performance engines - it's all about air flow!

So for a given engine, if we want it to make more power, we actually have very few choices available:

* we can make the engine bigger, so that the pistons displace more air. This is the simplest way
* we can leave it the same size but make it spin faster - that way we displace more air in a given time
* we can leave it the same size and the same speed, but get more air through it by compressing the air

The first option is the way to go if you can get away with it. But it's inefficient because it increases mechanical losses. The second option has its advantages. The engine can be small (and thus light) and when you don't need the power, it can be pretty efficient. But this approach also has its downsides that we won't get into here. The third option is the most complicated conceptually but is actually surprisingly practical. It can result in an engine that behaves like a small engine when we don't need the power, and like a big one when we do. 

There is a fourth option, that allows us to cheat a bit. The trick is that we don't really need *air* to burn the fuel - what we need is *oxygen*. Air just happens to be the most convenient source of oxygen, most of the time. But as we have seen, it's bulky. If you can supply oxygen in a more compact form then you can burn a lot more fuel without doing any of the three things listed above. This is the basic idea behind nitrous oxide injection, which is the least practical (but the most dramatic and most Hollywood-friendly) way to make more power. 

Let's come back to that third option. Compressing the intake air is called *forced induction* or *supercharging* and there are two ways to do it:

* a belt driven pump (commonly just called a *supercharger*)
* an exhaust driven pump (originally called a turbo-supercharger, nowadays just called a turbocharger or turbo) 

They both force more air into the engine by compressing it. The difference is where the energy to do that compression comes from. Superchargers take the requireed energy from the engine's output; turbos take it from the heat of the exhaust. Superchargers are thus a little parsitic. A supercharger that adds 50 horsepower might take 15 horsepower to work, so the net gain is really 35. But a turbo that adds 50 horsepower brings no corresponding drain - the energy that drives it would have been wasted as heat anyway! 

Superchargers are still used on some high performance cars but turbos have emerged as the most popular way. Nowadays, turbos are used largely to meet emissions standards; cars that previously might have had, say a 3L engine now have a 2L with a turbo, so they can match or exceed the power of the previous generation, but still meet stricter fuel economy and emissions standards.

But back in the late 70s and early 80s when turbocharging was still a novelty, it was exclusively used for high performance cars, and it presented a number of problems. In the case of the 944 Turbo, we'll get to see exactly how these problems were solved. And this is really cool because these were the absolute cutting edge solutions at the time - the best in the world. 

What are these problems? In brief, *boost control* and *knock*. 

Boost is the term used to refer to the extra pressure (over and above atmospheric pressure) that the intake air of a turbocharged engine has. A turbo works by compressing intake air via a fan. The fan is driven by a shaft which in turn is spun by the hot expanding exhaust gas passing through a turbine (i.e. another fan). So a turbo is really a positive feedback loop. It makes the engine make more power, and that results in more exhaust energy, and the increased exhaust energy makes the turbo spin faster, compressing the intake air even more, and causing the engine to make even more power...you can see where this is going. Like all positive feedback systems, there needs to be some way to regulate the contribution it makes or else things will get out of hand. 

Knock is a problem that any engine can suffer from, but it's greately exasperated by the increased pressure and heat of turbo engines. It's an uncontrolled burning process; after the spark ignites the air/fuel mixture, instead of burning steadily and predictably, it will sometimes start to burn in multiple places at once and get out of control. This can destory an engine if left unchecked. 

The solutions to these two problems are intertwined. Early turbocharged engines had very primitive boost control, and as a result they had to be tuned very conservatively to prevent the engine from being destroyed by knocking. The advent of electronic boost and knock control changed all that and allowed cars like the 944 Turbo to be pushed close to the limit of what was physically possible. To achieve this, a separate ECU was developed to work alongside the Motronic DME. This ECU is known as the KLR. 

## The Porsche 944 KLR

In pretty much all boost control systems, the means of regulation is with an exhaust valve called a *wastegate*. The wastegate can open to allow exhaust gas to bypass the turbo, or close and force all the gas through the turbo, or do something in between. The force that actuates the wastegate comes, conveniently, from the boost pressure. In the early, simple systems, some very basic mechanical system regulated the air pressure to the wastegate actuator. Electronic boost control allows the use of software with arbitrary logic to regulate this air pressure signal via a solenoid valve. The KLR monitors the actual boost via a pressure sensor, and compares this to a map of target boost, then regulates the air pressure to the wategate to make the actual boost track the target curve as closely as possible. 

At the same time, the KLR also monitors the engine for knock using a piezo sensor attached to the engine block. If it detects knock, it adjusts the ignition timing, delaying the firing of the spark by a few degrees, which is the standard way to mitigate knock. This results in a reduction of power but saves the engine from damage. The KLR has the ability to montior each cylinder individually for knock, and adjust the spark timing separately for each one so that the engine can be kept running on the ragged edge of what's possible, in total safety. All this stuff is considered very basic, standard tech for any car now, but in the mid 1908s it was revolutionaty. 

As with the DME, the KLR is based on an Intel microcontroller and an ADC. But instead of the common 8051, the KLR uses a more primitve device - the MCS-48 (specifically the 8039 variant). Presumably this was cheaper. It does run at a higher speed (11Mhz vs 6Mhz for the DME's 8051) and that could have been a factor too. But it's simplistic instruction set and minimal timer and interrupt resources definitely complicated the code. Like the late model DMEs, the entire program (including maps) lives on an EPROM - in this case, a 24-pin 4K chip. 
