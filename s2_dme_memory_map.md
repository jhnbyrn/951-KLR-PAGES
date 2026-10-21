# Porsche 944S2 memory map (Motronic M2.1)

## Variables

| Location | Purpose | Notes |
|----------|----------|----------|
3Ah | rpm/40 ||
42h | load ||
37h | NTC I air intake temp | |
38h | NTC II engine coolant temp ||
36h | battery voltage ||
70h | injector dead-time | |

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

| Function | Pin # | Purpose |
|----------|----------|----------|
P1.0 | 1 | fuel injectors (batch) |
P1.1 | 2 | ignition |
P1.2 | 3 | reset for 68705 |
P1.4 | 5 | idle stabilizer |

### External addresses

These devices are read using ```movx```. 

| Address space | Device | Purpose |
|---------------|---------------|-------|
| BCxx | ADC (channels 0-7) | various sensors (see ADC channels above) |
| F4 | S706 hex buffer | TPS idle (bit 0), TPS WOT (bit 1), region curve family (bit 2) |
| EC | S707 hex buffer | FQS (bits 0-3) | 
| DC | S708 | |
| 7Exx | external SRAM | |
| 7Fxx | external SRAM | |

## FQS
The FQS settings are located at 61ED. It's basically the same setup as ML1.x. 

The FQS switch is read via the data port, not via an ADC channel as with ML1.x - this means there's no decoding to do with ML2.x, we just get the 3 bits representing the 8 positions directly (into location 21h). 

The timing values are similar but not identical to ML1.x. With ML1.x we have 130 or 132 flywheel teeth, with each one being ~2.7 degrees. Timing values are represented in the code and maps as quarter-tooth values. With ML2.x, we have 6 degrees per tooth, and values are represented as eighth-tooth values. In both systems, the FQS positions 4-7 subtracts 4 units, so that's 3.0 degrees for ML2.x compared with ~2.7 for ML1.x

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
| fuel, part throttle | 3Ah (12), 42h (12) |  608D | 64F2 | 7 | 6C84 | | |
| fuel, WOT | 3Ah (16) | 608D | 64F2 | 6 | 6C62 | | |
| spark advance, part throttle | 3Ah (12), 42h (12) | 608D | 64F2 | 4 | 6BAA | | |
| spark advance, WOT | 3Ah (16) | 608D | 64F2 | 1 | 6B74 | | |
| dwell | 3Ah (12), 36h (7)| 603C | 6490 | 11 | 681C | | |
| injector dead time | 36h (4) | 6004 | 6468 | 1 | 66A8 | | |

* Injector latency/dead-time:

| Variable 0x36 (54) | Value |
|---|---|
| 118 | 118 |
| 176 | 94 |
| 206 | 64 |
| 235 | 49 |


* Fuel, part throttle:

| 0x3a \ 0x42 | 26 | 36 | 42 | 47 | 57 | 69 | 78 | 90 | 105 | 117 | 126 | 140 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 21 | 120 | 120 | 120 | 120 | 119 | 119 | 116 | 115 | 113 | 113 | 109 | 98 |
| 25 | 117 | 117 | 118 | 119 | 118 | 118 | 117 | 116 | 116 | 113 | 106 | 95 |
| 37 | 117 | 117 | 118 | 119 | 119 | 119 | 119 | 119 | 118 | 116 | 112 | 112 |
| 50 | 117 | 117 | 118 | 119 | 120 | 120 | 119 | 118 | 118 | 116 | 116 | 116 |
| 62 | 117 | 117 | 119 | 120 | 120 | 120 | 119 | 119 | 122 | 122 | 119 | 119 |
| 75 | 117 | 120 | 120 | 120 | 120 | 121 | 120 | 120 | 120 | 120 | 116 | 116 |
| 100 | 117 | 120 | 120 | 121 | 122 | 123 | 122 | 122 | 123 | 125 | 125 | 125 |
| 112 | 117 | 120 | 120 | 121 | 121 | 122 | 122 | 122 | 122 | 123 | 131 | 131 |
| 125 | 120 | 120 | 120 | 121 | 121 | 122 | 123 | 124 | 124 | 140 | 142 | 142 |
| 144 | 121 | 121 | 121 | 122 | 122 | 122 | 123 | 126 | 139 | 143 | 142 | 135 |
| 150 | 120 | 120 | 120 | 122 | 122 | 123 | 125 | 126 | 121 | 141 | 131 | 131 |
| 163 | 119 | 119 | 119 | 122 | 122 | 123 | 125 | 126 | 138 | 138 | 137 | 128 |

