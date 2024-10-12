import weakref


def _raise_immutable_error():
    """Small helper for raising ImmutableError (since you cannot raise in a lambda directly."""
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
        f"Frozen{obj_type.__name__}" if obj_type is not set else "",
        (Frozen, obj_type),
        {"_Frozen__freeze_attributes": fr_attr, "_Frozen__freeze_items": fr_item},
    )

    # Add new __repr__ that encloses the original repr in <Frozen()>
    frozen_type.__repr__ = (
        lambda self: f"<Frozen({obj_type.__repr__(self).strip('()' if obj_type is set else '')})>"
    )

    # Deal with mutable methods of lists
    # Gathered from _collections_abc.py:MutableSequence and https://docs.python.org/3/library/stdtypes.html#mutable-sequence-types
    if issubclass(obj_type, list):
        frozen_type.insert = lambda self, i, x: _raise_immutable_error()
        frozen_type.append = lambda self, x: _raise_immutable_error()
        frozen_type.clear = lambda self, x: _raise_immutable_error()
        frozen_type.reverse = lambda self: _raise_immutable_error()
        frozen_type.extend = lambda self, x: _raise_immutable_error()
        frozen_type.pop = lambda self, x=None: _raise_immutable_error()
        frozen_type.remove = lambda self, x: _raise_immutable_error()
        frozen_type.__iadd__ = lambda self, x: _raise_immutable_error()
        frozen_type.__imul__ = lambda self, x: _raise_immutable_error()

    # Deal with mutable methods of dict
    # Gathered from _collections_abc.py:MutableMapping and https://docs.python.org/3/library/stdtypes.html#mapping-types-dict
    if issubclass(obj_type, dict):
        frozen_type.pop = lambda self, key, default=None: _raise_immutable_error()
        frozen_type.popitem = lambda self: _raise_immutable_error()
        frozen_type.clear = lambda self: _raise_immutable_error()
        frozen_type.update = lambda self, other=(), **kwds: _raise_immutable_error()
        frozen_type.setdefault = (
            lambda self, key, default=None: _raise_immutable_error()
        )
        frozen_type.__ior__ = lambda self, it: _raise_immutable_error()

    # Deal with mutable methods of dict
    # Gathered from _collections_abc.py:MutableSet and https://docs.python.org/3/library/stdtypes.html#set-types-set-frozenset
    if issubclass(obj_type, set):
        frozen_type.add = lambda self, value: _raise_immutable_error()
        frozen_type.discard = lambda self, value: _raise_immutable_error()
        frozen_type.remove = lambda self, value: _raise_immutable_error()
        frozen_type.pop = lambda self: _raise_immutable_error()
        frozen_type.clear = lambda self: _raise_immutable_error()
        frozen_type.__ior__ = lambda self, it: _raise_immutable_error()
        frozen_type.__iand__ = lambda self, it: _raise_immutable_error()
        frozen_type.__ixor__ = lambda self, it: _raise_immutable_error()
        frozen_type.__isub__ = lambda self, it: _raise_immutable_error()

    # Store newly created type in cache
    _frozen_type_cache[key] = weakref.ref(
        frozen_type, lambda _: _frozen_type_cache.pop(key)
    )

    return frozen_type


#: set of types that are already immutable and hence will be ignored by `freeze`
IMMUTABLE_TYPES = frozenset({int, str, bytes, bool, frozenset, tuple})
