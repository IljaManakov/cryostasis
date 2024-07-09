from copy import deepcopy

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

@pytest.mark.xfail(reason="freezing builtins does not work")
def test_freeze_item_assignment_builtins():

    l = [1,2,3]
    freeze(l)
    with pytest.raises(ImmutableError):
        l[0] = 5
    assert l[0] == 1
