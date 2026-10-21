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

| Purpose | Axes | Table 1 | Table 2 | Local name | Raw location | 
|--------|--------|--------|--------|--------|--------|
| fuel, part throttle | 3Ah (12), 42h (12) |  608D | 64F2 | 7 | 6C84 |
| fuel, WOT | 3Ah (16) | 608D | 64F2 | 6 | 6C62 | 
| spark advance, part throttle | 3Ah (12), 42h (12) | 608D | 64F2 | 4 | 6BAA |
| spark advance, WOT | 3Ah (16) | 608D | 64F2 | 1 | 6B74 |
| dwell | 3Ah (12), 36h (7)| 603C | 6490 | 11 | 681C |
| injector dead time | 36h (4) | 6004 | 6468 | 1 | 66A8 |

### Units

* Fuel and injector latency units look the same as the 8v cars
* I'm pretty sure ignition timing values are in 1/8th tooth counts, that is 0.75 degrees, with __30__ being TDC, i.e. zero. So the formula should be:

```spark_advance = 0.75 * (map_value - 30)```

### Injector latency/dead-time:

Address: `0x66a8`

Data start (file offset): `0x66ae`. Size: 4 values (1-axis, 4 bytes).

Raw breakpoints, axis 1: 118 176 206 235

| Variable 0x36 (54), battery voltage in V | Value |
|---|---|
| 8.1 | 118 |
| 12.1 | 94 |
| 14.1 | 64 |
| 16.1 | 49 |

### Fuel, part throttle:

Address: `0x6c84`

Data start (file offset): `0x6ca0`. Size: 12 rows x 12 columns (144 bytes), stored row-major: each row is 12 consecutive bytes.

Raw breakpoints, axis 1: 21 25 37 50 62 75 100 112 125 144 150 163

Rows: variable 0x3a (58), engine speed in rpm. Columns: variable 0x42 (66).

| 0x3a \ 0x42 | 26 | 36 | 42 | 47 | 57 | 69 | 78 | 90 | 105 | 117 | 126 | 140 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 840 | 120 | 120 | 120 | 120 | 119 | 119 | 116 | 115 | 113 | 113 | 109 | 98 |
| 1000 | 117 | 117 | 118 | 119 | 118 | 118 | 117 | 116 | 116 | 113 | 106 | 95 |
| 1480 | 117 | 117 | 118 | 119 | 119 | 119 | 119 | 119 | 118 | 116 | 112 | 112 |
| 2000 | 117 | 117 | 118 | 119 | 120 | 120 | 119 | 118 | 118 | 116 | 116 | 116 |
| 2480 | 117 | 117 | 119 | 120 | 120 | 120 | 119 | 119 | 122 | 122 | 119 | 119 |
| 3000 | 117 | 120 | 120 | 120 | 120 | 121 | 120 | 120 | 120 | 120 | 116 | 116 |
| 4000 | 117 | 120 | 120 | 121 | 122 | 123 | 122 | 122 | 123 | 125 | 125 | 125 |
| 4480 | 117 | 120 | 120 | 121 | 121 | 122 | 122 | 122 | 122 | 123 | 131 | 131 |
| 5000 | 120 | 120 | 120 | 121 | 121 | 122 | 123 | 124 | 124 | 140 | 142 | 142 |
| 5760 | 121 | 121 | 121 | 122 | 122 | 122 | 123 | 126 | 139 | 143 | 142 | 135 |
| 6000 | 120 | 120 | 120 | 122 | 122 | 123 | 125 | 126 | 121 | 141 | 131 | 131 |
| 6520 | 119 | 119 | 119 | 122 | 122 | 123 | 125 | 126 | 138 | 138 | 137 | 128 |

### Fuel, WOT:

Address: `0x6c62`

Data start (file offset): `0x6c74`. Size: 16 values (1-axis, 16 bytes).

Raw breakpoints, axis 1: 25 38 50 62 69 75 81 87 100 112 125 137 145 150 160 163

| Variable 0x3a (58), engine speed in rpm | Value |
|---|---|
| 1000 | 81 |
| 1520 | 122 |
| 2000 | 131 |
| 2480 | 130 |
| 2760 | 128 |
| 3000 | 125 |
| 3240 | 128 |
| 3480 | 140 |
| 4000 | 136 |
| 4480 | 136 |
| 5000 | 129 |
| 5480 | 116 |
| 5800 | 112 |
| 6000 | 110 |
| 6400 | 109 |
| 6520 | 116 |


### Spark advance, part throttle:

Address: `0x6baa`

