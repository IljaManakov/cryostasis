__all__ = ["ImmutableError", "freeze"]

from typing import TypeVar


class ImmutableError(Exception):
    pass


Instance = TypeVar("Instance", bound=object)


def freeze(
    obj: Instance, *, freeze_attributes: bool = True, freeze_items: bool = True
) -> Instance:
    from .detail import _create_dynamic_frozen_type, IMMUTABLE_TYPES, Frozen
    from ._builtin_helpers import _set_class_on_builtin

    if obj.__class__ in IMMUTABLE_TYPES or obj.__class__.__bases__[0] is Frozen:
        return obj

    obj_type = obj.__class__
    frozen_type = _create_dynamic_frozen_type(obj_type, freeze_attributes, freeze_items)
    if isinstance(obj, (list, set, dict)):
        _set_class_on_builtin(obj, frozen_type)
    else:
        obj.__class__ = frozen_type
    return obj


def deepfreeze(
    obj: Instance, *, freeze_attributes: bool = True, freeze_items: bool = True
) -> Instance:
    from itertools import chain

    # set for keeping id's of seen instances
    # we only keep the id's because some instances might not be hashable
    # also we don't want to hold refs to the instances here and weakref is not supported by all types
    seen_instances: set[int] = set()

    def _deepfreeze(obj, freeze_attributes, freeze_items):
        if id(obj) not in seen_instances:
            seen_instances.add(id(obj))
        else:
            return obj

        freeze(obj, freeze_attributes=freeze_attributes, freeze_items=freeze_items)

        # freeze all attributes
        try:
            attr_iterator = vars(obj).values()
        except TypeError:
            pass
        else:
            for attr in attr_iterator:
                _deepfreeze(attr, freeze_attributes, freeze_items)

        if isinstance(obj, str):
            return obj

        # freeze all items
        try:
            item_iterator = iter(obj)
            if isinstance(obj, dict):
                item_iterator = chain(item_iterator, obj.values())
        except TypeError:
            pass
        else:
            for item in item_iterator:
                _deepfreeze(item, freeze_attributes, freeze_items)

        return obj

    return _deepfreeze(obj, freeze_attributes, freeze_items)


del TypeVar, Instance
