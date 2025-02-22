from __future__ import annotations
import weakref
from copy import deepcopy
from enum import Enum, EnumMeta
from functools import wraps, update_wrapper
from inspect import signature
from types import (
    FunctionType,
    MethodType,
    SimpleNamespace,
    BuiltinFunctionType,
    WrapperDescriptorType,
    MethodWrapperType,
    MethodDescriptorType,
    ClassMethodDescriptorType,
    NotImplementedType,
)
from typing import TypeVar, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from cryostasis import Exclusions

Instance = TypeVar("Instance", bound=object)

# Currently unfreezeable. Might be supported in the future.
_unfreezeable = (Enum, EnumMeta, staticmethod, classmethod)


def _is_special(obj):
    """
    Helper for determining whether ``obj`` is an object that does not allow ``__class__`` assignment
    and needs to be handled with _builtin_helpers.
    """

    if isinstance(obj, (list, set, dict)):
        return True

    if hasattr(obj.__class__, "__slots__"):
        return True

    if isinstance(obj, type):
        return True

    if isinstance(obj, FunctionType):
        return True

    if isinstance(obj, SimpleNamespace):
        return True

    return False


def _raise_immutable_error(*args, **kwargs):
    """Small helper for raising ImmutableError. This function is also used as a substitute for mutable methods on builtins."""
    from . import ImmutableError

    raise ImmutableError("This object is immutable")


class Frozen:
    """
    Class that makes instances 'read-only' in the sense that changing or deleting attributes / items will raise an ImmutableError.
    The class itself is not instantiated directly.
    Rather, it is used as a base for a dynamically created type in :meth:`~cryostasis.freeze`.
    The dynamically created type is then assigned to the to-be-frozen instances __class__.
    Due to how Python's method resolution order (MRO) works, this effectively makes the instance read-only.
    """

    __frozen__ = True

    #: If True, setting or deleting attributes will raise ImmutableError
    __freeze_attributes = True

    #: If True, setting or deleting items (i.e. through []-operator) will raise ImmutableError
    __freeze_items = True

    def __init__(self):
        raise NotImplementedError(
            "Frozen is an implementation detail and should never be instantiated."
        )

    def __setattr__(self, name, value):
        if self.__freeze_attributes:
            _raise_immutable_error()
        else:
            return super().__setattr__(name, value)

    def __delattr__(self, name):
        if self.__freeze_attributes:
            _raise_immutable_error()
        else:
            return super().__delattr__(name)

    def __setitem__(self, name, value):
        if self.__freeze_items:
            _raise_immutable_error()
        else:
            return super().__setitem__(name, value)

    def __delitem__(self, name):
        if self.__freeze_items:
            _raise_immutable_error()
        else:
            return super().__delitem__(name)


_mutable_methods = {
    # Gathered from _collections_abc.py:MutableSequence and https://docs.python.org/3/library/stdtypes.html#mutable-sequence-types
    list: [
        "insert",
        "append",
        "clear",
        "reverse",
        "extend",
        "pop",
        "remove",
        "__iadd__",
        "__imul__",
    ],
    # Gathered from _collections_abc.py:MutableMapping and https://docs.python.org/3/library/stdtypes.html#mapping-types-dict
    dict: ["pop", "popitem", "clear", "update", "setdefault", "__ior__"],
    # Gathered from _collections_abc.py:MutableSet and https://docs.python.org/3/library/stdtypes.html#set-types-set-frozenset
    set: [
        "add",
        "discard",
        "remove",
        "pop",
        "clear",
        "__ior__",
        "__iand__",
        "__ixor__",
        "__isub__",
    ],
}


# Type instances are super expensive in terms of memory
# We cache and reuse our dynamically created types to reduce the memory footprint
# Since we don't want to unnecessarily keep types alive we store weak instead of strong references.
_frozen_type_cache: dict[(type, bool, bool), weakref.ReferenceType[type]] = {}


def _create_frozen_type(obj: object, fr_attr: bool, fr_item: bool) -> type:
    # Check if we already have it cached
    key = (obj if isinstance(obj, FunctionType) else type(obj), fr_attr, fr_item)
    if (frozen_type_ref := _frozen_type_cache.get(key, None)) is not None:
        if frozen_type := frozen_type_ref():  # check if the weakref is still alive
            return frozen_type

    if isinstance(obj, (FunctionType, staticmethod, classmethod)):
        frozen_type = _create_frozen_function_type(obj)
    else:
        frozen_type = _create_dynamic_frozen_type(obj, fr_attr, fr_item)

    # Store newly created type in cache
    _frozen_type_cache[key] = weakref.ref(
        frozen_type, lambda _: _frozen_type_cache.pop(key)
    )

    return frozen_type


def _create_frozen_function_type(function: FunctionType) -> type:
    # Define a new type that we can later put in the functions __class__
    frozen_type_dict = dict(
        # We need to copy the function to avoid endless recursion later
        __original_function__=(cloned_function := _clone_function(function)),
        __repr__=lambda self: f"<Frozen({repr(cloned_function)})>",
        __doc__=function.__doc__,
        __call__=staticmethod(cloned_function),
        __setattr__=_raise_immutable_error,
        __frozen__=True,
    )
    if "self" in signature(function).parameters:
        frozen_type_dict["__get__"] = (
            lambda self, instance, owner: self.__call__
            if instance is None
            else MethodType(self.__call__, instance)
        )
    frozen_type = type(
        f"Frozen{function.__name__}",
        tuple(),
        frozen_type_dict,
    )

    # Carry over anything else in the functions __dict__ that is not special (__dunder__)
    {
        type.__setattr__(frozen_type, k, v)
        for k, v in function.__dict__.items()
        if not k.startswith("__")
    }

    return frozen_type


