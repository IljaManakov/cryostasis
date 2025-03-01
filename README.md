# ❄️ cryostasis ❄️ -- Freeze arbitrary Python objects


## Summary

`cryostasis` is a package that allows to turn arbitrary Python objects immutable.
The package is very lightweight and does not have any dependencies.
It offers the `freeze` and `deepfreeze` functions to freeze an object in-place.
When an object is frozen any modification to its attributes or items (i.e. assignment or deletion using the []-operator) will raise an `ImmutableError`.
All existing attributes, methods and items will still be accessible on the frozen instance though.
Since `freeze` acts in-place rather than applying a wrapper, the freezing affects all sites that hold references to the instance.
This ensures that the instance cannot be modified by some part of the codebase that just happened to get a reference earlier.
Frozen instances can be reverted back to their original state using the `thaw` and `deepthaw` functions.

## Use Cases

### Protecting central / global structures from accidental modification
You can use`cryostasis` in any scenario in which a central mutable instance is passed around to multiple sites, which should only have "read-only" access to its data.
This could be, for example, a configuration-driven application, where an initial configuration is loaded and then passed to different functions.
Another example would be the processing of large JSON responses that are passed to multiple functions.

### Truly frozen dataclasses
You can use `freeze` / `deepfreeze` wherever you would have used a `dataclass(frozen=True)` but want to be a bit more thorough:
- unlike the `dataclass` decorator, `freeze` can also be used on instances of builtin types such as lists or dictionaries
- also unlike the `dataclass`decorator, `deepfreeze` will freeze the instance and all of its attributes and items recursively

The freezing can be automated by adding `freeze(self)` / `deepfreeze(self)` in the dataclass' `__post_init__`.
An additional benefit of this approach over `frozen=True` is that the instance is not yet frozen in the context of `__post_init__`.
This eliminates the hassle of dealing with argument conversion on frozen dataclass instances.

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

## Documentation

The documentation of `cryostasis` is hosted on [readthedocs](https://cryostasis.readthedocs.io/en/stable/).

## Report Issues

This project lives on [GitHub](https://github.com/IljaManakov/cryostasis).
If you encounter any issues or have feature requests, please open an issue using the project's [Issues](https://github.com/IljaManakov/cryostasis/issues) tab.
