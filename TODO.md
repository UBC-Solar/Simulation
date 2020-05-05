#TODO

##Battery

- fix usage of variables in base_battery: make them parameterized.

- fix/handle behaviour when out of charge or charge exceeds battery capacity (throw exception? return a value? indicate to caller that something happened!)

- try to move more model-specific variables to basic_battery, as base_battery is supposed to be extensible across all possible batteries.

- avoid magic numbers

- fix pass on update function in BaseBattery, let BasicBattery override it (this is valid, as Python will leave something not implemented in a subclass when you don't declare it again)

##Motor

- please document all functions properly

