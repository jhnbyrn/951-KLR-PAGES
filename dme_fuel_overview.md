The fueling section of the DME code is the most complicated part of the program. The idea is simple enough: measure some key variables (load, rpm etc.) and determine how much fuel to inject. But the range of variables and the way that they affect the final fuel quantity is very comlpicated.

Here's a quick overview of the most important fuel adjustments the DME performs (in no particular order):

* load/base pulse width calculation
* driving mode (idle/PT/WOT)
* warm-up (coolant temp) adjustment
* startup enrichment
* acceleration enrichment
* FQS, altitude and air temp adjustment
* lambda correction

That isn't even an exhaustive list. When you consider the fact that just a few years prior to the advent of the Motronic system, all fueling was done mechanically, it really puts the sheer sophistication of this system for its time into perspective. Imagine having to design a mechanical system that can do even half the things in that list!

In this chapter I want to discuss the strategy of fuel calculation from a very basic perspective. 

And the simplest, most important thing we can say from this perspective is that the goal of all these fuel calculations is to come up with a number that controls how long the fuel injectors will be opened for, for a given revolution. This number should be the number of timer ticks that the injector is turned on for. We load that number into the timer, turn the injector on, and then when the timer reaches zero we turn the injector off. Simple. 

The second most important thing to say is that the steps that lead to this final number can be divided into two kinds: the base calulation, and the adjustments. 

To explain this in more detail, let's first dispense with a common misconception about fuel maps. If you've heard of fuel maps before, and you're aware that they allow a fuel value to be looked up by various inputs like rpm and load, you might expect that the cells of the maps contain the number we're looking for - that is, something that represents a certain amount of injector on-time. Or at least something that can be translated into on-time. But that's not the case, at least in the Motronic system. In this system, the maps only contain fractions that multiply an existing injector pulse width number (usually to increase it a by a small proportion, but occasionally to reduce it). 

The same thing is true for basically all the fuel adjustments - the fuel quality switch, altitude adjustment, temperature adjustments etc. They're all just fractions that mean things like "increase fuel by 6%". 

So where does this existing pulse width value come from? It's calculated from two numbers: rpm and airflow. The details are somewhat involved because of the way the AFM works, but roughly speaking it's airflow divided by rpm. There is some scaling to convert the resulting number into an appropriate number of timer ticks for the routine that controls the injector, and we call this number the base pulse width, or BPW. 

The BPW is calibrated based on the known fuel delivery rate of the engine so that it always results in an AFR of 14.7:1 - as long as the AFM is working correctly (with no leaks), the injectors are clean, the wiring is in good shape, and the fuel pressure regulator is working correctly. 

Now you have surely heard the term "load" used in reference to fuel injection systems as a sort of measurment of how hard the engine is working at a given moment. And you might know that this is measured as airflow per rpm, that is airflow divided by rpm. That means that BPW and load are really the same thing! In Motronic, there are two different numbers used for BPW and load, just because the units need to be different. The injector pulse time needs to be a fairly large, 16-bit number, since it counts timer ticks with high resolution. But there's also a load value that's used as a map input for various things, which needs to be scaled into a smaller 8-bit value to work with the map lookup routine. But rest assured these two numbers represent the same thing, and are always proportional - in fact the smaller, 8-bit load value is literally just the high byte of the BPW value. 

Now, if a 14.7 AFR was all we ever needed, then the calculation of the BPW would be the end of the story, and no fuel maps would be needed at all. The maps exist because 14.7 is not always the ideal AFR. Lots of conditions require a richer AFR. The ideal AFR depends on many factors, but most commonly load, boost and temperature. Wait, load? Again? That's confusing right? We already used airflow to calculate load, i.e. BPW, to get the AFR to 14.7, and now I'm saying we sometimes use the load value again to get a different AFR? Well yes, that is exactly what I'm saying. The 14.7 ratio is appropriate for fairly light loads. When the engine is working harder (that is, more airflow per rpm) we usually want a richer mixture. And when the engine is boosting, we want it even richer still to help with cooling.

