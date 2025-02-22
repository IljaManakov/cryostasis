import contextlib
import enum
import gc
import operator
import re
import types
from copy import deepcopy
from enum import EnumMeta

import pytest
from cryostasis import freeze, ImmutableError, deepfreeze, thaw, is_frozen, deepthaw, Exclusions


@pytest.fixture(scope="module")
def dummy_class():
    """Fixture that provides a simple dummy class with a value and repr."""
    class Color(enum.Enum):
        RED = 1
        GREEN = 2
        BLUE = 3

    class Dummy:
        def __init__(self, value):
            self.value = value
            self._list = [1, 2, 3]
            self.color = Color.RED

        def __repr__(self):
            return f"Dummy(value={self.value})"

        def __getitem__(self, item):
            return self._list[item]

        def __setitem__(self, key, value):
            self._list[key] = value

        def __delitem__(self, key):
            del self._list[key]

        def my_method(self):
            pass

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
    with pytest.raises(ImmutableError):
        method()
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
    with pytest.raises(ImmutableError):
        method()
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
    with pytest.raises(ImmutableError):
        method()
    assert a_set == {1, 2, 3}


def test_thaw():
    a_list = [1, 2, 3]
    cycled_list = thaw(freeze(a_list))
    assert cycled_list is a_list
    assert not is_frozen(cycled_list)
    a_list[0] = 5
    a_list.append(9001)
    assert a_list == [5, 2, 3, 9001]
    assert thaw(a_list) is a_list



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
    ( 1, True, "hello", b"hello", tuple(), frozenset(), freeze([1,2,3]), None)]
)
def test_freeze_immutable(instance):
    """Tests that `freeze` does not modify instances of already immutable types."""
    repr_before = repr(instance)
    class_before = instance.__class__
    frozen_instance = freeze(instance)
    assert repr(frozen_instance) == repr_before
    assert frozen_instance.__class__ == class_before


def test_freeze_classdecorator():
    @freeze
    class A:
        MY_CONSTANT = 1
        def __getitem__(self, item):
            return self.MY_CONSTANT

    assert is_frozen(A)

    with pytest.raises(ImmutableError):
        A.MY_CONSTANT = 9001

    with pytest.raises(ImmutableError):
        A.new_method = lambda self: print("Nice!")


def test_deepfreeze_deepthaw(dummy_class):
    """Tests that `deepfreeze` recursively freezes and `deepthaw` recursively unfreezes all attributes and items."""

    modified_instance = dummy_class("hello")
    modified_instance.a_list = [1,2,3]
    modified_instance.a_dict = {"a": 1, "b": 2}
    obj = {
        "a": {1, 2, 3},
        "b": [True, modified_instance],
        "c": dummy_class("world"),
        "d": dummy_class,
        "f": dummy_class.__dict__,
        "g": types.SimpleNamespace(),
    }
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

    deepthaw(obj)

    obj['d'] = 5
    obj["a"].add(5)
    obj["b"][-1].a_list.append(5)
    obj["b"][-1].a_dict['c'] = 5
    obj["b"][-1].bla = 5
    obj["b"].append(5)
    obj["c"].bla = 5


def test_deepfreeze_infinite_recursion():
    """Tests that `deepfreeze` does not recurse infinitely on reference cycles."""
    l1 = []
    l2 = [l1]
    l1.append(l2)
    deepfreeze(l1)


def test_freeze_memory_consumption():
    """Tests the caching of dynamically created types during `freeze`"""
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


def test_freeze_descriptors():
    """Tests that `freeze` also works with descriptors"""

    class Descriptor:

        def __init__(self):
            self.val = None

        def __get__(self, instance, owner):
            return self.val

        def __set__(self, instance, value):
            self.val = value

        def __delete__(self, instance):
            raise RuntimeError("You shall not delete me!")

    class DummyWithDescriptor:

        descriptor = Descriptor()

    dummy = DummyWithDescriptor()
    dummy.descriptor = 1
    freeze(dummy)
    with pytest.raises(ImmutableError):
        del dummy.descriptor
    with pytest.raises(ImmutableError):
        dummy.descriptor = 42


def test_freeze_with_slots():
    """Tests that `freeze` also works if the current type has __slots__"""

    class DummyWithSlots:
        __slots__ = ["val"]

    d = DummyWithSlots()
    d.val = 1
    assert d.val == 1

    freeze(d)
    with pytest.raises(ImmutableError):
        d.val = 42
    assert d.val == 1


def test_freeze_enums():
    """This only tests that ``freeze`` does not fail on enums. Enums are not actually being frozen"""
    class TestEnum(enum.Enum):
        RED = "red"
        BLUE = "blue"
        GREEN = "green"

    TestEnum.flag = True
    TestEnum.RED.rgb = (255, 0, 0)
    with pytest.warns(RuntimeWarning, match= "Skipping"):
        freeze(TestEnum.RED)
    with pytest.warns(RuntimeWarning, match= "Skipping"):
        freeze(TestEnum)


def test_freeze_function():
    def func():
        return True

    func.bla = 10
    assert func.bla == 10

    ffunc = freeze(func)
    assert ffunc is func
    assert is_frozen(func)

    with pytest.raises(ImmutableError):
        func.bla = 11
    assert func.bla == 10

    with pytest.raises(ImmutableError):
        func.new_attr = 10
    assert not hasattr(func, "new_attr")

    thaw(func)
    assert not is_frozen(func)
    func.bla = 11
    assert func.bla == 11


