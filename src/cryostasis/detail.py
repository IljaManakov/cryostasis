import weakref
from functools import wraps


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

    #: If True, setting or deleting attributes will raise ImmutableError
    __freeze_attributes = True

    #: If True, setting or deleting items (i.e. through []-operator) will raise ImmutableError
    __freeze_items = True

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


def _create_dynamic_frozen_type(obj_type: type, fr_attr: bool, fr_item: bool):
    """
    Dynamically creates a new type that inherits from both the original type ``obj_type`` and :class:`~cryostasis.detail.Frozen`.
    Also, modifies the ``__repr__`` of the created type to reflect that it is frozen.

    Args:
        obj_type: The original type, which will be the second base of the newly created type.
        fr_attr: Bool indicating whether attributes of instances of the new type should be frozen. Is passed to :attr:`~cryostasis.detail.Frozen.__freeze_attributes`.
        fr_item: Bool indicating whether items of instances of the new type should be frozen. Is passed to :attr:`~cryostasis.detail.Frozen.__freeze_items`.
    """

    # Check if we already have it cached
    key = (obj_type, fr_attr, fr_item)
    if (frozen_type_ref := _frozen_type_cache.get(key, None)) is not None:
        if frozen_type := frozen_type_ref():  # check if the weakref is still alive
            return frozen_type

    # Create new type that inherits from Frozen and the original object's type
    frozen_type = type(
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

    # Store newly created type in cache
    _frozen_type_cache[key] = weakref.ref(
        frozen_type, lambda _: _frozen_type_cache.pop(key)
    )

    return frozen_type


#: set of types that are already immutable and hence will be ignored by `freeze`
IMMUTABLE_TYPES = frozenset({int, str, bytes, bool, frozenset, tuple})
