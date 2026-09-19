# KLR boost control gain maps

This is a small 2-axis map located at 992 in the KLR's program memory. It's actually four maps packed into one, and here we'll unpack them and take a close look at each one. 

All four maps relate to boost control, and they break down like this:

Bits | Purpose
-----|--------
0, 1 | smoothing factor for the target boost filtering process
2, 3 | gain for the derivative/spool assist term
4 | gain for the proportional term
5, 6, 7 | over all gain for the combined closed loop term

When the map is read the value for the current rpm/throttle settings is stored in 6Bh. The way most of the map values are extracted is simply by bit masking, with rotation where necessary. For example, here's how the target boost filtering routine does it:

```
0xdde mov  a,@r0		;r0=6B
0xddf anl  a,#$3		;mask all but bits 0,1
0xde1 add  a,#$1		;a = 1, 2, 3 or 4
```

And here's how the derivative term routine does it:

```
0xe5d mov  a,@r0
0xe5e rr   a
0xe5f rr   a
0xe60 anl  a,#$3
0xe62 add  a,#$1
```

The gain values are used in different ways: some are exponents, others are multipliers. We'll look at each in more detail next. 

## Smoothing factor

The target boost value that's used to calculate the P and I terms of the controller is not the value read directly from the target boost map (51h). Instead, that value is filtered through a queue of three variables: 51h -> 55h -> 53h. The final value 53h is the one that's used for the controller, and this lags behind the real map value. 

If you have read about the [exponential smoothing routine](exponential_smoothing.md) you may recall that one of its inputs is a *smoothing factor* - this factor determines what how slowly the filtered value follows the original value. The smoothing factor is used as a reciprocal of the form ```1/2^n``` in the smoothing routine, so bigger numbers make the filtered value follow the target more slowly. This part of the PID gain map is used as the value *n* in the previous formula, so that at higher rpm, we have less smoothing/faster following. In fact the throttle position rows of this map are all the same, so we can simplify it like this - here, the raw values are shown as ```2^n```:

| RPM | 2003 | 2393 | 2873 | 3316 | 3922 | 4544 | 5401 | max |
|---|---|---|---|---|---|---|---|---|
| 2^n | 8 | 8 | 8 | 4 | 4 | 4 | 2 | 2 |

## Spool assist gain

The boost controller uses a derivative-based term to help build boost when demand suddenly increases (i.e. quick throttle opening). The basic value of the term is the derivative of the boost delta. The way that's achieved is that the delta is calculated continuously based on the the raw (unfiltered) target boost value 51h, and then another variable follows this via the exponential smoothing routine; the spool assist term is just the difference between the delta and the filtered follower value, multiplied by an exponential gain factor. 

As with the smoothing factor we saw previously, all the throttle position rows are the same, so we really just have:

| RPM | 2003 | 2393 | 2873 | 3316 | 3922 | 4544 | 5401 | max |
|---|---|---|---|---|---|---|---|---|---|
| 2^n | 1 | 1 | 2 | 4 | 2 | 2 | 4 | 4 |

Again, these values are in the exponential form that's actually used. So at higher rpm, we have more gain for this term. 

## Proportional gain

Only a single bit (bit 4) is used for the P term gain, and in fact it isn't really used at all: it's zero in all cells. This is a bit of a strange situation because in fact [the code that calculates the P term](klr_pi_boost_control_code.md) wouldn't be safe if the gain was increased. It's exponential, so a value of zero means a gain of 1. 

## Final gain stage

After the various controller terms are combined (into 63h), there's a final gain stage that's applied when the correction is applied to the cycling valve pulse. This value is encoded in the three most significant bits of the gain map. The mask that selects these values sets all the lower bits to 1, and the resulting value multiplies the correction value 63h. But only the high byte of this multiplication used, so we effectively have a division by 256. Thus the raw map values OR'd with 00011111 just represent fractions of 256 - therefore this stage can only reduce the correction, or leave it alone. Here's the final effect of this map:

| Throttle deg \ RPM | 2003 | 2393 | 2873 | 3316 | 3922 | 4544 | 5401 | max |
|---|---|---|---|---|---|---|---|---|
| 61 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| 69 | 1.0 | 0.9 | 0.7 | 0.6 | 0.6 | 0.7 | 0.7 | 0.9 |
| 77 | 1.0 | 0.6 | 0.5 | 0.5 | 0.5 | 0.6 | 0.6 | 0.7 |
| 90 | 1.0 | 0.7 | 0.5 | 0.5 | 0.5 | 0.6 | 0.7 | 0.9 |

