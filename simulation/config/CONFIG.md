# Objected-Oriented Configuration


`Simulation` uses a strongly object-oriented system for configuration. First of all, all configuration is described by configuration objects which inherit from the `Config` base class. The `Config` base class itself is a [Pydantic](pydantic.com) model, and so will its subclasses.

## Basic Usage

Briefly, Pydantic models allow for class fields to be annotated and type-checked upon instantiation: they are a straightforward way to have immutable, type-safe data containers.

As an example,
```python
from pydantic import Field
from simulation.config import Config, ConfigDict


class InitialConditions(Config):
    """
    Configuration object describing the initial conditions for a simulation.
    """
    model_config = ConfigDict(frozen=True)

    current_coord: tuple[float, float]  # Initial Position of the car
    initial_battery_soc: float = Field(ge=0.0, le=1.0)  # 0% <= SOC < 100%
    start_time: int  # Time since the beginning of the first day (12:00:00AM) in s

```
We,

1. Make a class called `InitialConditions` inherit from `Config`
2. Add a class variable called `model_config` which stores configuration for Pydantic. We set `frozen=True` to make the object immutable.
3. Add class field `current_coord` and annotate it with `tuple[float, float]`
4. Add a class field `initial_battery_soc`, annotate it with `float`, and set it to be a `Field` that is restricted to be between 0.0 and 1.0 by setting the parameters `ge=0.0` and `le=1.0`.
5. Add a class field called `start_time` and annotate it with `int`. 

The result is an immutable object which will be type-checked upon instantiation have exactly the fields we just created and guaranteed to satisfy the types we annotated it with, and restricted the numerical value in the case of `initial_battery_soc`.

## Subclassing

The `Config` object has one neat trick added onto it that regular Pydantic models don't have. 

As an example, imagine we actually have two different kinds of initial conditions (for some reason). Maybe sometimes we know the end time, and other times we don't. We _could_ add an optional parameter to the model, which would be a good idea in this simple case, but for more advanced usage where we have more dramatic differences, we can do something else.

First, we will modify initial conditions to have a new field, `initial_conditions_type`, add add the parameter `subclass_type="initial_conditions_type"` to `model_config`.

```python
from pydantic import Field
from simulation.config import Config, ConfigDict


class InitialConditions(Config):
    """
    Configuration object describing the initial conditions for a simulation.
    """
    model_config = ConfigDict(frozen=True, subclass_type="initial_conditions_type")

    current_coord: tuple[float, float]  # Initial Position of the car
    initial_battery_soc: float = Field(ge=0.0, le=1.0)  # 0% <= SOC < 100%
    start_time: int  # Time since the beginning of the first day (12:00:00AM) in s
    
    initial_conditions_type: str

```

Then, create a _subclass_ of `InitialConditions`, let's call it `TimedInitialConditionsConfig`.

```python
from simulation.config import InitialConditions


class TimedInitialConditions(InitialConditions):
    end_time: int
```

The way inheritance works in Python is that `TimedInitialConditions` will inherit all the fields of `InitialConditions`.
Now, we can use the `build_from` factory method available from `Config` to build either `TimedInitialConditions` or `InitialConditions` dynamically by setting `initial_conditions_type`!

```python
>>> initial_conditions_dict = {
    "current_coord": [10, 10],
    "initial_battery_soc": 0.1,
    "start_time": 10000
}

>>> type(InitialConditions.build_from(initial_conditions_dict))
"<class 'InitialConditions'>"

>>> timed_initial_conditions_dict = {
    "current_coord": [10, 10],
    "initial_battery_soc": 0.1,
    "start_time": 10000,
    "initial_conditions_type": "TimedInitialConditions",
    "end_time": 10000
}

>>> type(InitialConditions.build_from(timed_initial_conditions_dict))
"<class 'TimedInitialConditionsConfig'>"
```
