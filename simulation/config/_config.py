import abc
from pydantic import BaseModel, ConfigDict as _ConfigDict
from typing import List, Type, Dict
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

        for _, field in fields.items():
            field_class = field.annotation

            if hasattr(field_class, "tree"):
                field_class.tree(node)

            else:
                Node(field_class.__name__, parent=node)

        return node

    @classmethod
    def build_from(cls, config_dict: Dict) -> "Config":
        """
        Create a configuration object from a dictionary. A subclass of this configuration object may be built if the
        dictionary contains the field specified by a model_config["subclass_type"] attribute and the value matches
        a subclass type name.

        :param config_dict: the dictionary that will be built into a configuration object
        :return: a configuration object
        """
        # Find if we have a setting that specifies how to identify subclasses
        if (subclass_field := getattr(cls, "model_config", {}).get("subclass_field")) is not None:
            try:
                subclass_type = config_dict[subclass_field]
                subclass_type_name = subclass_type + "Config"   # We need to manually add `Config` to the end

                subclasses: List[Type[Config]] = cls.subclasses()

                # Try to find a subclass with the name that matches our key
                for subclass in subclasses:
                    if subclass_type_name == subclass.__name__:
                        return subclass.model_validate(config_dict)

                else:
                    raise NameError(f"Could not find a Config subclass of "
                                    f"{cls.__name__} with name {subclass_type_name}!")

            except NotImplementedError:
                pass    # Fall through to the case where `map` doesn't exist

        # Otherwise, we should just build the object from here.
        return cls.model_validate(config_dict)

    def __hash__(self):
        return hash_dict(self.model_dump())