Unlike the smaller maps, this one really does vary by both throttle and rpm. And in fact it's pretty much the *opposite* shape of the target boost map. I have to speculate about the reason for this, but I think it's probably to compensate for the increased control authority that the cycling valve would have at higher boost. 

It's tempting to show it as a surface in 3D like the boost maps, but the gain map does not have any interpolation, and I don't want to give a false impression that it does. Instead, a heat map probably makes more sense:

[]!(images/klr_boost_control/pid_final_gain_stage_1.png)


## Appendix - raw map data

### Complete map:

| Throttle deg \ RPM | 2003 | 2393 | 2873 | 3316 | 3922 | 4544 | 5401 | max |
|---|---|---|---|---|---|---|---|---|
| 61 | 227 | 227 | 231 | 234 | 230 | 230 | 233 | 233 |
| 69 | 227 | 195 | 167 | 138 | 134 | 166 | 169 | 201 |
| 77 | 227 | 131 | 103 | 106 | 102 | 134 | 137 | 169 |
| 90 | 227 | 163 | 103 | 106 | 102 | 134 | 169 | 201 |


### Smoothing:

* raw:

| Throttle deg \ RPM | 2003 | 2393 | 2873 | 3316 | 3922 | 4544 | 5401 | max |
|---|---|---|---|---|---|---|---|---|
| 61 | 3 | 3 | 3 | 2 | 2 | 2 | 1 | 1 |
| 69 | 3 | 3 | 3 | 2 | 2 | 2 | 1 | 1 |
| 77 | 3 | 3 | 3 | 2 | 2 | 2 | 1 | 1 |
| 90 | 3 | 3 | 3 | 2 | 2 | 2 | 1 | 1 |

* translated: 

| Throttle deg \ RPM | 2003 | 2393 | 2873 | 3316 | 3922 | 4544 | 5401 | max |
|---|---|---|---|---|---|---|---|---|
| 61 | 8 | 8 | 8 | 4 | 4 | 4 | 2 | 2 |
| 69 | 8 | 8 | 8 | 4 | 4 | 4 | 2 | 2 |
| 77 | 8 | 8 | 8 | 4 | 4 | 4 | 2 | 2 |
| 90 | 8 | 8 | 8 | 4 | 4 | 4 | 2 | 2 |

### Derivative:

* raw:

| Throttle deg \ RPM | 2003 | 2393 | 2873 | 3316 | 3922 | 4544 | 5401 | max |
|---|---|---|---|---|---|---|---|---|
| 61 | 0 | 0 | 1 | 2 | 1 | 1 | 2 | 2 |
| 69 | 0 | 0 | 1 | 2 | 1 | 1 | 2 | 2 |
| 77 | 0 | 0 | 1 | 2 | 1 | 1 | 2 | 2 |
| 90 | 0 | 0 | 1 | 2 | 1 | 1 | 2 | 2 |

* translated

| Throttle deg \ RPM | 2003 | 2393 | 2873 | 3316 | 3922 | 4544 | 5401 | max |
|---|---|---|---|---|---|---|---|---|
| 61 | 1 | 1 | 2 | 4 | 2 | 2 | 4 | 4 |
| 69 | 1 | 1 | 2 | 4 | 2 | 2 | 4 | 4 |
| 77 | 1 | 1 | 2 | 4 | 2 | 2 | 4 | 4 |
| 90 | 1 | 1 | 2 | 4 | 2 | 2 | 4 | 4 |

### Final gain:

* raw:

| Throttle deg \ RPM | 2003 | 2393 | 2873 | 3316 | 3922 | 4544 | 5401 | max |
|---|---|---|---|---|---|---|---|---|
| 61 | 255 | 255 | 255 | 255 | 255 | 255 | 255 | 255 |
| 69 | 255 | 223 | 191 | 159 | 159 | 191 | 191 | 223 |
| 77 | 255 | 159 | 127 | 127 | 127 | 159 | 159 | 191 |
| 90 | 255 | 191 | 127 | 127 | 127 | 159 | 191 | 223 |

* translated:

| Throttle deg \ RPM | 2003 | 2393 | 2873 | 3316 | 3922 | 4544 | 5401 | max |
|---|---|---|---|---|---|---|---|---|
| 61 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| 69 | 1.0 | 0.9 | 0.7 | 0.6 | 0.6 | 0.7 | 0.7 | 0.9 |
| 77 | 1.0 | 0.6 | 0.5 | 0.5 | 0.5 | 0.6 | 0.6 | 0.7 |
| 90 | 1.0 | 0.7 | 0.5 | 0.5 | 0.5 | 0.6 | 0.7 | 0.9 |