def _create_dynamic_frozen_type(obj: object, fr_attr: bool, fr_item: bool):
    """
    Dynamically creates a new type that inherits from both the original type ``obj_type`` and :class:`~cryostasis.detail.Frozen`.
    Also, modifies the ``__repr__`` of the created type to reflect that it is frozen.

    Args:
        obj: The original object, whose type will be the second base of the newly created type.
        fr_attr: Bool indicating whether attributes of instances of the new type should be frozen. Is passed to :attr:`~cryostasis.detail.Frozen.__freeze_attributes`.
        fr_item: Bool indicating whether items of instances of the new type should be frozen. Is passed to :attr:`~cryostasis.detail.Frozen.__freeze_items`.
    """

    obj_type = type(obj)

    # Create new type that inherits from Frozen and the original object's type
    frozen_type = type(obj_type)(
        f"Frozen{obj_type.__name__}",
        (Frozen, obj_type),
        {"_Frozen__freeze_attributes": fr_attr, "_Frozen__freeze_items": fr_item}
        | ({"__slots__": []} if hasattr(obj_type, "__slots__") else {}),
    )

    # Add new __repr__ that encloses the original repr in <Frozen()>
    frozen_type.__repr__ = (
        lambda self: "<Frozen("
        + (
            obj_type.__repr__(self)
            .rstrip(
                ")" if obj_type is set else ""
            )  # `set` repr is weird and needs special handling
            .replace("Frozenset(", "")
            .replace(  # `object` repr also needs special fixing
                f"cryostasis.detail.{self.__class__.__qualname__}",
                f"{(base := self.__class__.__bases__[1]).__module__}.{base.__qualname__}",
            )
        )
        + ")>"
    )

    # Deal with mutable methods of builtins
    for container_type, methods in _mutable_methods.items():
        if issubclass(obj_type, container_type):
            for method in methods:
                substitute = wraps(getattr(obj_type, method))(_raise_immutable_error)
                setattr(frozen_type, method, substitute)

    return frozen_type


def _traverse_and_apply(
    obj: Instance, func: Callable[[Instance], Instance]
) -> Instance:
    from itertools import chain
    from cryostasis import deepfreeze_object_blacklist, deepfreeze_type_blacklist

    # set for keeping id's of seen instances
    # we only keep the id's because some instances might not be hashable
    # also we don't want to hold refs to the instances here and weakref is not supported by all types
    seen_instances: set[int] = set()

    def _traverse_and_apply_impl(obj: Instance) -> Instance:
        if id(obj) not in seen_instances:
            seen_instances.add(id(obj))
        else:
            return obj

        if obj in deepfreeze_object_blacklist:
            return obj

        if any(isinstance(obj, t) for t in deepfreeze_type_blacklist):
            return obj

        func(obj)

        # freeze all attributes
        try:
            attr_iterator = vars(obj).values()
        except TypeError:
            pass
        else:
            for attr in attr_iterator:
                _traverse_and_apply_impl(attr)

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
                _traverse_and_apply_impl(item)

        return obj

    return _traverse_and_apply_impl(obj)


#: set of types that are already immutable and hence will be ignored by `freeze`
IMMUTABLE_TYPES = frozenset(
    #  type(int.real) is getset_descriptor i.e. what you get from property
    {
        int,
        float,
        str,
        bytes,
        bool,
        frozenset,
        tuple,
        type(None),
        type(int.real),
        BuiltinFunctionType,
        WrapperDescriptorType,
        MethodWrapperType,
        MethodDescriptorType,
        ClassMethodDescriptorType,
    }
)


def _clone_function(function: FunctionType):
    """Helper that can clone a function by instantiating :class:`types.FunctionType`."""
    clone = FunctionType(
        function.__code__,
        function.__globals__,
        name=f"{function.__name__}_clone",
        argdefs=function.__defaults__,
        closure=function.__closure__,
    )

    clone.__kwdefaults__ = function.__kwdefaults__
    update_wrapper(clone, function, updated=[])
    return clone


def _is_frozen_function(obj: object):
    return hasattr(obj, "__original_function__")


def _exclusions_ioperator(
    self: Exclusions, other: object, operator: callable
) -> NotImplementedType | Exclusions:
    if not isinstance(other, self.__class__):
        return NotImplemented

    for field in self.__dataclass_fields__:
        if field == "NOT_SET":
            continue
        attr = getattr(self, field)
        operator(attr, getattr(other, field))

    return self


def _exclusions_operator(
    self: Exclusions, other: object, operator: callable
) -> NotImplementedType | Exclusions:
    import operator as operator_module

    if not isinstance(other, self.__class__):
        return NotImplemented

    new_exclusions = deepcopy(self)
    operator = getattr(operator_module, f"i{operator.__name__.strip('_')}")
    operator(new_exclusions, other)

    return new_exclusions
