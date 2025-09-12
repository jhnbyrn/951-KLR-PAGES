# How the Motronic DME Maps Work
The DME has many, many maps - over 80 in fact. They're stored in the second 4k of program memory. 

Extracting the map info can be useful for tools like TunerPro and also generally just for visualizing and understanding the parameters the engine was designed to work with. So let's dive into the Motronic map structure. 

We'll start with a small example to keep things simple. This map is located at 15F9 and it's the target rpm map for idle. There are various ways to visualize a map; for a simple one like this, just seeing a table with familiar units of measurement is enough for human-readability:

Temperature (degrees C) | -25 | 50 | 75
Target speed (in rpm) | 1000 | 920 | 840

For practical reasons, however, the DME code doesn't work directly in these familiar units. Here's how the map looks from a programmer's perspective:

30 | 139 | 178
25 | 23 | 2

This is much more obscure - clearly there's some translation needed to get from units (in the code) to common everyday units like degrees C and revolutions per minutee. 

But it's worse - even this less familiar representation is still not how it's actually stored! Here's what that same map truly looks like, in it's native setting, viewed in a hex editor:


![](images/dme_map_reading/idle_target_map_1.png)


It might be a little clearer to copy those raw bytes and format them here:

`13 03 6d 27 4d 19 17 15`

That's quite a bit different from the more readable ones we just looked at. So how does this pile of numbers represent a map of target engine speeds? In the following sections we'll break this down piece by piece and learn how that nice human-readable representations are derived from the raw data. 

First, note that the values I pulled from the raw source are in hexadecimal form. When we want to help with readability, we'll convert them to decimal. (Sometimes, I might even remember to tell you when I do that). Here's a breakdown of the structure of the raw map:

* first byte: input variable 
* second byte: axis length (let's call it "n" - in this case, n=3)
* next n bytes: axis values, i.e headings
* next n bytes: the actual values (this is what TunerPro XDF files generally consider to be the "start" of the map) 

Now each of these might seem a little cryptic so I'll explain them one by one. 

## First byte: the input variable
This value is the RAM address of the input variable. In the Motronic code, key engine parameters live in certain memory locations. They're stored there after being read by the ADC (and possibly after some post-processing) and then they always stay there; those locations are reserved just for their respective parameters. So the maps are written with the appropriate input variable location hard-coded. Here are the most important ones:

```
37h: rpm
49h: load
13h: engine coolant temp
11h: system voltage
```

So in our example map above, the first byte is 13 and that tells us that this map depends on engine temp (NTC). 

## Second byte: the length of the axis
This is pretty straightforward; the number 3 in this example just tells us that there are 3 values in the axis! So this map only cares about 3 different temperature ranges. As a rule, the right-most value in the map applies to all input values to the right, and vice-versa for the left. So for instance if the right-most axis number was 0 deg. C, then the value corresponding to that would apply for all temperatures below 0C. 

## Next n bytes: the axis values
This is where things start to get a little more complicated. We said earlier that the 3 values following the axis length are the headings of the map. Let's look at these values in decimal to make things clearer:

```109 39 77```

Now you might ask things like: what do these numbers mean? Are they C, or F? Don't tell me they're Kelvins?! Let's leave the question of units until a little later and for now just deal with questions like: why are they spaced so unevenly, and why don't they go in one direction? 

For reasons that will be clearer later, Motronic software encodes map headings as diffs or deltas instead of the values you'd expect. The best way to explain this is to explain what the code does. Let's say we have an input value of 177. The map routine will start at the right-hand end of the axis, and start adding the headings, one at a time, to the intput value until the add results in an overflow. 

For example we'll get

```177 + 77 = 254``` (no overflow, keep going)
```254 + 39 = 293``` (this is > than 255, so we have an overflow). 

Once an overflow is detected, we have found the columns that our input falls between. Now we could just take the index of the column that triggered the overflow (2 in this example) and use that as an index into the values list, and return that value. In practice though, the Motronic code does something more sophisticated than that called linear interpolation. The short explanation of this is: for inputs that fall between column headings (which is what happens most of the time), the DME figures out the most appropriate in-between value and returns that even though it's not explicitly stored in the map. We'll leave the details til later.  

## Last n bytes: the actual map values
Finally we get to the part everyone actually cares about - the map values themselves! What do they represent? Generally to see what they represent we have to look at the code that uses them. Immediately after a map is read, the return value is usually compared to some known variable. For example, when the map in our example is read, the resulting value is then compared to the value in 37. You might recall that 37 is the location of engine speed. That tells us that this map contains engine speed values. Otherwise, why would the programmers want to compare the returned value to engine speed? You knew that at the start because I told you, but this is how I knew. 

What about units - what units are the map values in? That is the hardest question of all to answer. For one thing, there isn't one answer! Probably the most important observation we can make here is that it is not possible to figure out what the numbers in a map mean without knowing something about what's going on outside the little metal enclosure of the DME. 

Let's look at a few examples:

### Units: Engine speed
The short explanation here is that the units of engine speed are RPM/40. That is, the number 1 means 40RPM, 2 means 80RPM etc. 

How do we know that? The way engine speed is measured in Motronic is by counting the number of speed sensor pulses within a fixed timer interval. That part can be ascertained by reading the code. But to know that 1 unit equals 40RPM, someone had to go an count the teeth on the flywheel! And someone always has to do something like that to answer such questions. 

A word about units and naming conventions. Everyone and I mean everyone uses the term "rpm" interchangeably with "engine speed" and I don't want to be that guy so I will just keep doing that to avoid confusion. But the Motronic maps don't deal in rpm, strictly speaking they use units of rpm/40. 

### Units: Battery voltage
First let's address why this is necessary, and then how it's even possible. The DME needs to know the current battery voltage because many critial things in the engine perform differently depending on the voltage, for example fuel injectors, ignition coils etc. Pulse widths and dwell times need to be adjusted for the battery voltage. 

The DME measuring it's own supply voltage is possible because the ADC has a fixed 5v reference, and the supply voltage is divided by approximately 3.5 before being read into one of the ADC's channels. So it can measure voltages up to around 17.5v. 

My rough calculations give a conversion rate of 1 unit in the code equals 0.0686 volts. 


### Units: Engine temperature
Now we get into the territory that made me say this question of units is one of the hardest of all to answer. The DME uses an NTC temperature sensor which is not linear. Immediately after the temp sensor is read by the ADC, it's linearized using a special map. You can think of this map as a complementary curve that corrects the natural curve of the NTC sensor. The sensor value is also complemented (i.e. inverted) so that we end up with a linear scale where lower numbers correspond to lower temperatures. This is handy and intuitive, but the details of how all this is done can wait til another time. 

To cut a long story short for now, the temperature ends up as a fairly straight line with an offset of around 65 and a slope of somewhere around 1.46. With that in mind we can take any value in the code, subtract 65 and divide the result by 1.46 to get a pretty good value for the temperature in degrees C. This is not perfect but it's close. Bear in mind that the NTC sensors have a very wide tolerance range, and as a result the map headings are very approximate. 
