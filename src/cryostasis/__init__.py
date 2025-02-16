import warnings
from types import FunctionType

from .detail import Instance, _unfreezeable
from pathlib import Path

__version__ = open(Path(__file__).parent / "version.txt").read()
del Path

__all__ = [
    "ImmutableError",
    "freeze",
    "deepfreeze",
    "thaw",
    "deepthaw",
    "is_frozen",
    "warn_on_enum",
    "deepfreeze_object_blacklist",
]

#: Enums cannot be made immutable by :func:`~cryostasis.freeze` (yet).
#: Hence, a warning is issued when an enum is encountered.
#: Set this variable to False to suppress the warning.
warn_on_enum = True

#: List of objects that will be ignored by :func:`cryostasis.deepfreeze`.
#: Any object placed in here will not be frozen and will also terminate the traversal (the object will become a leaf in the traversal graph).
deepfreeze_object_blacklist = list(_unfreezeable)

#: List of types, whose instances will be ignored by :func:`cryostasis.deepfreeze`.
#: Any object that is of a type placed in here will not be frozen and will also terminate the traversal (the object will become a leaf in the traversal graph).
deepfreeze_type_blacklist = list(_unfreezeable)

del _unfreezeable


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
    import gc

    from .detail import _create_frozen_type, _is_special, _unfreezeable, IMMUTABLE_TYPES
    from ._builtin_helpers import _set_class_on_builtin_or_slots

    if isinstance(obj, _unfreezeable):
        if warn_on_enum:
            warnings.warn(
                f"Skipping {obj} as enums are currently not supported in `freeze`",
                RuntimeWarning,
            )
        return obj

    # do nothing if already immutable or frozen
    if obj.__class__ in IMMUTABLE_TYPES or is_frozen(obj):
        return obj

    # special handling for mappingproxy
    # can be circumvented using gc to obtain the underlying dict
    if isinstance(obj, type(type.__dict__)):
        obj = gc.get_referents(obj)[0]

    frozen_type = _create_frozen_type(obj, freeze_attributes, freeze_items)
    if _is_special(obj):
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
    from .detail import _is_frozen_function, _is_special
    from ._builtin_helpers import _set_class_on_builtin_or_slots

    if not is_frozen(obj):
        return obj

    obj_type = obj.__class__
    initial_type = FunctionType if _is_frozen_function(obj) else obj_type.__bases__[1]
    if _is_special(obj) or _is_frozen_function(obj):
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

    return hasattr(obj, "__frozen__")


del Instance
