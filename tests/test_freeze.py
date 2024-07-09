import gc
from copy import deepcopy
from inspect import signature

import pytest
from cryo import freeze, ImmutableError


@pytest.fixture(scope='module')
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

    d = dummy_class('hello')
    d2 = deepcopy(d)
    frozen_d = freeze(d)
    assert frozen_d is d
    d_repr = repr(d).strip("\"\'")
    assert d_repr != repr(d2)
    assert d_repr.startswith('<Frozen(')
    assert d_repr.endswith(')>')
    assert repr(d2).strip("\"\'") == d_repr.removeprefix("<Frozen(").removesuffix(")>")

    assert isinstance(d, dummy_class)
    assert issubclass(d.__class__, dummy_class)


def test_freeze_attribute_assignment(dummy_class):

    d = dummy_class('hello')
    freeze(d)
    with pytest.raises(ImmutableError):
        d.value = 'world'
    assert d.value == "hello"


def test_freeze_item_assignment(dummy_class):
    d = dummy_class("Hi")
    assert d[0] == 1
    d[0] = 9001
    assert d[0] == 9001

    freeze(d)
    with pytest.raises(ImmutableError):
        d[0] = 1
    assert d[0] == 9001

def test_freeze_item_assignment_list():

    l = [1,2,3]
    freeze(l)
    with pytest.raises(ImmutableError):
        l[0] = 5
    with pytest.raises(ImmutableError):
        l.bla = 1
    assert l == [1,2,3]

def test_freeze_item_assignment_dict():

    d = dict(a=1, b=2, c=3)
    freeze(d)
    with pytest.raises(ImmutableError):
        d['a'] = 5
    with pytest.raises(ImmutableError):
        d.bla = 1
    assert d == dict(a=1, b=2, c=3)

def test_freeze_item_assignment_set():

    s = {1, 2, 3}
    freeze(s)
    with pytest.raises(ImmutableError):
        s.add(5)
    with pytest.raises(ImmutableError):
        s.bla = 1
    assert s == {1, 2, 3}

@pytest.mark.parametrize("method", [
    "insert",
    "append",
    "clear",
    "reverse",
    "extend",
    "pop",
    "remove",
    "__iadd__",
    "__imul__",
])
def test_freeze_list_mutable_methods(method):
    l = [1, 2, 3]
    freeze(l)
    method = getattr(l, method)
    args = {n: None for n, p in signature(method).parameters.items() if n != 'self' and p.kind.value != 4}
    with pytest.raises(ImmutableError):
        method(*args.values())
    assert l == [1, 2, 3]

@pytest.mark.parametrize("method", [
    "pop",
    "popitem",
    "clear",
    "update",
    "setdefault",
    "__ior__",
])
def test_freeze_dict_mutable_methods(method):
    d = dict(a=1, b=2, c=3)
    freeze(d)
    method = getattr(d, method)
    args = {n: None for n, p in signature(method).parameters.items() if n != 'self' and p.kind.value != 4}
    with pytest.raises(ImmutableError):
        method(*args.values())
    assert d == dict(a=1, b=2, c=3)

@pytest.mark.parametrize("method", [
    "add",
    "discard",
    "remove",
    "pop",
    "clear",
    "__ior__",
    "__iand__",
    "__ixor__",
    "__isub__",
])
def test_freeze_set_mutable_methods(method):
    s = {1, 2, 3}
    freeze(s)
    method = getattr(s, method)
    args = {n: None for n, p in signature(method).parameters.items() if n != 'self' and p.kind.value != 4}
    with pytest.raises(ImmutableError):
        method(*args.values())
    assert s == {1, 2, 3}

def test_gc_compatibility():
    l1 = []
    l2 = [l1]
    l1.append(l2)
    freeze(l1)
    freeze(l2)

    gc.collect()
    del l1, l2
    assert gc.collect() == 2
