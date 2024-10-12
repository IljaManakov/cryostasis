import contextlib
import gc
from copy import deepcopy
from inspect import signature

import pytest
from cryostasis import freeze, ImmutableError, deepfreeze


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

        def __delitem__(self, key):
            del self._list[key]

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


@pytest.mark.parametrize(
    ["freeze_attributes", "context"],
    [pytest.param(freeze_attributes, context, id=f"{freeze_attributes=}")
     for freeze_attributes, context in
     zip((True, False), (pytest.raises(ImmutableError), contextlib.nullcontext()))])
def test_freeze_attribute_assignment(dummy_class, freeze_attributes, context):
    dummy = dummy_class("hello")
    freeze(dummy, freeze_attributes=freeze_attributes)
    with context:
        dummy.value = "world"
    assert dummy.value == ("hello" if freeze_attributes else "world")

@pytest.mark.parametrize(
    ["freeze_attributes", "context"],
    [pytest.param(freeze_attributes, context, id=f"{freeze_attributes=}")
     for freeze_attributes, context in
     zip((True, False), (pytest.raises(ImmutableError), contextlib.nullcontext()))])
def test_freeze_attribute_deletion(dummy_class, freeze_attributes, context):
    dummy = dummy_class("hello")
    freeze(dummy, freeze_attributes=freeze_attributes)
    with context:
        del dummy.value
    assert getattr(dummy, "value", None) == ("hello" if freeze_attributes else None)

@pytest.mark.parametrize(
    ["freeze_items", "context"],
    [pytest.param(freeze_items, context, id=f"{freeze_items=}")
     for freeze_items, context in
     zip((True, False), (pytest.raises(ImmutableError), contextlib.nullcontext()))])
def test_freeze_item_assignment(dummy_class, freeze_items, context):
    dummy = dummy_class("Hi")
    assert dummy[0] == 1
    dummy[0] = 9001
    assert dummy[0] == 9001

    freeze(dummy, freeze_items=freeze_items)
    with context:
        dummy[0] = 1
    assert dummy[0] == (9001 if freeze_items else 1)

@pytest.mark.parametrize(
    ["freeze_items", "context"],
    [pytest.param(freeze_items, context, id=f"{freeze_items=}")
     for freeze_items, context in
     zip((True, False), (pytest.raises(ImmutableError), contextlib.nullcontext()))])
def test_freeze_item_deletion(dummy_class, freeze_items, context):
    dummy = dummy_class("Hi")
    assert dummy[0] == 1
    assert dummy[1] == 2
    dummy[0] = 9001
    assert dummy[0] == 9001

    freeze(dummy, freeze_items=freeze_items)
    with context:
        del dummy[0]
    assert dummy[0] == (9001 if freeze_items else 2)


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
    """Tests that gc collection of frozen builtins does not error / crash."""
    l1 = []
    l2 = [l1]
    l1.append(l2)
    freeze(l1)
    freeze(l2)

    gc.collect()
    del l1, l2
    assert gc.collect() == 2


@pytest.mark.parametrize(
    "instance",
    [pytest.param(inst, id=inst.__class__.__name__) for inst in
    ( 1, True, "hello", b"hello", tuple(), frozenset(), freeze([1,2,3]))]
)
def test_freeze_immutable(instance):
    """Tests that `freeze` does not modify instances of already immutable types."""
    repr_before = repr(instance)
    class_before = instance.__class__
    frozen_instance = freeze(instance)
    assert repr(frozen_instance) == repr_before
    assert frozen_instance.__class__ == class_before


def test_deepfreeze(dummy_class):
    """Tests that `deepfreeze` recursively freezes all attributes and items."""

    modified_instance = dummy_class("hello")
    modified_instance.a_list = [1,2,3]
    modified_instance.a_dict = {"a": 1, "b": 2}
    obj = {"a": {1, 2, 3}, "b": [True, modified_instance], "c": dummy_class("world")}
    deepfreeze(obj)

    with pytest.raises(ImmutableError):
        obj['d'] = 5
    with pytest.raises(ImmutableError):
        obj["a"].add(5)
    with pytest.raises(ImmutableError):
        obj["b"].append(5)
    with pytest.raises(ImmutableError):
        obj["b"][-1].a_list.append(5)
    with pytest.raises(ImmutableError):
        obj["b"][-1].a_dict['c'] = 5
    with pytest.raises(ImmutableError):
        obj["b"][-1].bla = 5
    with pytest.raises(ImmutableError):
        obj["c"].bla = 5

def test_deepfreeze_infinite_recursion():
    """Tests that `deepfreeze` does not recurse infinitely on reference cycles."""
    l1 = []
    l2 = [l1]
    l1.append(l2)
    deepfreeze(l1)


def test_freeze_memory_consumption():
    import psutil, os

    lists = [[] for _ in range(10_000)]
    process = psutil.Process(os.getpid())
    baseline = int(process.memory_full_info().uss / 1024**2)  # baseline process memory in MB
    for l in lists:
        freeze(l)

    # Size of type is on the order of ~ 0.5 kB
    # Since we freeze 10k instances, if the cache is not working, we would allocate much more than 1 MB
    # We keep the 1MB threshold due to other fluctuations in the processes memory
    assert abs(int(process.memory_full_info().uss / 1024**2) - baseline) <= 1
