# The Motronic map read routine

In the [section on maps](dme_map_info.md) we examined Motronic map structure and how to make sense of their content. In this section we'll explore the map lookup process in more detail. 

## Map locations
The maps are stored in the upper 4K of program memory, and as a result of that, it takes 2 bytes to represent their locations. But if you look at the Motronic code, you won't see these 16-bit locations being referenced directly. You'll typically see things like this:

```
	mov	r2,#37h
	lcall	X051d ;this is the map lookup routine
```

For convenience, the code refers to maps using a short, 1-byte identifier, like 37h in the example above. The map read routine at 051D must convert this into the true 16-bit map location. You might guess that this is done via a lookup table. You're almost right; it's actually *two* lookup tables. 

The first table is located at 1090. Let's follow an example using the map 37 from the code snippet above. We load the literal value "37" into __r2__ and call the map read routine at 051D. The following logic happens inside that routine:

Our offset into the table at 1090 is 37h, which gets us to

|1090 | 1091 | 1092 | 1093 | ... | <span style="color:red">10C7</span> | 10C8 | ...|
|-----|-----|-----|-----|-----|-----|-----|-------
|00 | 02 | 02 | 1A | ... | <span style="color:red">__4a__</span> | 4c | ...|

The output, __4a__ is now used as the offset into the second table at 11E0, which gets us to 122A:

|11E0 | <span style="color:grey">11E1</span> | 11E2 | <span style="color:grey">11E3</span> | ... | <span style="color:red">122A</span> | <span style="color:grey">122B</span> | 122C | ... |
|-----|-----|-----|-----|-----|-----|-----|-------|----|
| 12 | A0 | 12 | A6  | ... | <span style="color:red">__15__</span> | <span style="color:red">__F9__</span> | 16 | ...|

...and our final output is the 2-byte value 15F9. This is the true location of the map. 

Or, if you prefer to see it as plain English:

1. The map's short number (37h, or 55 decimal in this example) is added to a base map table location, __1090__, and we read a single byte from that location
2. In this case we have 1090+37 = 10C7, and the value we find at __10c7__ is __4A__. 
3. Now we take the offset of the map table, __11E0__, and add 4A, to get __122A__. 
4. At location __122A__, we read __2__ bytes to get 15F9. This is our actual map location. 


## But why though
Now we may well ask, *why* do all this? Why not just refer to the maps by their real location wherever we need to refer to them in the code? There are a couple of reasons. 

Firstly, it's much simpler to have a 1-byte identifier for each map because that's the native "word" size of the 8051. To load a 2-byte value takes 2 instructions, and this would have to happen dozens of times throughout the code. Additionally, related maps are often in adjacent locations in the first table, which provides a very convenient way to select alternate versions of a given map depending on some condition. For example:

```
	mov	r2,#38h
	jnb	20h.2,X0964
	inc	r2
```

In this example (taken from the [ISV routine](isv_routine.md))) we load map 38h into r2 in preparation for the map read routine, but then we check a condition and switch to map 39h if that condition is met before calling the read routine. This would not be so simple if we had to load the real map location, since obviously the locations couldn't be adjacent. 

Another advantage: changing the maps. Suppose we have some branch in the code where we choose one of two different maps (like the example above). But at some point we decide we don't really need them to be different after all. We can just overwrite the entry for the second map in the Table 1090, and avoid touching the code that uses the map. This works both ways - if we know we want different maps but we haven't had time to create both yet, we can make the table point at the same map for both inputs, and then change it later when we get around to creating the second map. You can do this by changing the code where you use the map, but that's just not quite as convenient. Is this worth the hassle? That probably depends on how often the maps need to change. My guess would be that early in the development process, they changed a lot.  

So that helps to explain why we have the first, 1-byte table. But couldn't the output of that table be the real 2-byte location of the map? That would mean we'd have to __inc__ twice to select an adjacent map, but that's not a big deal, and is surely a small price to pay for eliminating another lookup step right? That would probably work but there are advantages to having the second lookup table. I can't say for certain what the Bosch engineers were thinking, so what follows is my best guess at why it's useful to have the second table. 

If you have read my other article on [montronic maps](dme_map_info.md) you will know that the map read routine uses both 1-axis (2D) and 2-axis (3D) maps. What's not clear in that article is how it tells the difference. The answer may surprise you: if the output value from the 1090 table is even, then the map read routine treats it as a 1-axis map. If odd, it's treated as a 2-axis map. So in the example we used earlier, we had __4A__ which is even - a 1D map. But since this value is used as an offset into Table 11E0, this even/odd system constrains where the value can point to. As you add more and more maps (and perhaps change your mind about how many axes each one needs) re-arranging the maps to make sure that they all live at a location with the right parity could be really tedious. But this problem is much easier to deal with when you have Table 11E0 as an intermediate step. Each entry in this table is just two bytes so it's relatively easy to re-arrange it to get each type of map into a suitable location. The actual maps can stay where they are - the parity of their *true* locations doesn't matter. And Table 1090 can stay the same too! 

There's a [saying in software engineering](https://en.wikipedia.org/wiki/Fundamental_theorem_of_software_engineering):

>> We can solve any problem by introducing an extra level of indirection.

True or not, hopefully this discussion sheds a little light on how to trace map lookups!



