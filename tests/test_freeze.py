from copy import deepcopy

import pytest

from cryo import freeze, ImmutableError


def test_freeze():


    class Dummy:

        def __init__(self, value):
            self.value = value

        def __repr__(self):
            return f"Dummy('value={self.value}')"

    d = Dummy('hello')
    d2 = deepcopy(d)
    frozen_d = freeze(d)
    assert frozen_d is d
    with pytest.raises(ImmutableError):
        d.value = 'world'
    assert d.value == "hello"
    d_repr = repr(d).strip("\"\'")
    assert d_repr.startswith('<Frozen(')
    assert d_repr.endswith(')>')
    assert repr(d2).strip("\"\'") == d_repr.removeprefix("<Frozen(").removesuffix(")>")

    pytest.xfail("Instance checks do not work yet")
    assert isinstance(d, Dummy)
