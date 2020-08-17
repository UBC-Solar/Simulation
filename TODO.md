#TODO
To be complete at the end this Saturday, 09 May 2020

##For Everyone

- If a line of code is too long, shorten it using line breaks. PEP8 specifies 72 columns as a recommended length, but try to keep it below 90

- Document your code properly. Write descriptive function specifications. Use the """ """

- Dont put comments at the end of a line of code. Put comments on top of a line of code (PEP8)

- avoid magic numbers

##Battery - Mihir

- fix usage of variables in base_battery: make them parameterized.

- fix/handle behaviour when out of charge or charge exceeds battery capacity (throw exception? return a value? indicate to caller that something happened!)

- try to move more model-specific variables to basic_battery, as base_battery is supposed to be extensible across all possible batteries.

- fix pass on update function in BaseBattery, let BasicBattery override it (this is valid, as Python will leave something not implemented in a subclass when you don't declare it again)

##Motor - Harry and Chris Aung

- Clean up code as above and submit pull request. Fisher might have more comments

##Vehicle Body Losses - Fisher and David

- Currently, David has put the Vehicle Drag in the motor class. But it would be better if the vehicle drag is implemented as a seperate class

###

Energy produced by the arrays depend on the following variables
- location, location is known
- time and day, is also known

Speed of the car is given for this value
