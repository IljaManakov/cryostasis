class ImmutableError(Exception):
    pass


class Frozen:

    def __instancecheck__(cls, instance):
        print("In Frozen")
        return cls.__instancecheck__(instance) or instance.__bases__[1].__instancecheck__(instance)

    def __setattr__(self, name, value):
        raise ImmutableError("This object is immutable")


def freeze(obj: object):
    obj_type = obj.__class__
    frozen_type = type(f"Frozen{obj_type.__name__}", (Frozen, obj_type), dict(obj_type.__dict__))
    frozen_type.__repr__ = lambda self: f"<Frozen({obj_type.__repr__(self)})>"

    obj.__class__ = frozen_type
    return obj
