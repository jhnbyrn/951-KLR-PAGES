# Porsche 951 DME/KLR Info

## Introduction

### What's This About?

The purpose of this site is to document the inner workings of the Porsche 944 Turbo engine management system. This system consists of 2 ECUs:

1. The DME (this is the main ECU that runs the engine)
2. The KLR (this is a secondary ECU that handles boost control and knock control)

The site started mainly with info about the KLR but has now started to grow to incude code walkthroughs and other articles on the DME. 

The role of the KLR in the 951's engine management is very thorougly explained in the [Technik](reference/TECHNIK491321.pdf) document. That document is a good starting point if you landed here wondering what this is all about. 

The details of the KLR hardware and software have always been a bit of a mystery, though. The DME has been reverse-engineered to varying extents by various people, and aftermarket re-writes have been on sale for years with lots of improvements over the original. Some of the workings of the original code have been made public too as part of [this](https://sourceforge.net/projects/opendme/) project. But to my knowledge, no one has ever done the same for the KLR, until now. 

### What's a KLR?
Briefly, the KLR is a secondary engine management computer found in the Porsche 944 Turbo. It works alongside the main computer (known as the DME) and provides 2 main functions:

* closed-loop boost control for the tubocharger

* knock (aka detonation) detection and mitigation

All the details that are missing here are in the Porsche Technik document linked in the previous section. 

### What's the Point of This Site?
I've done this purely for the purposes education and critical review - there's no commercial aspect to this project, and it's absolutely *not* a tuning or hacking tutorial. You might find it useful as a starting point for hacking - but be warned: I can't stand over the information I've provided here confidently enough to guarantee that you won't blow something up!

### Prerequisites
To understand this info on this site, you'll need a combination of basic microcontroller programming and electronics knowledge, and a reasonable understanding of how electronic engine management works. But you don't need to be an engineer or a professional programmer. The code we'll be looking at is pretty archaic, and I've had to read a lot of old documentation in order to make sense of it, so I'll try and explain everything as clearly as I can. 

I haven't completely reverse engineered the hardware - for me, it's really all about the code, the *logic*. But you can't understand the code without knowing what the various intput and output pins are hooked up to, so a certain amount of hardware analysis is unavoidable. The only non-trivial part of the hardware is the knock sensor amplifier, which I'll explain in detail. A knowledge of basic, hobbyist-level electronics is all you'll need (that's all I have anyway). 


## Navigating This Site

The DME stuff is still in early stages - I have a few articles on random topics but it's still missing a lot. For now I'll just list links to all the DME stuff without any particular order or structure. 

I've broken my work on the KLR down into 2 sections: a walkthrough of most of the key hardware and software, features, with code snippets (currently still work-in-progress), and a reference section with fairly raw information. You could just dive into the disassembled code in the reference section - it's annotated with brief function descriptions, and you can use the pin assignments page for reference. But I'm assuming that most people reading this will benefit from a more gentle introduction, and that's what the walkthrough is for. 

It's written to be read in the order presented below - the code can be pretty complicated in parts, even for simple features, and I need to assume that you have the basics down by the time you start looking at more advanced things like knock detection. 

In the reference section I've provided a few notes on how to read 8048 series code. Most of this information can be found in the official pdfs in the archive section below, but they're pretty long so I wanted to put some of the most important stuff into a more accessible document. If you find anything in the code tough going, it's worth taking a look at my notes. 


## DME

* [How the Motronic DME maps work](dme_map_info.md) *This explains the structure of the maps found in the DME code, and how to interpret the headings and data*

* [The Motronic map locations](dme_map_locations.md) *Here we get into the details of how the maps are looked up in the code.*

* [How the DME reads engine temperature](ntc_info.md) *This section breaks down the details of the DME's main temperature sensor and explains how temperature is measured and used in the code*

* [An overview of the DME fuel maps](dme_fuel_overview.md) *An explanation of the role that fuel maps actually play, and the concept of the base pulse width*

* [How engine load is calculated](dme_load_calculation.md) *This explores the concept of load and explains how it's calculated from airflow and RPM*

* [Engine load code walkthrough](dme_load_code_walkthrough.md) *Here we explore the actual code for load calculation, and work through an example to calculate the expected fuel pulse width*

* [The idle stabilizer valve routine](isv_routine.md) *This is a detailed code walkthrough of the routine that controls the ISV*

* [DME crankshaft sensors](dme_crank_sensor_hardware.md) *We explore the basics of how the DME measures crankshaft angles, without getting into the weeds of the actual code*

* [DME ignition timing routine](ignition_timing_code.md) *This is the code-walkthrough companion for the crank sensor article; here we __do__ get into the weeds of the actual code!* 

## KLR Hardware

* [Overview](hardware_overview.md) *A high-level overview of the KLR hardware.*

* [Knock Detection (hardware)](knock_hardware.md) *This section explains the signal conditioning for the knock sensor, and demonstrates how the self-test works*


## KLR Software

* [Basic KLR signal timing](klr_signal_timing.md) *Here we'll take a look at the most important input and output signals on the scope, and briefly discuss how they're generated, without getting into too much detail.*

* [How the KLR Measures Engine Speed](speed_measurement.md) *Understanding how engine speed is measured is essential if you want to understand how the signals are generated. It's also a soft introdudction to reading the 8048 assembly code.*

* [How the Ignition Signal is Generated](ignition_signal.md) *This section gets into the code in detail and explains exactly how the KLR generates the iginition output signal*

* [How the throttle position sensor is processed](klr_tps_processing.md) *Here we'll explore exactly how the KLR reads the varying voltage of the throttle position sensor (TPS) and creates the wide-open-throttle (WOT) signal for the DME*

* [RPM Map Axis](rpm_axis.md) *In this section we'll see how the raw engine speed we measured in the timer routine is turned into an rpm range value that can be used as the rpm axis for looking up map values*

* [RPM Constants](rpm_constants.md) *Here we'll look at a large number of small single-axis maps (rpm only) that store lots of important constants*

* [Cycling Valve PWM Generation]() *TBD*

* [Blink Codes]() *TBD*

* [Knock Detection](knock_detection.md) *This section goes through the entire knock detection routine step-by-step. This is by far the most complicated single routine in the KLR, so it's a pretty big section and it leans very heavily on the previous stuff.*

* [Exponential Smoothing](exponential_smoothing.md) *This is a quick explantion of a general purpose exponential smoothing routine that's used in many plces throughout the KLR code.*

* [ADC Reading]() *TBD*

* [Boost Control]() *TBD*

## Reference

* [Pin Assignments](pin_assignments.md)

* [Disassembled, annotated code](Annotated_Stock1987_951KLR.asm)

* [Outline of the code](outline_of_code.md)

* [Reading MCS48 Series Assembly Code](reading_code.md) *Some notes on how to read assembly code for the Intel 8048, aka MCS48 microcontrollers. This should make the rest of the site easier to understand.*

## Other Reference Material (Archived)

* [85 944 Turbo TECHNIK](reference/TECHNIK491321.pdf)
* [DME/KLR Test Plan](reference/DME_KLR_Test_Plan.pdf)
* [MCS48 User's Manual](reference/mcs48.pdf)
* [MCS48 Assembly Language Manual](reference/9800255D_MCS-48_and_UPI-41_Assembly_Language_Reference_Manual_Dec78.pdf)
