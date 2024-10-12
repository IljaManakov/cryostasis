def _raise_immutable_error():
    from . import ImmutableError

    raise ImmutableError("This object is immutable")


class Frozen:
    __freeze_attributes = True
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


def _create_dynamic_frozen_type(obj_type: type, fr_attr: bool, fr_item: bool):
    # Create new type that inherits from Frozen and the original object's type
    frozen_type = type(
        f"Frozen{obj_type.__name__}",
        (Frozen, obj_type),
        {"_Frozen__freeze_attributes": fr_attr, "_Frozen__freeze_items": fr_item},
    )

    # Add new __repr__ that encloses the original repr in <Frozen()>
    frozen_type.__repr__ = lambda self: f"<Frozen({obj_type.__repr__(self)})>"

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

    return frozen_type


IMMUTABLE_TYPES = {int, str, bytes, bool, frozenset, tuple}
