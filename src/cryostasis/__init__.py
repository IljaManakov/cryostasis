__all__ = ["ImmutableError", "freeze"]


class ImmutableError(Exception):
    pass


def freeze(obj: object, *, freeze_attributes=True, freeze_items=True):
    from .detail import _create_dynamic_frozen_type, IMMUTABLE_TYPES, Frozen
    from ._builtin_helpers import _set_class_on_builtin

    if obj.__class__ in IMMUTABLE_TYPES or obj.__class__.__bases__[0] is Frozen:
        return obj

    obj_type = obj.__class__
    frozen_type = _create_dynamic_frozen_type(obj_type, freeze_attributes, freeze_items)
    if isinstance(obj, (list, set, dict)):
        _set_class_on_builtin(obj, frozen_type)
    else:
        obj.__class__ = frozen_type
    return obj
