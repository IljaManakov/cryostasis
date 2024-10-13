__all__ = ["ImmutableError", "freeze", "deepfreeze"]

from typing import TypeVar


class ImmutableError(Exception):
    """Error indicating that you attempted to modify a frozen instance."""

    pass


Instance = TypeVar("Instance", bound=object)


def freeze(
    obj: Instance, *, freeze_attributes: bool = True, freeze_items: bool = True
) -> Instance:
    """
    Freezes a python object, making it effectively 'immutable'.
    Which aspects of the instance should be frozen can be tuned using the kw-only arguments ``freeze_attributes`` and ``freeze_items``.

    .. note

        This function freezes the instance in-place, meaning that, even if there are multiple existing references to the instance,
        the 'immutability' will be reflected on all of them.

    Args:
        obj: The object to freeze.
        freeze_attributes: If ``True``, the attributes on the instance will no longer be assignable or deletable. Defaults to ``True``.
        freeze_items: If ``True``, the items (i.e. the []-operator) on the instance will no longer be assignable or deletable. Defaults to ``True``.

    Returns:
        A new reference to the frozen instance. The freezing itself happens in-place. The returned reference is just for convenience.

    Examples:
        >>> from cryostasis import freeze
        >>>
        >>> class Dummy:
        ...     def __init__(self, value):
        ...         self.value = value
        >>>
        >>> d = Dummy(value=5)
        >>> d.value = 42        # ok
        >>> freeze(d)
        >>> d.value = 9001      # raises ImmutableError
        >>>
        >>> l = freeze([1,2,3])
        >>> l[0] = 5            #  raises ImmutableError
        >>> l.append(42)        #  raises ImmutableError
    """

    from .detail import _create_dynamic_frozen_type, IMMUTABLE_TYPES, Frozen
    from ._builtin_helpers import _set_class_on_builtin_or_slots

    if obj.__class__ in IMMUTABLE_TYPES or obj.__class__.__bases__[0] is Frozen:
        return obj

    obj_type = obj.__class__
    frozen_type = _create_dynamic_frozen_type(obj_type, freeze_attributes, freeze_items)
    if isinstance(obj, (list, set, dict)) or hasattr(obj_type, "__slots__"):
        _set_class_on_builtin_or_slots(obj, frozen_type)
    else:
        obj.__class__ = frozen_type
    return obj


def deepfreeze(
    obj: Instance, *, freeze_attributes: bool = True, freeze_items: bool = True
) -> Instance:
    """
    Freezes a python object and all of its attributes and items recursively, making all of them it effectively 'immutable'.
    For more information, see :func:`~cryostasis.freeze`.

    Args:
        obj: The object to deepfreeze.
        freeze_attributes: If ``True``, the attributes on the instances will no longer be assignable or deletable. Defaults to ``True``.
        freeze_items: If ``True``, the items (i.e. the []-operator) on the instances will no longer be assignable or deletable. Defaults to ``True``.

    Returns:
        A new reference to the deepfrozen instance. The freezing itself happens in-place. The returned reference is just for convenience.

    Examples:
        >>> from cryostasis import deepfreeze
        >>>
        >>> class Dummy:
        ...     def __init__(self, value):
        ...         self.value = value
        ...         self.a_dict = dict(a=1, b=2, c=[])
        >>>
        >>> d = Dummy(value=[1,2,3])
        >>> deepfreeze(d)
        >>> d.value = 9001              # raises ImmutableError
        >>> d.value[0] = 42             # raises ImmutableError
        >>> d.a_dict['c'].append(0)     # raises ImmutableError
    """

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