* Fuel, WOT:

| Variable 0x3a (58) | Value |
|---|---|
| 25 | 81 |
| 38 | 122 |
| 50 | 131 |
| 62 | 130 |
| 69 | 128 |
| 75 | 125 |
| 81 | 128 |
| 87 | 140 |
| 100 | 136 |
| 112 | 136 |
| 125 | 129 |
| 137 | 116 |
| 145 | 112 |
| 150 | 110 |
| 160 | 109 |
| 163 | 116 |

* Spark advance, part throttle:

| 0x3a \ 0x42 | 26 | 36 | 42 | 47 | 57 | 69 | 78 | 90 | 105 | 117 | 126 | 140 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 21 | 42 | 45 | 51 | 58 | 65 | 54 | 55 | 49 | 45 | 45 | 45 | 45 |
| 25 | 42 | 45 | 58 | 71 | 65 | 54 | 55 | 49 | 45 | 45 | 45 | 45 |
| 37 | 42 | 64 | 73 | 73 | 65 | 63 | 60 | 58 | 54 | 54 | 54 | 54 |
| 50 | 42 | 71 | 73 | 74 | 71 | 69 | 68 | 66 | 62 | 61 | 61 | 61 |
| 62 | 58 | 75 | 79 | 78 | 75 | 72 | 69 | 68 | 67 | 64 | 64 | 64 |
| 75 | 91 | 79 | 79 | 79 | 80 | 80 | 80 | 79 | 78 | 70 | 71 | 71 |
| 100 | 91 | 85 | 83 | 77 | 78 | 77 | 76 | 69 | 67 | 65 | 63 | 62 |
| 112 | 91 | 91 | 85 | 85 | 83 | 81 | 77 | 72 | 68 | 66 | 67 | 67 |
| 125 | 91 | 91 | 85 | 85 | 76 | 74 | 70 | 68 | 62 | 60 | 61 | 61 |
| 144 | 91 | 91 | 85 | 85 | 81 | 76 | 74 | 70 | 64 | 64 | 65 | 65 |
| 150 | 91 | 91 | 91 | 91 | 79 | 74 | 76 | 76 | 71 | 67 | 67 | 66 |
| 163 | 91 | 91 | 91 | 91 | 82 | 78 | 78 | 78 | 75 | 71 | 66 | 56 |

* Spark advance, WOT:

| Variable 0x3a (58) | Value |
|---|---|
| 25 | 46 |
| 38 | 55 |
| 50 | 62 |
| 62 | 65 |
| 69 | 71 |
| 75 | 72 |
| 81 | 72 |
| 87 | 72 |
| 105 | 63 |
| 112 | 68 |
| 125 | 62 |
| 137 | 63 |
| 145 | 66 |
| 150 | 68 |
| 160 | 68 |
| 163 | 56 |

* Dwell

| 0x3a \ 0x36 | 88 | 117 | 147 | 176 | 206 | 235 | 242 |
|---|---|---|---|---|---|---|---|
| 1 | 110 | 88 | 36 | 22 | 18 | 14 | 10 |
| 2 | 111 | 89 | 37 | 23 | 18 | 14 | 10 |
| 4 | 114 | 91 | 38 | 23 | 18 | 14 | 10 |
| 8 | 127 | 101 | 42 | 26 | 20 | 16 | 10 |
| 13 | 151 | 121 | 50 | 31 | 24 | 19 | 10 |
| 20 | 192 | 155 | 64 | 40 | 31 | 24 | 13 |
| 27 | 192 | 192 | 80 | 49 | 39 | 30 | 16 |
| 36 | 192 | 192 | 102 | 63 | 49 | 38 | 21 |
| 52 | 192 | 192 | 110 | 72 | 57 | 45 | 27 |
| 91 | 192 | 192 | 192 | 125 | 99 | 79 | 47 |
| 140 | 192 | 192 | 192 | 192 | 152 | 121 | 72 |
| 165 | 187 | 187 | 187 | 187 | 179 | 143 | 84 |
