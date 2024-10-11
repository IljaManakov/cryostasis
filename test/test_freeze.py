import gc
from copy import deepcopy
from inspect import signature

import pytest
from cryostasis import freeze, ImmutableError


@pytest.fixture(scope="module")
def dummy_class():
    """Fixture that provides a simple dummy class with a value and repr."""

    class Dummy:
        def __init__(self, value):
            self.value = value
            self._list = [1, 2, 3]

        def __repr__(self):
            return f"Dummy('value={self.value}')"

        def __getitem__(self, item):
            return self._list[item]

        def __setitem__(self, key, value):
            self._list[key] = value

    return Dummy


def test_freeze(dummy_class):
    """
    Tests the following aspects of :func:`cryo.freeze`:
        - Returns a reference to the frozen object.
        - The original object and the one returned are the same
        - The repr of the frozen object is correctly modified to indicate that the instance is frozen
        - Instance checks with the original class still work on the frozen object
    """

    dummy = dummy_class("hello")
    dummy_clone = deepcopy(dummy)
    dummy_frozen_ref = freeze(dummy)
    assert dummy_frozen_ref is dummy
    dummy_repr = repr(dummy).strip("\"'")
    assert dummy_repr != repr(dummy_clone)
    assert dummy_repr.startswith("<Frozen(")
    assert dummy_repr.endswith(")>")
    assert repr(dummy_clone).strip("\"'") == dummy_repr.removeprefix(
        "<Frozen("
    ).removesuffix(")>")

    assert isinstance(dummy, dummy_class)
    assert issubclass(dummy.__class__, dummy_class)


def test_freeze_attribute_assignment(dummy_class):
    dummy = dummy_class("hello")
    freeze(dummy)
    with pytest.raises(ImmutableError):
        dummy.value = "world"
    assert dummy.value == "hello"


def test_freeze_item_assignment(dummy_class):
    dummy = dummy_class("Hi")
    assert dummy[0] == 1
    dummy[0] = 9001
    assert dummy[0] == 9001

    freeze(dummy)
    with pytest.raises(ImmutableError):
        dummy[0] = 1
    assert dummy[0] == 9001


def test_freeze_item_assignment_list():
    a_list = [1, 2, 3]
    freeze(a_list)
    with pytest.raises(ImmutableError):
        a_list[0] = 5
    with pytest.raises(ImmutableError):
        a_list.bla = 1
    assert a_list == [1, 2, 3]


def test_freeze_item_assignment_dict():
    a_dict = dict(a=1, b=2, c=3)
    freeze(a_dict)
    with pytest.raises(ImmutableError):
        a_dict["a"] = 5
    with pytest.raises(ImmutableError):
        a_dict.bla = 1
    assert a_dict == dict(a=1, b=2, c=3)


def test_freeze_item_assignment_set():
    a_set = {1, 2, 3}
    freeze(a_set)
    with pytest.raises(ImmutableError):
        a_set.add(5)
    with pytest.raises(ImmutableError):
        a_set.bla = 1
    assert a_set == {1, 2, 3}


@pytest.mark.parametrize(
    "method",
    [
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
)
def test_freeze_list_mutable_methods(method):
    a_list = [1, 2, 3]
    freeze(a_list)
    method = getattr(a_list, method)
    args = {
        n: None
        for n, p in signature(method).parameters.items()
        if n != "self" and p.kind.value != 4
    }
    with pytest.raises(ImmutableError):
        method(*args.values())
    assert a_list == [1, 2, 3]


@pytest.mark.parametrize(
    "method",
    [
        "pop",
        "popitem",
        "clear",
        "update",
        "setdefault",
        "__ior__",
    ],
)
def test_freeze_dict_mutable_methods(method):
    a_dict = dict(a=1, b=2, c=3)
    freeze(a_dict)
    method = getattr(a_dict, method)
    args = {
        n: None
        for n, p in signature(method).parameters.items()
        if n != "self" and p.kind.value != 4
    }
    with pytest.raises(ImmutableError):
        method(*args.values())
    assert a_dict == dict(a=1, b=2, c=3)


@pytest.mark.parametrize(
    "method",
    [
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
)
def test_freeze_set_mutable_methods(method):
    a_set = {1, 2, 3}
    freeze(a_set)
    method = getattr(a_set, method)
    args = {
        n: None
        for n, p in signature(method).parameters.items()
        if n != "self" and p.kind.value != 4
    }
    with pytest.raises(ImmutableError):
        method(*args.values())
    assert a_set == {1, 2, 3}


def test_gc_compatibility():
    l1 = []
    l2 = [l1]
    l1.append(l2)
    freeze(l1)
    freeze(l2)

    gc.collect()
    del l1, l2
    assert gc.collect() == 2
