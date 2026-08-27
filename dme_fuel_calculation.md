# DME Fuel calculation

## Overview

In [the load calculation section](dme_load_calculation.md) we saw how the DME calculates the base pulse width for the fuel injectors. This calculation takes airflow and rpm into account, and produces a pulse with value that is proportional to airflow and inversely proportional to rpm. This should make sense if we want to maintain a constant AFR, since (all other things being equal):

* doubling the airflow should double the fuel pulse width
* doubling the rpm should halve the pulse width

If the second point sounds wrong, just remember that we said *all other things being equal*. So if the rpm doubles, but the airflow doesn't change at all, that means we have twice as many fuel inection events per second as we had before, but the fuel requirement is the same as before, so the pulse width should be halved. 

In practice of course, airflow and rpm usually change at the same time. Our *ceteris paribus* example is therefore contrived and unrealistic, but it's helpful for understanding the relationship between each variable and the base fuel pulse. Another difference between theory and practice is that we actually *don't* want to maitain a constant AFR. The proper AFR varies by driving condition in numerous ways. For example:

* colder temperatures require a richer AFR
* acceleration requires a richer AFR
* boost requires a richer AFR
* sometimes fuel economy demands a slightly leaner AFR

We'll get into some of these points in more detail later, but for now we'll just cover the basic mechanism by which the AFR is controlled. 

## AFR adjustment

The basic mechanism that Motronic uses for AFR adjustment is simply multiplying the base fuel pulse width by a fraction. For instance, multiplying by 1.03 has the effect of adding 3% fuel. It's hard to intuitively see the effect this has on the AFR, but we can calculate it easily using 14.7 / 1.03 = 14.2. So 14.2:1 is a 3% richer mixture than the default 14.7:1. These fractions can be smaller than 1 too, which results in a leaner mixture, and of course they can be equal to 1 which means that they have no effect. 

In the simplest possible terms, the base pulse width is multiplied by one fraction after another, each one corresponding to some type of correction (temperature, acceleration, altitude, load, and so on). Each one might lean or richen the mixture, and the end result is the actual pulse width that's used to control the injector. It's quite possible that all the fractions will just be 1, and so the actual pulse width will just be the base pulse width. 

The fractions are stored in maps and constants. Some of the maps use rpm and load as their inputs, others use coolant temperature, or intake air temperature. 

In practice, the implementation of this mechanism can be hard to follow in the code because of the difficulties of working with fractions in an 8-bit system. If you look at the raw map values, what you'll see is that most of the cells are close to the value 128. In fact, 128 is the denominator of the fractions used in the vast majority of fuel correction values, and it's not stored anywhere (instead, it's implicit in how the multiplication works). So whenever you see 128 in a fuel map, that means 1, and indicates that this cell targets 14.7:1 (that is, it does nothing). If you see, 132 for example, that means 132/128, which is 1.03125, or (for hand-waving purposes) 1.03. So a map cell of 132 means a target AFR of 14.2:1. 
