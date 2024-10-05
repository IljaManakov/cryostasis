"""
For descriptors we need a new descriptor that we bind to the dynamically created type.
It should forward the original value on __get__ and disable __set__ and __del__.
The latter two should only be implemented if they also exist on the original descriptor because their existence impacts the attribute lookup order.

Also, __slots__ are actually converted into descriptors.

Also also, assigning to __class__ attr on instances with descriptors will be a pain in the butt.
CPython has a check to make sure that both old and new cls have the same slots which is great...
Problem is that it is never run because new will be already disqualified before that due to not having a common base with old -.-

Below is a draft after a few minutes of brainstorming. It kinda works. #TODO
"""


class FrozenDescriptor:
    def __init__(self, original_inst):
        self.original_inst = original_inst

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, *args):
        return getattr(self.original_inst, self.name)

    def __set__(self, *args):
        print("möööp")

    def __del__(self, *args):
        print("möööp, möööp")


class A:
    __slots__ = ["a", "b"]


a = A()
a.a = 1

class C(A):
    a = FrozenDescriptor(a)

c = C()
assert c.a == 1
c.a = 100  # triggers FrozenDescriptor.__set__