def test_freeze_class():
    class TestClass:
        over = 9000

        def method(self):
            return "method"

        @staticmethod
        def staticmethod():
            return "staticmethod"

    freeze(TestClass)
    with pytest.raises(ImmutableError):
        TestClass.new_attr = 10
    with pytest.raises(ImmutableError):
        TestClass.over = 10
    assert TestClass.over == 9000

    instance = TestClass()
    assert instance is not None
    instance.over = 10
    assert TestClass.over == 9000
    instance.new_attr = 10
    assert instance.new_attr == 10

    thaw(TestClass)
    TestClass.over = 9001
    assert TestClass.over == 9001


@pytest.mark.parametrize(
    ["instance", "expected"],
    [pytest.param(inst, exp, id=inst.__class__.__name__) for inst, exp in
        [
            ([1, 2, 3], "<Frozen([1, 2, 3])>"),
            (dict(a=1, b=2, c=3), "<Frozen({'a': 1, 'b': 2, 'c': 3})>"),
            ({1,2,3}, "<Frozen({1, 2, 3})>"),
            (dummy_class.__pytest_wrapped__.obj()(5), "<Frozen(Dummy(value=5))>"),
            (dummy_class.__pytest_wrapped__.obj(), "<Frozen(<class 'test_freeze.dummy_class.<locals>.Dummy'>)>"),
            (lambda: None, "<Frozen(<function <lambda> at ...>)>"),
            (type("ClassWithoutRepr",tuple(), {})(), "<Frozen(<test_freeze.ClassWithoutRepr object at ...>)>"),
        ]
    ]
)
def test_freeze_repr(instance, expected):

    repr_string = repr(freeze(instance))
    expected = re.escape(expected).replace(re.escape("..."), ".*")
    thaw(instance)
    assert re.match(expected, repr_string)


def test_frozen_not_constructible():
    from cryostasis.detail import Frozen
    with pytest.raises(NotImplementedError):
        Frozen()


@pytest.mark.parametrize(
    ["exclusions", "contains", "expected"],
    [pytest.param(exc, cont, exp, id=f"{cont} in {exc} is {exp}") for exc, cont, exp in (
        # positives
        (dict(attrs=["a", "b"]), dict(attr="b"), True),
        (dict(items=["a", 1]), dict(item=1), True),
        (dict(items=["a", 1]), dict(item="a"), True),
        (dict(bases=[int, type]), dict(subclass=EnumMeta), True),
        (dict(types=[str, int]), dict(instance=1), True),
        (dict(objects=[object(), dummy_class]), dict(object=dummy_class), True),

        # matched negatives
        (dict(attrs=["a", "b"]), dict(attr="c"), False),
        (dict(items=["a", 1]), dict(item="c"), False),
        (dict(items=["a", 1]), dict(item=3), False),
        (dict(bases=[int, type]), dict(subclass=float), False),
        (dict(types=[str, int]), dict(instance=1.), False),
        (dict(objects=[object(), dummy_class]), dict(object=object()), False),

        # mismatched negatives
        (dict(items=["a", 1]), dict(attr="b"), False),
        (dict(types=[str, int]), dict(item=1), False),
        (dict(attrs=["a", "b"]), dict(item="a"), False),
        (dict(objects=[object(), EnumMeta]), dict(subclass=EnumMeta), False),
        (dict(items=["a", 1]), dict(instance=1), False),
        (dict(bases=[int, type]), dict(object=type), False),
    )]
)
def test_exclusions_call(exclusions, contains, expected):
    assert Exclusions(**exclusions)(**contains) is expected


@pytest.mark.parametrize(
    ["contains", "match"],
    [pytest.param(contains, match, id=f"{contains=}, {match=}") for contains, match in (
        (dict(), "at least one"),
        (dict(attr=1), "not a valid"),
        (dict(item=1.), "not a valid"),
        (dict(subclass="Hi"), "not a valid"),
    )]
)
def test_exclusions_raises(contains, match):
    with pytest.raises(ValueError, match=match):
        Exclusions()(**contains)


@pytest.mark.parametrize(
    ["left", "right"],
    [(Exclusions(attrs={"a", "b"}, items={1, 2}, types={object, Exclusions}, bases={int, float}, objects={1., 2.}),
    Exclusions(attrs={"b", "c"}, items={2, 3}, types={Exclusions, type}, bases={float, str}, objects={2., 3.}))]
)
@pytest.mark.parametrize(
    ["operator", "expected"],
    [pytest.param(op, exp, id=op.__name__) for op, exp in (
        (operator.sub, Exclusions(attrs={"a"}, items={1}, types={object}, bases={int}, objects={1.})),
        (operator.and_, Exclusions(attrs={"b"}, items={2}, types={Exclusions}, bases={float}, objects={2.})),
        (operator.or_, Exclusions(attrs={"a", "b", "c"}, items={1, 2, 3}, types={object, Exclusions, type}, bases={int, float, str}, objects={1., 2., 3.}))
    )]
)
def test_exclusions_arithmetic(left, right, operator, expected):
    assert operator(left, right) == expected
