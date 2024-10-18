__all__ = ["ImmutableError", "freeze", "deepfreeze"]

from .detail import Instance


class ImmutableError(Exception):
    """Error indicating that you attempted to modify a frozen instance."""

    pass


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
    from .detail import _traverse_and_apply
    from functools import partial

    return _traverse_and_apply(
        obj,
        partial(freeze, freeze_attributes=freeze_attributes, freeze_items=freeze_items),
    )


def thaw(obj: Instance) -> Instance:
    """
    Undoes the freezing on an instance.
    The instance will become mutable again afterward.

    Args:
        obj: The object to make mutable again.

    Returns:
        A new reference to the thawed instance. The thawing itself happens in-place. The returned reference is just for convenience.
    """
    from .detail import IMMUTABLE_TYPES, Frozen
    from ._builtin_helpers import _set_class_on_builtin_or_slots

    obj_type = obj.__class__
    bases = obj_type.__bases__

    if obj_type in IMMUTABLE_TYPES:
        return obj  # Nothing to do here

    if bases[0] is not Frozen:
        import warnings

        warnings.warn(f"Attempting to thaw a non-frozen instance {obj}.")
        return obj

    initial_type = obj_type.__bases__[1]
    if isinstance(obj, (list, set, dict)) or hasattr(obj_type, "__slots__"):
        _set_class_on_builtin_or_slots(obj, initial_type)
    else:
        object.__setattr__(obj, "__class__", initial_type)

    return obj


def deepthaw(obj: Instance) -> Instance:
    """
    Undoes the freezing on an instance and all of its attributes and items recursively.
    The instance and any object that can be reached from its attributes or items will become mutable again afterward.

    Args:
        obj: The object to deep-thaw.

    Returns:
        A new reference to the deep-thawed instance. The thawing itself happens in-place. The returned reference is just for convenience.
    """
    from .detail import _traverse_and_apply

    return _traverse_and_apply(obj, thaw)


def is_frozen(obj: Instance) -> bool:
    """
    Check that indicates whether an object is frozen or not.

    Args:
        obj: The object to check.

    Returns:
        True if the object is frozen, False otherwise.
    """
    from .detail import Frozen

    return isinstance(obj, Frozen)


del Instance