Putting this together, we can give a very rough overview of the fuel calulation process (although in the code, the steps don't happen in quite this order):

1. measure rpm and airflow, and calculate BPW and load
2. check driving mode (idle, part throttle or wide-open throttle) and select the appropriate map
3. use rpm (and possibly load) to look up the apporpriate map value
4. multiply the BPW by the value we looked up from the map
5. use engine temperature (and possibly rpm and load) to look up more values from other maps
6. multiply the BPW by each of these values

So in summary we always start with a BPW which should get us 14.7 AFR and then the map values multiply this pulse width to get a different (usually richer) AFR. Thus we can think of each the values in the map cells as representing a particular AFR. 

Let's take a look at some actual fuel maps in raw form and analyze their meaning a little. 

RPM/Load |     21 |    26 |     37  |     42 |     48 |    53  |     63 |     79 |     90 |    100 |    122 |    142
---------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------
     800 |    133 |   133  |  133   | 133    | 133    | 133    | 132    | 131    | 131    | 131    | 131    | 131
     960 |    133    133    133    132    132    132    132    132    132    132    132    132
    1120 |    133    133    133    132    132    132    132    132    132    132    132    132
    1440 |    133    134    134    134    134    134    136    136    137    137    137    137
    1760 |    133    134    134    135    136    136    136    136    137    143    143    143
    2080 |    133    134    135    136    136    137    137    137    137    138    149    149
    2400 |    133    134    136    136    136    137    137    137    138    140    148    148
    3360 |    133    135    136    136    138    138    138    138    139    140    141    150
    4000 |    133    135    136    136    138    138    138    139    139    140    141    147
    4640 |    133    135    137    137    139    139    139    139    139    139    139    143
    5600 |    133    135    136    136    136    137    137    137    137    137    137    138
    6240 |    136    136    138    138    138    137    136    136    136    136    136    136

The way to read these numbers is as fractions, where the denominator is 128. This value of 128 is not explicitly stored anywhere. Instead, the value that's read from the map is divided by 128 in the code after the map is read. The reason it's done this way is that division by 128 (or indeed any power of 2) is very easy and efficient in 8-bit assembly code. But unfortunately it does complicate the code quite a bit. 

(I don't want to get too deep into the weeds of that here, so for now I'll just say that what happens is this: the 16-bit BPW gets multiplied by the raw map cell value, resulting in a 24-bit number, but then the top two bytes are taken as the result, discarding the lower byte. This constitutes an rough division by 256. Then the result is shifted to the left one place, which is a multiplication by 2. Thus overall we have division by 128. This entire process needs to be repeated for every map that's looked up in the fuel calculation process.)

So with that in mind, we can see that a map cell value of say 134 really means 134/128=~1.046, which means a roughly 4.6% increase in fuel over the base 14.7 AFR, in other words about 14.0 AFR. So when visualizing these maps, we could show each cell as an AFR to indicate its true meaning. 

Now let's take a look at the wide-open throttle fuel map:

  RPM |    Value
------|-----------------
    1000 |      138
    1480 |      143
    2000 |      149
    2120 |      151
    2240 |      154
    2520 |      157
    3000 |      157
    3280 |      159
    3520 |      159
    4000 |      157
    4520 |      152
    5000 |      146
    5520 |      141
    5800 |      138
    6000 |      136
    6240 |      136

The most obvious fact to note here is that it only has one input - rpm. This fact has led to a lot of confusion over the years, with tuners often believing (wrongly) that "the AFM is ignored" or "load plays no role in WOT fueling". Of course you now know that can't be true - the BPW is always used, and is always derived from the AFM signal. 

What's different about the WOT map is that load plays no role in adjusting the AFR. Let's work out what this really means. Suppose you floor the throttle completely, 100%. You should hit full boost before 3280rpm. The map value for that is 159/128 or ~11.8 AFR. So this is the AFR that the factory tuners thought was appropriate for full load/full boost at 3280 rpm. So far so good. 

But in the 951, the WOT driving mode is active whenever the throttle position is above 65 degrees, or about 72%. So suppose you open the throttle to say 75%. Then you won't hit full boost - or anywhere near it - at 3280rpm. Since you'll be at some much lower load than full boost, you might expect that some leaner ratio than 11.8 is appropriate. But 11.8 is what you'll get, because the WOT map assumes full load. There's no real harm in this and it was probably done to save memory. Part throttle is where the driver spends most of their time and where driveability, efficiency and emissions control are most important, so part throttle gets a full 2-axis map, and always gives an AFR that's ideal for the actual current load. WOT gives an AFR that's safe for maximum load/boost, and acceptable for ~72% load, if perhaps a little wasteful. 

Of course all this assumes that the BPW was correct to begin with, and that is based on the real airflow measurement. If that measurement is wrong for any reason (e.g. intake leaks, damaged AFM etc., or exceeding the AFM's limits) then your AFR under WOT will be wrong! The fact that load isn't used in the map lookup won't save your BPW! 

So let me say it once more: the AFM is not ignored at wide open throttle!


