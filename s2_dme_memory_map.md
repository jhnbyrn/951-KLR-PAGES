#Porsche 944S2 memory map (Motronic M2.1)

## Variables

| Location | Purpose | Notes |
|----------|----------|----------|
3Ah | rpm/40 ||
42h | load ||
37h | NTC I air intake temp | |
38h | NTC II engine coolant temp ||
36h | battery voltage ||

## ADC Channels

| Channel | Pin | Purpose |
|----------|----------|----------|
0 | 26 | AFM |
1 | 27 | Battery voltage |
2 | 28 | NTC I |
3 | 1 | NTC II |
4 | 2 | unused (DME #43) |
5 | 3 | O2 sensor (via Bosch 20015 IC, S600 #10)|
6 | 4 | version code (DME #39)[1] |
7 | 5 | marked "power strg unused on S2" (DME #46) |

[1] not to be confused with "curve family" on DME #54, which doesn't use an ADC channel but is read into 20h.2 via the S710 hex buffer. Both are used together for region coding. 

## Pin/address assignments
### 8051 pins

| Function | Pin | Purpose |
|----------|----------|----------|
P1.0 | 1 | fuel injectors (batch) |
P1.1 | 2 | ignition |
P1.2 | 3 | reset for 68705 |
P1.4 | 5 | idle stabilizer |

### External addresses

## FQS
The FQS settings are located at 61ED. It's basically the same setup as ML1.x. 

The FQS switch is read via the data port, not via an ADC channel as with ML1.x - this means there's no decoding to do with ML2.x, we just get the 3 bits representing the 8 positions directly (into location 21h). 

The timing values are similar but not identical to ML1.x. With ML1.x we have 130 or 132 flywheel teeth, with each one being ~2.7 degrees. Timing values are represente in the code and maps as quarter-tooth values. With ML2.x, we have 6 degrees per tooth, and values are represented as eighth-tooth values. In both systems, the FQS positions 4-7 subtracts 4 units, so that's 3.0 degrees for ML2.x compared with ~2.7 for ML1.x

| Offset (FQS Position) | Hex value | Decimal value | Effect on fuel | Effect on timing | 
|--------------|--------------|--------------|--------------|--------------|
|0 |  80h |  128 | 0 | 0 |
|1 |  84h | 132 | + 3.1% | 0 |
|2 |  7Ch | 124 | - 3.1% | 0 | 
|3 | 88h | 136 | + 6.25% | 0 |
|4 |  80h |  128 | 0 | -3 |
|5 |  84h | 132 | + 3.1% | -3 |
|6 |  7Ch | 124 | - 3.1% | -3 | 
|7 | 88h | 136 | + 6.25% | -3 |

## Maps
The raw map data is generally stored starting at 6670. The main map lookup table starts at 6450 (Table 2). This table in turn is address via offsets stored at 6000 (Table 1).

The ML2.x system uses a more complicated map lookup process than the one used in ML1.x. In that system, each map has a unique 1-byte identifier. So if you see a reference to "map 5" in the code, it's easy to find that map, and conversely if you see a particular map that interests you in the raw binary, it's relatively easy to figure out how that map is referred to in the code, so you can find where it's read and figure out its purpose. 

In ML2.x system, the two intermediate lookup tables are used with *variable* offsets, with the result that different functions throughout the program have their own 1-byte map namespace. So "map 5" doesn't unabiguously identify one particular map in ML2.x; you have to know how the table pointers are set when the code refers to that map. That can be traced in the code with a little work. But going the other way - that is, starting with a raw map location like 0x6670 and figuring out where that's used in the code - is much harder. 

| Purpose | Axes | Table 1 | Table 2 | Local name | Raw location | First value | Last value |
|--------|--------|--------|--------|--------|--------|--------|--------|
| fuel, part throttle | 3Ah, 42h |  608D | 64F2 | 7 | 6C84 | | |
| fuel, WOT | 3Ah | 608D | 64F2 | 6 | 6C62 | | |
| spark advance, part throttle | 3Ah, 42h | 608D | 64F2 | 4 | 6BAA | | |
| spark advance, WOT | 3Ah | 608D | 64F2 | 1 | 6B74 | | |
| dwell | 3Ah, 36h | 603C | 6490 | 11 | 681C | | |
