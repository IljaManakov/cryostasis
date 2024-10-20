# ❄️ cryostasis ❄️ -- Freeze arbitrary Python objects


## Summary

`cryostasis` is a package that allows to turn arbitrary Python objects immutable.
The package is very lightweight and does not have any dependencies.
It offers the `freeze` and `deepfreeze` functions.
When an object is frozen any modification to its attributes or items (i.e. assignment or deletion using the []-operator) will raise an `ImmutableError`.
All existing attributes, methods and items will still be accessible on the frozen instance though.

You can think of using `cryostasis.freeze` as a more thorough variant of `dataclass(frozen=True)`:
- unlike the `dataclass` decorator, `freeze` can also be used on instances of builtin types such as lists or dictionaries
- also unlike the `dataclass`decorator, `deepfreeze` will freeze the instance and all of its attributes and items recursively

Frozen instances can be reverted back to their original state using the `thaw` and `deepthaw` functions.

## Use Cases

As I already alluded to, you can use `freeze` / `deepfreeze` wherever you would have used a frozen dataclass but want to be a bit more thorough.
More generally, `cryostasis` can be used in any scenario in which a central mutable instance is passed around to multiple sites.
This could be, for example, a configuration-driven application, where you want to make sure that no site accidentally modifies the central configuration from their local scope.

## Examples

`freeze` works by freezing an object in-place. For convenience, `freeze` also return a reference to the object.
Attributes and items remain accessible but any modifications to them will raise an `cryostasis.ImmutableError`.
On builtin, mutable types (e.g. `list`) the methods that modify the internal state of the instance also raise the same exception.

```python
from cryostasis import freeze

class Dummy:
    def __init__(self, value):
        self.value = value

d = Dummy(value=5)
d.value = 42        # ok
freeze(d)
d.value = 9001      # raises ImmutableError
del d.value         # raises ImmutableError

l = freeze([1,2,3])
l[0]                #  ok -- returns 1
l[0] = 5            #  raises ImmutableError
del l[0]            #  raises ImmutableError
l.append(42)        #  raises ImmutableError
```

`deepfreeze` works the same way (it calls `freeze` internally) except that is recurses through the instances attributes and items, freezing all of them while traversing.

```python
from cryostasis import deepfreeze

class Dummy:
    def __init__(self, value):
        self.value = value
        self.a_dict = dict(a=1, b=2, c=[])

d = Dummy(value=[1,2,3])
deepfreeze(d)
d.value                     # ok -- returns <Frozen([1,2,3])>
d.value = 9001              # raises ImmutableError
del d.value                 # raises ImmutableError
d.value[0]                  # ok -- returns 1
d.value[0] = 42             # raises ImmutableError
del d.value[0]              # raises ImmutableError
d.a_dict['c']               # ok -- returns <Frozen([])>
d.a_dict['c'].append(0)     # raises ImmutableError
```

## Report Issues

This project lives on [GitHub](https://github.com/IljaManakov/cryostasis).
If you encounter any issues or have feature requests, please open an issue using the project's [Issues](https://github.com/IljaManakov/cryostasis/issues) tab.