Data start (file offset): `0x6bc6`. Size: 12 rows x 12 columns (144 bytes), stored row-major: each row is 12 consecutive bytes.

Raw breakpoints, axis 1: 21 25 37 50 62 75 100 112 125 144 150 163

Rows: variable 0x3a (58), engine speed in rpm. Columns: variable 0x42 (66).

| 0x3a \ 0x42 | 26 | 36 | 42 | 47 | 57 | 69 | 78 | 90 | 105 | 117 | 126 | 140 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 840 | 42 | 45 | 51 | 58 | 65 | 54 | 55 | 49 | 45 | 45 | 45 | 45 |
| 1000 | 42 | 45 | 58 | 71 | 65 | 54 | 55 | 49 | 45 | 45 | 45 | 45 |
| 1480 | 42 | 64 | 73 | 73 | 65 | 63 | 60 | 58 | 54 | 54 | 54 | 54 |
| 2000 | 42 | 71 | 73 | 74 | 71 | 69 | 68 | 66 | 62 | 61 | 61 | 61 |
| 2480 | 58 | 75 | 79 | 78 | 75 | 72 | 69 | 68 | 67 | 64 | 64 | 64 |
| 3000 | 91 | 79 | 79 | 79 | 80 | 80 | 80 | 79 | 78 | 70 | 71 | 71 |
| 4000 | 91 | 85 | 83 | 77 | 78 | 77 | 76 | 69 | 67 | 65 | 63 | 62 |
| 4480 | 91 | 91 | 85 | 85 | 83 | 81 | 77 | 72 | 68 | 66 | 67 | 67 |
| 5000 | 91 | 91 | 85 | 85 | 76 | 74 | 70 | 68 | 62 | 60 | 61 | 61 |
| 5760 | 91 | 91 | 85 | 85 | 81 | 76 | 74 | 70 | 64 | 64 | 65 | 65 |
| 6000 | 91 | 91 | 91 | 91 | 79 | 74 | 76 | 76 | 71 | 67 | 67 | 66 |
| 6520 | 91 | 91 | 91 | 91 | 82 | 78 | 78 | 78 | 75 | 71 | 66 | 56 |


### Spark advance, WOT:

Address: `0x6b74`

Data start (file offset): `0x6b86`. Size: 16 values (1-axis, 16 bytes).

Raw breakpoints, axis 1: 25 38 50 62 69 75 81 87 105 112 125 137 145 150 160 163

| Variable 0x3a (58), engine speed in rpm | Value |
|---|---|
| 1000 | 46 |
| 1520 | 55 |
| 2000 | 62 |
| 2480 | 65 |
| 2760 | 71 |
| 3000 | 72 |
| 3240 | 72 |
| 3480 | 72 |
| 4200 | 63 |
| 4480 | 68 |
| 5000 | 62 |
| 5480 | 63 |
| 5800 | 66 |
| 6000 | 68 |
| 6400 | 68 |
| 6520 | 56 |


### Dwell

Address: `0x681c`

Data start (file offset): `0x6833`. Size: 12 rows x 7 columns (84 bytes), stored row-major: each row is 7 consecutive bytes.

Raw breakpoints, axis 1: 1 2 4 8 13 20 27 36 52 91 140 165

Raw breakpoints, axis 2: 88 117 147 176 206 235 242

Rows: variable 0x3a (58), engine speed in rpm. Columns: variable 0x36 (54), battery voltage in V.

| 0x3a \ 0x36 | 6.0 | 8.0 | 10.1 | 12.1 | 14.1 | 16.1 | 16.6 |
|---|---|---|---|---|---|---|---|
| 40 | 110 | 88 | 36 | 22 | 18 | 14 | 10 |
| 80 | 111 | 89 | 37 | 23 | 18 | 14 | 10 |
| 160 | 114 | 91 | 38 | 23 | 18 | 14 | 10 |
| 320 | 127 | 101 | 42 | 26 | 20 | 16 | 10 |
| 520 | 151 | 121 | 50 | 31 | 24 | 19 | 10 |
| 800 | 192 | 155 | 64 | 40 | 31 | 24 | 13 |
| 1080 | 192 | 192 | 80 | 49 | 39 | 30 | 16 |
| 1440 | 192 | 192 | 102 | 63 | 49 | 38 | 21 |
| 2080 | 192 | 192 | 110 | 72 | 57 | 45 | 27 |
| 3640 | 192 | 192 | 192 | 125 | 99 | 79 | 47 |
| 5600 | 192 | 192 | 192 | 192 | 152 | 121 | 72 |
| 6600 | 187 | 187 | 187 | 187 | 179 | 143 | 84 |
