class ImmutableError(Exception):
    pass


class Frozen:
    __freeze_attribute_assignment = True
    __freeze_item_assignment = True

    def __setattr__(self, name, value):
        if self.__freeze_attribute_assignment:
            raise ImmutableError("This object is immutable")
        else:
            return super().__setattr__(name, value)

    def __setitem__(self, name, value):
        if self.__freeze_item_assignment:
            raise ImmutableError("This object is immutable")
        else:
            return super().__setattr__(name, value)


def freeze(obj: object, *, freeze_attribute_assignment=True, freeze_item_assignment=True, recursive=True):
    obj_type = obj.__class__
    frozen_type = type(f"Frozen{obj_type.__name__}",
                       (Frozen, obj_type),
                       {"_Frozen__freeze_attribute_assignment": freeze_attribute_assignment,
                        "_Frozen__freeze_item_assignment": freeze_item_assignment})
    frozen_type.__repr__ = lambda self: f"<Frozen({obj_type.__repr__(self)})>"

    obj.__class__ = frozen_type
    return obj
