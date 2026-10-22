# Porsche 944S2 memory map (Motronic M2.1)

## Checksum (IMPORTANT!)
The Motronic M2.x uses a ROM checksum and sets a fault code if the image has been changed. The simplest thing to do for tuning is to simply disable this check, rather than calculating and updating the checksum for every change. So here's a version of the original with the check disabled (but no other changes). 

This image came from a 9442 DME with the following part # info on the label:

__Bosch 0 261 200 195__
__944.618.124.02__ 
__TYP 944S-MW-02__

[944 S2 DME (chip label 1267356132), CHECKSUM DISABLED, USE THIS ONE!](binaries/944_S2_DME_1267356132_checksum_disabled.bin)
[944 S2 DME (chip label 1267356132), original](binaries/944_S2_DME_1267356132.bin)

## Variables

| Location | Purpose | Notes |
|----------|----------|----------|
3Ah | rpm/40 ||
42h | load ||
37h | NTC I air intake temp | |
38h | NTC II engine coolant temp |
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
T0 | 14 | hall effect (cam) sensor |

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
| injector dead time | 36h (4) | 6004 | 6458 | 1 | 66A8 |

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
| 8 | 118 |
| 12 | 94 |
| 14 | 64 |
| 16 | 49 |

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
| 3480 | 135 |
| 4000 | 140 |
| 4480 | 136 |
| 5000 | 135 |
| 5480 | 123 |
| 5800 | 117 |
| 6000 | 116 |
| 6400 | 115 |
| 6520 | 122 |

### Spark advance, part throttle:

Address: `0x6baa`

Data start (file offset): `0x6bc6`. Size: 12 rows x 12 columns (144 bytes), stored row-major: each row is 12 consecutive bytes.

Raw breakpoints, axis 1: 21 25 37 50 62 75 100 112 125 144 150 163

Rows: variable 0x3a (58), engine speed in rpm. Columns: variable 0x42 (66).

| 0x3a \ 0x42 | 26 | 36 | 42 | 47 | 57 | 69 | 78 | 90 | 105 | 117 | 126 | 140 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 840 | 41 | 44 | 50 | 57 | 63 | 52 | 52 | 46 | 41 | 41 | 41 | 41 |
| 1000 | 41 | 44 | 57 | 70 | 63 | 52 | 52 | 46 | 41 | 41 | 41 | 41 |
| 1480 | 41 | 63 | 72 | 72 | 63 | 61 | 57 | 55 | 50 | 50 | 50 | 50 |
| 2000 | 41 | 70 | 72 | 73 | 69 | 67 | 66 | 63 | 59 | 57 | 57 | 57 |
| 2480 | 57 | 74 | 78 | 77 | 73 | 70 | 67 | 66 | 64 | 61 | 60 | 60 |
| 3000 | 90 | 78 | 78 | 78 | 78 | 78 | 78 | 77 | 75 | 67 | 67 | 67 |
| 4000 | 90 | 84 | 82 | 76 | 76 | 75 | 74 | 67 | 64 | 62 | 59 | 58 |
| 4480 | 90 | 90 | 84 | 84 | 81 | 79 | 75 | 70 | 65 | 63 | 63 | 63 |
| 5000 | 90 | 90 | 84 | 84 | 74 | 72 | 68 | 66 | 59 | 57 | 57 | 57 |
| 5760 | 90 | 90 | 84 | 84 | 79 | 74 | 72 | 68 | 61 | 61 | 61 | 61 |
| 6000 | 90 | 90 | 90 | 90 | 77 | 72 | 74 | 74 | 68 | 64 | 63 | 62 |
| 6520 | 90 | 90 | 90 | 90 | 80 | 76 | 76 | 76 | 72 | 68 | 62 | 52 |

### Spark advance, WOT:

Address: `0x6b74`

Data start (file offset): `0x6b86`. Size: 16 values (1-axis, 16 bytes).

Raw breakpoints, axis 1: 25 38 50 62 69 75 81 87 105 112 125 137 145 150 160 163

| Variable 0x3a (58), engine speed in rpm | Value |
|---|---|
| 1000 | 42 |
| 1520 | 51 |
| 2000 | 58 |
| 2480 | 61 |
| 2760 | 67 |
| 3000 | 68 |
| 3240 | 68 |
| 3480 | 68 |
| 4200 | 59 |
| 4480 | 64 |
| 5000 | 58 |
| 5480 | 59 |
| 5800 | 62 |
| 6000 | 64 |
| 6400 | 64 |
| 6520 | 52 |

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
