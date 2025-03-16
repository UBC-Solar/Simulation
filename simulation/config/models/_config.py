import abc
from pydantic import BaseModel, ConfigDict as _ConfigDict, model_validator
from typing import List, Type, Dict, Any
from simulation.utils import hash_dict
from anytree import Node


class ConfigDict(_ConfigDict):
    """
    A TypedDict for configuring Pydantic behaviour, with the added `subclass_field` optional setting.
    """
    subclass_type: str


class Config(BaseModel, abc.ABC):
    """
    The Config abstract base class allows for the construction of configuration object trees.


    """
    @classmethod
    def subclasses(cls) -> List[Type["Config"]]:
        """
        Recursively obtain all the subclasses of this type as a flat list.

        :return: a one-dimensional list of subclasses as Type[Config].
        """
        subclasses = cls.__subclasses__()
        return subclasses + [g for s in subclasses for g in s.subclasses()]

    @classmethod
    def tree(cls, parent: Node = None):
        fields = cls.model_fields

        node = Node(cls.__name__, parent=parent)

        for name, field in fields.items():
            field_class = field.annotation

            if hasattr(field_class, "tree"):
                field_class.tree(node)

            else:
                Node(f"{str(name)}: {field_class.__name__}", parent=node)

        return node

    @classmethod
    def build_from(cls, config_dict: Dict) -> "Config":
        """
        Create a configuration object from a dictionary. A subclass of this configuration object may be built if the
        dictionary contains the field specified by a model_config["subclass_type"] attribute and the value matches
        a subclass type name.

        :param config_dict: the dictionary that will be built into a configuration object
        :return: a configuration object of type `cls` OR a subclass of `cls`.
        """
        # Find if we have a setting that specifies how to identify subclasses
        if (subclass_field := getattr(cls, "model_config", {}).get("subclass_field")) is not None:
            try:
                subclass_type = config_dict[subclass_field]
                subclass_type_name = subclass_type + "Config"  # We need to manually add `Config` to the end

                subclasses: List[Type[Config]] = cls.subclasses()

                # Try to find a subclass with the name that matches our key
                for subclass in subclasses:
                    if subclass_type_name == subclass.__name__:
                        # Here, we promote the data belonging to the subclass
                        # to be top-level keys in the dictionary so that Pydantic can find
                        # them when validating the model.
                        config_dict.update(config_dict[subclass_type])

                        return subclass.model_validate(config_dict)

                else:
                    raise NameError(f"Could not find a Config subclass of "
                                    f"{cls.__name__} with name {subclass_type_name}!")

            except NotImplementedError:
                pass  # Fall through to the case where `map` doesn't exist

        # Otherwise, we should just build the object from here.
        return cls.model_validate(config_dict)

    @model_validator(mode="before")
    @classmethod
    def intercept_nested_configs(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Before model_validate runs, go through the model's fields and check for any nested configuration objects
        to properly build them with `Config.build_from` to ensure that they are properly promoted to the correct
        subclass when necessary.
        """
        for field_name, field_annotation in cls.model_fields.items():
            try:
                annotation: Type = field_annotation.annotation
                if issubclass(annotation, Config):
                    # TODO: Test if this try-except has a valid purpose since looking now I'm not convinced that
                    #  KeyError should be suppressed
                    try:
                        # Replace the dictionary data with an actual instance of the subclass
                        field_data = values[field_name]
                        values[field_name] = annotation.build_from(field_data)

                    except KeyError:
                        pass

            # An annotation like `tuple[float]` will cause a TypeError in issubclass, but we don't care anyway
            except TypeError:
                continue

        return values

    def __hash__(self):
        return hash_dict(self.model_dump())
