# Complete selected CPython 3.14 test_typing methods at 18ef0f0cb52.
import unittest
import typing, types, annotationlib, sys, itertools, operator, re
from functools import reduce
from typing import (Annotated, ClassVar, Final, Required, NotRequired, ReadOnly, Literal,
                    Self, Never, LiteralString, TypeAlias, TypeGuard, TypeIs, Optional,
                    Generic, TypeVar, TypeVarTuple, Unpack, List, Tuple, Union, Dict,
                    ForwardRef, get_type_hints, get_args, get_origin)
from test_annotationlib import HarnessCase, EqualToForwardRef
CANNOT_SUBCLASS_TYPE = 'Cannot subclass special typing classes'
T = TypeVar('T')
KT = TypeVar('KT')
VT = TypeVar('VT')
gth = get_type_hints

class Employee:
    pass



class SelfTests(HarnessCase):
    def test_equality(self):
        self.assertEqual(Self, Self)
        self.assertIs(Self, Self)
        self.assertNotEqual(Self, None)


    def test_basics(self):
        class Foo:
            def bar(self) -> Self: ...
        class FooStr:
            def bar(self) -> 'Self': ...
        class FooStrTyping:
            def bar(self) -> 'typing.Self': ...

        for target in [Foo, FooStr, FooStrTyping]:
            with self.subTest(target=target):
                self.assertEqual(gth(target.bar), {'return': Self})
        self.assertIs(get_origin(Self), None)


    def test_repr(self):
        self.assertEqual(repr(Self), 'typing.Self')


    def test_cannot_subscript(self):
        with self.assertRaises(TypeError):
            Self[int]


    def test_cannot_subclass(self):
        with self.assertRaisesRegex(TypeError, CANNOT_SUBCLASS_TYPE):
            class C(type(Self)):
                pass
        with self.assertRaisesRegex(TypeError,
                r'Cannot subclass typing\.Self'):
            class D(Self):
                pass


    def test_cannot_init(self):
        with self.assertRaises(TypeError):
            Self()
        with self.assertRaises(TypeError):
            type(Self)()


    def test_no_isinstance(self):
        with self.assertRaises(TypeError):
            isinstance(1, Self)
        with self.assertRaises(TypeError):
            issubclass(int, Self)


    def test_alias(self):
        # TypeAliases are not actually part of the spec
        alias_1 = Tuple[Self, Self]
        alias_2 = List[Self]
        alias_3 = ClassVar[Self]
        self.assertEqual(get_args(alias_1), (Self, Self))
        self.assertEqual(get_args(alias_2), (Self,))
        self.assertEqual(get_args(alias_3), (Self,))




class LiteralStringTests(HarnessCase):
    def test_equality(self):
        self.assertEqual(LiteralString, LiteralString)
        self.assertIs(LiteralString, LiteralString)
        self.assertNotEqual(LiteralString, None)


    def test_basics(self):
        class Foo:
            def bar(self) -> LiteralString: ...
        class FooStr:
            def bar(self) -> 'LiteralString': ...
        class FooStrTyping:
            def bar(self) -> 'typing.LiteralString': ...

        for target in [Foo, FooStr, FooStrTyping]:
            with self.subTest(target=target):
                self.assertEqual(gth(target.bar), {'return': LiteralString})
        self.assertIs(get_origin(LiteralString), None)


    def test_repr(self):
        self.assertEqual(repr(LiteralString), 'typing.LiteralString')


    def test_cannot_subscript(self):
        with self.assertRaises(TypeError):
            LiteralString[int]


    def test_cannot_subclass(self):
        with self.assertRaisesRegex(TypeError, CANNOT_SUBCLASS_TYPE):
            class C(type(LiteralString)):
                pass
        with self.assertRaisesRegex(TypeError,
                r'Cannot subclass typing\.LiteralString'):
            class D(LiteralString):
                pass


    def test_cannot_init(self):
        with self.assertRaises(TypeError):
            LiteralString()
        with self.assertRaises(TypeError):
            type(LiteralString)()


    def test_no_isinstance(self):
        with self.assertRaises(TypeError):
            isinstance(1, LiteralString)
        with self.assertRaises(TypeError):
            issubclass(int, LiteralString)


    def test_alias(self):
        alias_1 = Tuple[LiteralString, LiteralString]
        alias_2 = List[LiteralString]
        alias_3 = ClassVar[LiteralString]
        self.assertEqual(get_args(alias_1), (LiteralString, LiteralString))
        self.assertEqual(get_args(alias_2), (LiteralString,))
        self.assertEqual(get_args(alias_3), (LiteralString,))




class LiteralTests(HarnessCase):
    def test_basics(self):
        # All of these are allowed.
        Literal[1]
        Literal[1, 2, 3]
        Literal["x", "y", "z"]
        Literal[None]
        Literal[True]
        Literal[1, "2", False]
        Literal[Literal[1, 2], Literal[4, 5]]
        Literal[b"foo", u"bar"]


    def test_enum(self):
        import enum
        class My(enum.Enum):
            A = 'A'

        self.assertEqual(Literal[My.A].__args__, (My.A,))


    def test_illegal_parameters_do_not_raise_runtime_errors(self):
        # Type checkers should reject these types, but we do not
        # raise errors at runtime to maintain maximum flexibility.
        Literal[int]
        Literal[3j + 2, ..., ()]
        Literal[{"foo": 3, "bar": 4}]
        Literal[T]


    def test_literals_inside_other_types(self):
        List[Literal[1, 2, 3]]
        List[Literal[("foo", "bar", "baz")]]


    def test_repr(self):
        self.assertEqual(repr(Literal[1]), "typing.Literal[1]")
        self.assertEqual(repr(Literal[1, True, "foo"]), "typing.Literal[1, True, 'foo']")
        self.assertEqual(repr(Literal[int]), "typing.Literal[int]")
        self.assertEqual(repr(Literal), "typing.Literal")
        self.assertEqual(repr(Literal[None]), "typing.Literal[None]")
        self.assertEqual(repr(Literal[1, 2, 3, 3]), "typing.Literal[1, 2, 3]")


    def test_dir(self):
        dir_items = set(dir(Literal[1, 2, 3]))
        for required_item in [
            '__args__', '__parameters__', '__origin__',
        ]:
            with self.subTest(required_item=required_item):
                self.assertIn(required_item, dir_items)


    def test_cannot_init(self):
        with self.assertRaises(TypeError):
            Literal()
        with self.assertRaises(TypeError):
            Literal[1]()
        with self.assertRaises(TypeError):
            type(Literal)()
        with self.assertRaises(TypeError):
            type(Literal[1])()


    def test_no_isinstance_or_issubclass(self):
        with self.assertRaises(TypeError):
            isinstance(1, Literal[1])
        with self.assertRaises(TypeError):
            isinstance(int, Literal[1])
        with self.assertRaises(TypeError):
            issubclass(1, Literal[1])
        with self.assertRaises(TypeError):
            issubclass(int, Literal[1])


    def test_no_subclassing(self):
        with self.assertRaises(TypeError):
            class Foo(Literal[1]): pass
        with self.assertRaises(TypeError):
            class Bar(Literal): pass


    def test_no_multiple_subscripts(self):
        with self.assertRaises(TypeError):
            Literal[1][1]


    def test_equal(self):
        self.assertNotEqual(Literal[0], Literal[False])
        self.assertNotEqual(Literal[True], Literal[1])
        self.assertNotEqual(Literal[1], Literal[2])
        self.assertNotEqual(Literal[1, True], Literal[1])
        self.assertNotEqual(Literal[1, True], Literal[1, 1])
        self.assertNotEqual(Literal[1, 2], Literal[True, 2])
        self.assertEqual(Literal[1], Literal[1])
        self.assertEqual(Literal[1, 2], Literal[2, 1])
        self.assertEqual(Literal[1, 2, 3], Literal[1, 2, 3, 3])


    def test_hash(self):
        self.assertEqual(hash(Literal[1]), hash(Literal[1]))
        self.assertEqual(hash(Literal[1, 2]), hash(Literal[2, 1]))
        self.assertEqual(hash(Literal[1, 2, 3]), hash(Literal[1, 2, 3, 3]))


    def test_args(self):
        self.assertEqual(Literal[1, 2, 3].__args__, (1, 2, 3))
        self.assertEqual(Literal[1, 2, 3, 3].__args__, (1, 2, 3))
        self.assertEqual(Literal[1, Literal[2], Literal[3, 4]].__args__, (1, 2, 3, 4))
        # Unhashable arguments will be deduplicated too
        self.assertEqual(Literal[[], []].__args__, ([],))
        self.assertEqual(Literal[{"a": 1}, {"a": 1}].__args__, ({"a": 1},))
        self.assertEqual(
            Literal[1, {'a': 'b'}, 2, {'a': 'b'}, 3].__args__,
            (1, {'a': 'b'}, 2, 3),
        )
        self.assertEqual(Literal[{1}, {1}, {2}, {2}].__args__, ({1}, {2}))


    def test_flatten(self):
        l1 = Literal[Literal[1], Literal[2], Literal[3]]
        l2 = Literal[Literal[1, 2], 3]
        l3 = Literal[Literal[1, 2, 3]]
        for l in l1, l2, l3:
            self.assertEqual(l, Literal[1, 2, 3])
            self.assertEqual(l.__args__, (1, 2, 3))


    def test_does_not_flatten_enum(self):
        import enum
        class Ints(enum.IntEnum):
            A = 1
            B = 2

        l = Literal[
            Literal[Ints.A],
            Literal[Ints.B],
            Literal[1],
            Literal[2],
        ]
        self.assertEqual(l.__args__, (Ints.A, Ints.B, 1, 2))




class ClassVarTests(HarnessCase):
    def test_basics(self):
        with self.assertRaises(TypeError):
            ClassVar[int, str]
        with self.assertRaises(TypeError):
            ClassVar[int][str]


    def test_repr(self):
        self.assertEqual(repr(ClassVar), 'typing.ClassVar')
        cv = ClassVar[int]
        self.assertEqual(repr(cv), 'typing.ClassVar[int]')
        cv = ClassVar[Employee]
        self.assertEqual(repr(cv), 'typing.ClassVar[%s.Employee]' % __name__)


    def test_cannot_subclass(self):
        with self.assertRaisesRegex(TypeError, CANNOT_SUBCLASS_TYPE):
            class C(type(ClassVar)):
                pass
        with self.assertRaisesRegex(TypeError, CANNOT_SUBCLASS_TYPE):
            class D(type(ClassVar[int])):
                pass
        with self.assertRaisesRegex(TypeError,
                                    r'Cannot subclass typing\.ClassVar'):
            class E(ClassVar):
                pass
        with self.assertRaisesRegex(TypeError,
                                    r'Cannot subclass typing\.ClassVar\[int\]'):
            class F(ClassVar[int]):
                pass


    def test_cannot_init(self):
        with self.assertRaises(TypeError):
            ClassVar()
        with self.assertRaises(TypeError):
            type(ClassVar)()
        with self.assertRaises(TypeError):
            type(ClassVar[Optional[int]])()


    def test_no_isinstance(self):
        with self.assertRaises(TypeError):
            isinstance(1, ClassVar[int])
        with self.assertRaises(TypeError):
            issubclass(int, ClassVar)




class FinalTests(HarnessCase):
    def test_basics(self):
        Final[int]  # OK
        with self.assertRaises(TypeError):
            Final[int, str]
        with self.assertRaises(TypeError):
            Final[int][str]
        with self.assertRaises(TypeError):
            Optional[Final[int]]


    def test_repr(self):
        self.assertEqual(repr(Final), 'typing.Final')
        cv = Final[int]
        self.assertEqual(repr(cv), 'typing.Final[int]')
        cv = Final[Employee]
        self.assertEqual(repr(cv), 'typing.Final[%s.Employee]' % __name__)
        cv = Final[tuple[int]]
        self.assertEqual(repr(cv), 'typing.Final[tuple[int]]')


    def test_cannot_subclass(self):
        with self.assertRaisesRegex(TypeError, CANNOT_SUBCLASS_TYPE):
            class C(type(Final)):
                pass
        with self.assertRaisesRegex(TypeError, CANNOT_SUBCLASS_TYPE):
            class D(type(Final[int])):
                pass
        with self.assertRaisesRegex(TypeError,
                r'Cannot subclass typing\.Final'):
            class E(Final):
                pass
        with self.assertRaisesRegex(TypeError,
                r'Cannot subclass typing\.Final\[int\]'):
            class F(Final[int]):
                pass


    def test_cannot_init(self):
        with self.assertRaises(TypeError):
            Final()
        with self.assertRaises(TypeError):
            type(Final)()
        with self.assertRaises(TypeError):
            type(Final[Optional[int]])()


    def test_no_isinstance(self):
        with self.assertRaises(TypeError):
            isinstance(1, Final[int])
        with self.assertRaises(TypeError):
            issubclass(int, Final)




class GetTypeHintsTests(HarnessCase):
    def test_get_type_hints_annotated(self):
        def foobar(x: List['X']): ...
        X = Annotated[int, (1, 10)]
        self.assertEqual(
            get_type_hints(foobar, globals(), locals()),
            {'x': List[int]}
        )
        self.assertEqual(
            get_type_hints(foobar, globals(), locals(), include_extras=True),
            {'x': List[Annotated[int, (1, 10)]]}
        )

        def foobar(x: list[ForwardRef('X')]): ...
        X = Annotated[int, (1, 10)]
        self.assertEqual(
            get_type_hints(foobar, globals(), locals()),
            {'x': list[int]}
        )
        self.assertEqual(
            get_type_hints(foobar, globals(), locals(), include_extras=True),
            {'x': list[Annotated[int, (1, 10)]]}
        )

        BA = Tuple[Annotated[T, (1, 0)], ...]
        def barfoo(x: BA): ...
        self.assertEqual(get_type_hints(barfoo, globals(), locals())['x'], Tuple[T, ...])
        self.assertEqual(
            get_type_hints(barfoo, globals(), locals(), include_extras=True)['x'],
            BA
        )

        BA = tuple[Annotated[T, (1, 0)], ...]
        def barfoo(x: BA): ...
        self.assertEqual(get_type_hints(barfoo, globals(), locals())['x'], tuple[T, ...])
        self.assertEqual(
            get_type_hints(barfoo, globals(), locals(), include_extras=True)['x'],
            BA
        )

        def barfoo2(x: typing.Callable[..., Annotated[List[T], "const"]],
                    y: typing.Union[int, Annotated[T, "mutable"]]): ...
        self.assertEqual(
            get_type_hints(barfoo2, globals(), locals()),
            {'x': typing.Callable[..., List[T]], 'y': typing.Union[int, T]}
        )

        BA2 = typing.Callable[..., List[T]]
        def barfoo3(x: BA2): ...
        self.assertIs(
            get_type_hints(barfoo3, globals(), locals(), include_extras=True)["x"],
            BA2
        )
        BA3 = typing.Annotated[int | float, "const"]
        def barfoo4(x: BA3): ...
        self.assertEqual(
            get_type_hints(barfoo4, globals(), locals()),
            {"x": int | float}
        )
        self.assertEqual(
            get_type_hints(barfoo4, globals(), locals(), include_extras=True),
            {"x": typing.Annotated[int | float, "const"]}
        )


    def test_get_type_hints_annotated_in_union(self):  # bpo-46603
        def with_union(x: int | list[Annotated[str, 'meta']]): ...

        self.assertEqual(get_type_hints(with_union), {'x': int | list[str]})
        self.assertEqual(
            get_type_hints(with_union, include_extras=True),
            {'x': int | list[Annotated[str, 'meta']]},
        )


    def test_get_type_hints_annotated_refs(self):

        Const = Annotated[T, "Const"]

        class MySet(Generic[T]):

            def __ior__(self, other: "Const[MySet[T]]") -> "MySet[T]":
                ...

            def __iand__(self, other: Const["MySet[T]"]) -> "MySet[T]":
                ...

        self.assertEqual(
            get_type_hints(MySet.__iand__, globals(), locals()),
            {'other': MySet[T], 'return': MySet[T]}
        )

        self.assertEqual(
            get_type_hints(MySet.__iand__, globals(), locals(), include_extras=True),
            {'other': Const[MySet[T]], 'return': MySet[T]}
        )

        self.assertEqual(
            get_type_hints(MySet.__ior__, globals(), locals()),
            {'other': MySet[T], 'return': MySet[T]}
        )


    def test_get_type_hints_annotated_with_none_default(self):
        # See: https://bugs.python.org/issue46195
        def annotated_with_none_default(x: Annotated[int, 'data'] = None): ...
        self.assertEqual(
            get_type_hints(annotated_with_none_default),
            {'x': int},
        )
        self.assertEqual(
            get_type_hints(annotated_with_none_default, include_extras=True),
            {'x': Annotated[int, 'data']},
        )


    def test_special_forms_no_forward(self):
        def f(x: ClassVar[int]):
            pass
        self.assertEqual(get_type_hints(f), {'x': ClassVar[int]})


    def test_special_forms_forward(self):

        class C:
            a: Annotated['ClassVar[int]', (3, 5)] = 4
            b: Annotated['Final[int]', "const"] = 4
            x: 'ClassVar' = 4
            y: 'Final' = 4

        class CF:
            b: List['Final[int]'] = 4

        self.assertEqual(get_type_hints(C, globals())['a'], ClassVar[int])
        self.assertEqual(get_type_hints(C, globals())['b'], Final[int])
        self.assertEqual(get_type_hints(C, globals())['x'], ClassVar)
        self.assertEqual(get_type_hints(C, globals())['y'], Final)
        lfi = get_type_hints(CF, globals())['b']
        self.assertIs(get_origin(lfi), list)
        self.assertEqual(get_args(lfi), (Final[int],))


    def test_basics(self):

        class Node(Generic[T]):

            def __init__(self, label: T):
                self.label = label
                self.left = self.right = None

            def add_both(self,
                         left: 'Optional[Node[T]]',
                         right: 'Node[T]' = None,
                         stuff: int = None,
                         blah=None):
                self.left = left
                self.right = right

            def add_left(self, node: Optional['Node[T]']):
                self.add_both(node, None)

            def add_right(self, node: 'Node[T]' = None):
                self.add_both(None, node)

        t = Node[int]
        both_hints = get_type_hints(t.add_both, globals(), locals())
        self.assertEqual(both_hints['left'], Optional[Node[T]])
        self.assertEqual(both_hints['right'], Node[T])
        self.assertEqual(both_hints['stuff'], int)
        self.assertNotIn('blah', both_hints)

        left_hints = get_type_hints(t.add_left, globals(), locals())
        self.assertEqual(left_hints['node'], Optional[Node[T]])

        right_hints = get_type_hints(t.add_right, globals(), locals())
        self.assertEqual(right_hints['node'], Node[T])




class RequiredTests(HarnessCase):
    def test_basics(self):
        with self.assertRaises(TypeError):
            Required[NotRequired]
        with self.assertRaises(TypeError):
            Required[int, str]
        with self.assertRaises(TypeError):
            Required[int][str]


    def test_repr(self):
        self.assertEqual(repr(Required), 'typing.Required')
        cv = Required[int]
        self.assertEqual(repr(cv), 'typing.Required[int]')
        cv = Required[Employee]
        self.assertEqual(repr(cv), f'typing.Required[{__name__}.Employee]')


    def test_cannot_subclass(self):
        with self.assertRaisesRegex(TypeError, CANNOT_SUBCLASS_TYPE):
            class C(type(Required)):
                pass
        with self.assertRaisesRegex(TypeError, CANNOT_SUBCLASS_TYPE):
            class D(type(Required[int])):
                pass
        with self.assertRaisesRegex(TypeError,
                r'Cannot subclass typing\.Required'):
            class E(Required):
                pass
        with self.assertRaisesRegex(TypeError,
                r'Cannot subclass typing\.Required\[int\]'):
            class F(Required[int]):
                pass


    def test_cannot_init(self):
        with self.assertRaises(TypeError):
            Required()
        with self.assertRaises(TypeError):
            type(Required)()
        with self.assertRaises(TypeError):
            type(Required[Optional[int]])()


    def test_no_isinstance(self):
        with self.assertRaises(TypeError):
            isinstance(1, Required[int])
        with self.assertRaises(TypeError):
            issubclass(int, Required)




class NotRequiredTests(HarnessCase):
    def test_basics(self):
        with self.assertRaises(TypeError):
            NotRequired[Required]
        with self.assertRaises(TypeError):
            NotRequired[int, str]
        with self.assertRaises(TypeError):
            NotRequired[int][str]


    def test_repr(self):
        self.assertEqual(repr(NotRequired), 'typing.NotRequired')
        cv = NotRequired[int]
        self.assertEqual(repr(cv), 'typing.NotRequired[int]')
        cv = NotRequired[Employee]
        self.assertEqual(repr(cv), f'typing.NotRequired[{__name__}.Employee]')


    def test_cannot_subclass(self):
        with self.assertRaisesRegex(TypeError, CANNOT_SUBCLASS_TYPE):
            class C(type(NotRequired)):
                pass
        with self.assertRaisesRegex(TypeError, CANNOT_SUBCLASS_TYPE):
            class D(type(NotRequired[int])):
                pass
        with self.assertRaisesRegex(TypeError,
                r'Cannot subclass typing\.NotRequired'):
            class E(NotRequired):
                pass
        with self.assertRaisesRegex(TypeError,
                r'Cannot subclass typing\.NotRequired\[int\]'):
            class F(NotRequired[int]):
                pass


    def test_cannot_init(self):
        with self.assertRaises(TypeError):
            NotRequired()
        with self.assertRaises(TypeError):
            type(NotRequired)()
        with self.assertRaises(TypeError):
            type(NotRequired[Optional[int]])()


    def test_no_isinstance(self):
        with self.assertRaises(TypeError):
            isinstance(1, NotRequired[int])
        with self.assertRaises(TypeError):
            issubclass(int, NotRequired)




class AnnotatedTests(HarnessCase):
    def test_new(self):
        with self.assertRaisesRegex(
            TypeError, 'Cannot instantiate typing.Annotated',
        ):
            Annotated()


    def test_repr(self):
        self.assertEqual(
            repr(Annotated[int, 4, 5]),
            "typing.Annotated[int, 4, 5]"
        )
        self.assertEqual(
            repr(Annotated[List[int], 4, 5]),
            "typing.Annotated[typing.List[int], 4, 5]"
        )


    def test_dir(self):
        dir_items = set(dir(Annotated[int, 4]))
        for required_item in [
            '__args__', '__parameters__', '__origin__',
            '__metadata__',
        ]:
            with self.subTest(required_item=required_item):
                self.assertIn(required_item, dir_items)


    def test_flatten(self):
        A = Annotated[Annotated[int, 4], 5]
        self.assertEqual(A, Annotated[int, 4, 5])
        self.assertEqual(A.__metadata__, (4, 5))
        self.assertEqual(A.__origin__, int)


    def test_order_in_union(self):
        expr1 = Annotated[int, 1] | str | Annotated[str, {}] | int
        for args in itertools.permutations(get_args(expr1)):
            with self.subTest(args=args):
                self.assertEqual(expr1, reduce(operator.or_, args))

        expr2 = Union[Annotated[int, 1], str, Annotated[str, {}], int]
        for args in itertools.permutations(get_args(expr2)):
            with self.subTest(args=args):
                self.assertEqual(expr2, Union[args])


    def test_specialize(self):
        L = Annotated[List[T], "my decoration"]
        LI = Annotated[List[int], "my decoration"]
        self.assertEqual(L[int], Annotated[List[int], "my decoration"])
        self.assertEqual(L[int].__metadata__, ("my decoration",))
        self.assertEqual(L[int].__origin__, List[int])
        with self.assertRaises(TypeError):
            LI[int]
        with self.assertRaises(TypeError):
            L[int, float]


    def test_hash_eq(self):
        self.assertEqual(len({Annotated[int, 4, 5], Annotated[int, 4, 5]}), 1)
        self.assertNotEqual(Annotated[int, 4, 5], Annotated[int, 5, 4])
        self.assertNotEqual(Annotated[int, 4, 5], Annotated[str, 4, 5])
        self.assertNotEqual(Annotated[int, 4], Annotated[int, 4, 4])
        self.assertEqual(
            {Annotated[int, 4, 5], Annotated[int, 4, 5], Annotated[T, 4, 5]},
            {Annotated[int, 4, 5], Annotated[T, 4, 5]}
        )
        # Unhashable `metadata` raises `TypeError`:
        a1 = Annotated[int, []]
        with self.assertRaises(TypeError):
            hash(a1)

        class A:
            __hash__ = None
        a2 = Annotated[int, A()]
        with self.assertRaises(TypeError):
            hash(a2)


    def test_instantiate(self):
        class C:
            classvar = 4

            def __init__(self, x):
                self.x = x

            def __eq__(self, other):
                if not isinstance(other, C):
                    return NotImplemented
                return other.x == self.x

        A = Annotated[C, "a decoration"]
        a = A(5)
        c = C(5)
        self.assertEqual(a, c)
        self.assertEqual(a.x, c.x)
        self.assertEqual(a.classvar, c.classvar)


    def test_instantiate_generic(self):
        MyCount = Annotated[typing.Counter[T], "my decoration"]
        self.assertEqual(MyCount([4, 4, 5]), {4: 2, 5: 1})
        self.assertEqual(MyCount[int]([4, 4, 5]), {4: 2, 5: 1})


    def test_instantiate_immutable(self):
        class C:
            def __setattr__(self, key, value):
                raise Exception("should be ignored")

        A = Annotated[C, "a decoration"]
        # gh-115165: This used to cause RuntimeError to be raised
        # when we tried to set `__orig_class__` on the `C` instance
        # returned by the `A()` call
        self.assertIsInstance(A(), C)


    def test_cannot_instantiate_forward(self):
        A = Annotated["int", (5, 6)]
        with self.assertRaises(TypeError):
            A(5)


    def test_cannot_instantiate_type_var(self):
        A = Annotated[T, (5, 6)]
        with self.assertRaises(TypeError):
            A(5)


    def test_cannot_getattr_typevar(self):
        with self.assertRaises(AttributeError):
            Annotated[T, (5, 7)].x


    def test_attr_passthrough(self):
        class C:
            classvar = 4

        A = Annotated[C, "a decoration"]
        self.assertEqual(A.classvar, 4)
        A.x = 5
        self.assertEqual(C.x, 5)


    def test_special_form_containment(self):
        class C:
            classvar: Annotated[ClassVar[int], "a decoration"] = 4
            const: Annotated[Final[int], "Const"] = 4

        self.assertEqual(get_type_hints(C, globals())['classvar'], ClassVar[int])
        self.assertEqual(get_type_hints(C, globals())['const'], Final[int])


    def test_special_forms_nesting(self):
        # These are uncommon types and are to ensure runtime
        # is lax on validation. See gh-89547 for more context.
        class CF:
            x: ClassVar[Final[int]]

        class FC:
            x: Final[ClassVar[int]]

        class ACF:
            x: Annotated[ClassVar[Final[int]], "a decoration"]

        class CAF:
            x: ClassVar[Annotated[Final[int], "a decoration"]]

        class AFC:
            x: Annotated[Final[ClassVar[int]], "a decoration"]

        class FAC:
            x: Final[Annotated[ClassVar[int], "a decoration"]]

        self.assertEqual(get_type_hints(CF, globals())['x'], ClassVar[Final[int]])
        self.assertEqual(get_type_hints(FC, globals())['x'], Final[ClassVar[int]])
        self.assertEqual(get_type_hints(ACF, globals())['x'], ClassVar[Final[int]])
        self.assertEqual(get_type_hints(CAF, globals())['x'], ClassVar[Final[int]])
        self.assertEqual(get_type_hints(AFC, globals())['x'], Final[ClassVar[int]])
        self.assertEqual(get_type_hints(FAC, globals())['x'], Final[ClassVar[int]])


    def test_cannot_subclass(self):
        with self.assertRaisesRegex(TypeError, "Cannot subclass .*Annotated"):
            class C(Annotated):
                pass


    def test_cannot_check_instance(self):
        with self.assertRaises(TypeError):
            isinstance(5, Annotated[int, "positive"])


    def test_cannot_check_subclass(self):
        with self.assertRaises(TypeError):
            issubclass(int, Annotated[int, "positive"])


    def test_too_few_type_args(self):
        with self.assertRaisesRegex(TypeError, 'at least two arguments'):
            Annotated[int]


    def test_subst(self):
        dec = "a decoration"
        dec2 = "another decoration"

        S = Annotated[T, dec2]
        self.assertEqual(S[int], Annotated[int, dec2])

        self.assertEqual(S[Annotated[int, dec]], Annotated[int, dec, dec2])
        L = Annotated[List[T], dec]

        self.assertEqual(L[int], Annotated[List[int], dec])
        with self.assertRaises(TypeError):
            L[int, int]

        self.assertEqual(S[L[int]], Annotated[List[int], dec, dec2])

        D = Annotated[typing.Dict[KT, VT], dec]
        self.assertEqual(D[str, int], Annotated[typing.Dict[str, int], dec])
        with self.assertRaises(TypeError):
            D[int]

        It = Annotated[int, dec]
        with self.assertRaises(TypeError):
            It[None]

        LI = L[int]
        with self.assertRaises(TypeError):
            LI[None]


    def test_typevar_subst(self):
        dec = "a decoration"
        Ts = TypeVarTuple('Ts')
        T = TypeVar('T')
        T1 = TypeVar('T1')
        T2 = TypeVar('T2')

        A = Annotated[tuple[*Ts], dec]
        self.assertEqual(A[int], Annotated[tuple[int], dec])
        self.assertEqual(A[str, int], Annotated[tuple[str, int], dec])
        with self.assertRaises(TypeError):
            Annotated[*Ts, dec]

        B = Annotated[Tuple[Unpack[Ts]], dec]
        self.assertEqual(B[int], Annotated[Tuple[int], dec])
        self.assertEqual(B[str, int], Annotated[Tuple[str, int], dec])
        with self.assertRaises(TypeError):
            Annotated[Unpack[Ts], dec]

        C = Annotated[tuple[T, *Ts], dec]
        self.assertEqual(C[int], Annotated[tuple[int], dec])
        self.assertEqual(C[int, str], Annotated[tuple[int, str], dec])
        self.assertEqual(
            C[int, str, float],
            Annotated[tuple[int, str, float], dec]
        )
        with self.assertRaises(TypeError):
            C[()]

        D = Annotated[Tuple[T, Unpack[Ts]], dec]
        self.assertEqual(D[int], Annotated[Tuple[int], dec])
        self.assertEqual(D[int, str], Annotated[Tuple[int, str], dec])
        self.assertEqual(
            D[int, str, float],
            Annotated[Tuple[int, str, float], dec]
        )
        with self.assertRaises(TypeError):
            D[()]

        E = Annotated[tuple[*Ts, T], dec]
        self.assertEqual(E[int], Annotated[tuple[int], dec])
        self.assertEqual(E[int, str], Annotated[tuple[int, str], dec])
        self.assertEqual(
            E[int, str, float],
            Annotated[tuple[int, str, float], dec]
        )
        with self.assertRaises(TypeError):
            E[()]

        F = Annotated[Tuple[Unpack[Ts], T], dec]
        self.assertEqual(F[int], Annotated[Tuple[int], dec])
        self.assertEqual(F[int, str], Annotated[Tuple[int, str], dec])
        self.assertEqual(
            F[int, str, float],
            Annotated[Tuple[int, str, float], dec]
        )
        with self.assertRaises(TypeError):
            F[()]

        G = Annotated[tuple[T1, *Ts, T2], dec]
        self.assertEqual(G[int, str], Annotated[tuple[int, str], dec])
        self.assertEqual(
            G[int, str, float],
            Annotated[tuple[int, str, float], dec]
        )
        self.assertEqual(
            G[int, str, bool, float],
            Annotated[tuple[int, str, bool, float], dec]
        )
        with self.assertRaises(TypeError):
            G[int]

        H = Annotated[Tuple[T1, Unpack[Ts], T2], dec]
        self.assertEqual(H[int, str], Annotated[Tuple[int, str], dec])
        self.assertEqual(
            H[int, str, float],
            Annotated[Tuple[int, str, float], dec]
        )
        self.assertEqual(
            H[int, str, bool, float],
            Annotated[Tuple[int, str, bool, float], dec]
        )
        with self.assertRaises(TypeError):
            H[int]

        # Now let's try creating an alias from an alias.

        Ts2 = TypeVarTuple('Ts2')
        T3 = TypeVar('T3')
        T4 = TypeVar('T4')

        # G is Annotated[tuple[T1, *Ts, T2], dec].
        I = G[T3, *Ts2, T4]
        J = G[T3, Unpack[Ts2], T4]

        for x, y in [
            (I,                  Annotated[tuple[T3, *Ts2, T4], dec]),
            (J,                  Annotated[tuple[T3, Unpack[Ts2], T4], dec]),
            (I[int, str],        Annotated[tuple[int, str], dec]),
            (J[int, str],        Annotated[tuple[int, str], dec]),
            (I[int, str, float], Annotated[tuple[int, str, float], dec]),
            (J[int, str, float], Annotated[tuple[int, str, float], dec]),
            (I[int, str, bool, float],
                                 Annotated[tuple[int, str, bool, float], dec]),
            (J[int, str, bool, float],
                                 Annotated[tuple[int, str, bool, float], dec]),
        ]:
            self.assertEqual(x, y)

        with self.assertRaises(TypeError):
            I[int]
        with self.assertRaises(TypeError):
            J[int]


    def test_annotated_in_other_types(self):
        X = List[Annotated[T, 5]]
        self.assertEqual(X[int], List[Annotated[int, 5]])


    def test_annotated_mro(self):
        class X(Annotated[int, (1, 10)]): ...
        self.assertEqual(X.__mro__, (X, int, object),
                         "Annotated should be transparent.")


    def test_annotated_cached_with_types(self):
        class A(str): ...
        class B(str): ...

        field_a1 = Annotated[str, A("X")]
        field_a2 = Annotated[str, B("X")]
        a1_metadata = field_a1.__metadata__[0]
        a2_metadata = field_a2.__metadata__[0]

        self.assertIs(type(a1_metadata), A)
        self.assertEqual(a1_metadata, A("X"))
        self.assertIs(type(a2_metadata), B)
        self.assertEqual(a2_metadata, B("X"))
        self.assertIsNot(type(a1_metadata), type(a2_metadata))

        field_b1 = Annotated[str, A("Y")]
        field_b2 = Annotated[str, B("Y")]
        b1_metadata = field_b1.__metadata__[0]
        b2_metadata = field_b2.__metadata__[0]

        self.assertIs(type(b1_metadata), A)
        self.assertEqual(b1_metadata, A("Y"))
        self.assertIs(type(b2_metadata), B)
        self.assertEqual(b2_metadata, B("Y"))
        self.assertIsNot(type(b1_metadata), type(b2_metadata))

        field_c1 = Annotated[int, 1]
        field_c2 = Annotated[int, 1.0]
        field_c3 = Annotated[int, True]

        self.assertIs(type(field_c1.__metadata__[0]), int)
        self.assertIs(type(field_c2.__metadata__[0]), float)
        self.assertIs(type(field_c3.__metadata__[0]), bool)


    def test_forwardref_partial_evaluation(self):
        # Test that Annotated partially evaluates if it contains a ForwardRef
        # See: https://github.com/python/cpython/issues/137706
        def f(x: Annotated[undefined, '']): pass

        ann = annotationlib.get_annotations(f, format=annotationlib.Format.FORWARDREF)

        # Test that the attributes are retrievable from the partially evaluated annotation
        x_ann = ann['x']
        self.assertIs(get_origin(x_ann), Annotated)
        self.assertEqual(x_ann.__origin__, EqualToForwardRef('undefined', owner=f))
        self.assertEqual(x_ann.__metadata__, ('',))




class TypeAliasTests(HarnessCase):
    def test_canonical_usage_with_variable_annotation(self):
        Alias: TypeAlias = Employee


    def test_canonical_usage_with_type_comment(self):
        Alias = Employee  # type: TypeAlias


    def test_cannot_instantiate(self):
        with self.assertRaises(TypeError):
            TypeAlias()


    def test_no_isinstance(self):
        with self.assertRaises(TypeError):
            isinstance(42, TypeAlias)


    def test_stringized_usage(self):
        class A:
            a: "TypeAlias"
        self.assertEqual(get_type_hints(A), {'a': TypeAlias})


    def test_no_issubclass(self):
        with self.assertRaises(TypeError):
            issubclass(Employee, TypeAlias)

        with self.assertRaises(TypeError):
            issubclass(TypeAlias, Employee)


    def test_cannot_subclass(self):
        with self.assertRaisesRegex(TypeError,
                r'Cannot subclass typing\.TypeAlias'):
            class C(TypeAlias):
                pass

        with self.assertRaises(TypeError):
            class D(type(TypeAlias)):
                pass


    def test_repr(self):
        self.assertEqual(repr(TypeAlias), 'typing.TypeAlias')


    def test_cannot_subscript(self):
        with self.assertRaises(TypeError):
            TypeAlias[int]




class TypeGuardTests(HarnessCase):
    def test_basics(self):
        TypeGuard[int]  # OK

        def foo(arg) -> TypeGuard[int]: ...
        self.assertEqual(gth(foo), {'return': TypeGuard[int]})

        with self.assertRaises(TypeError):
            TypeGuard[int, str]


    def test_repr(self):
        self.assertEqual(repr(TypeGuard), 'typing.TypeGuard')
        cv = TypeGuard[int]
        self.assertEqual(repr(cv), 'typing.TypeGuard[int]')
        cv = TypeGuard[Employee]
        self.assertEqual(repr(cv), 'typing.TypeGuard[%s.Employee]' % __name__)
        cv = TypeGuard[tuple[int]]
        self.assertEqual(repr(cv), 'typing.TypeGuard[tuple[int]]')


    def test_cannot_subclass(self):
        with self.assertRaisesRegex(TypeError, CANNOT_SUBCLASS_TYPE):
            class C(type(TypeGuard)):
                pass
        with self.assertRaisesRegex(TypeError, CANNOT_SUBCLASS_TYPE):
            class D(type(TypeGuard[int])):
                pass
        with self.assertRaisesRegex(TypeError,
                                    r'Cannot subclass typing\.TypeGuard'):
            class E(TypeGuard):
                pass
        with self.assertRaisesRegex(TypeError,
                                    r'Cannot subclass typing\.TypeGuard\[int\]'):
            class F(TypeGuard[int]):
                pass


    def test_cannot_init(self):
        with self.assertRaises(TypeError):
            TypeGuard()
        with self.assertRaises(TypeError):
            type(TypeGuard)()
        with self.assertRaises(TypeError):
            type(TypeGuard[Optional[int]])()


    def test_no_isinstance(self):
        with self.assertRaises(TypeError):
            isinstance(1, TypeGuard[int])
        with self.assertRaises(TypeError):
            issubclass(int, TypeGuard)




class TypeIsTests(HarnessCase):
    def test_basics(self):
        TypeIs[int]  # OK

        def foo(arg) -> TypeIs[int]: ...
        self.assertEqual(gth(foo), {'return': TypeIs[int]})

        with self.assertRaises(TypeError):
            TypeIs[int, str]


    def test_repr(self):
        self.assertEqual(repr(TypeIs), 'typing.TypeIs')
        cv = TypeIs[int]
        self.assertEqual(repr(cv), 'typing.TypeIs[int]')
        cv = TypeIs[Employee]
        self.assertEqual(repr(cv), 'typing.TypeIs[%s.Employee]' % __name__)
        cv = TypeIs[tuple[int]]
        self.assertEqual(repr(cv), 'typing.TypeIs[tuple[int]]')


    def test_cannot_subclass(self):
        with self.assertRaisesRegex(TypeError, CANNOT_SUBCLASS_TYPE):
            class C(type(TypeIs)):
                pass
        with self.assertRaisesRegex(TypeError, CANNOT_SUBCLASS_TYPE):
            class D(type(TypeIs[int])):
                pass
        with self.assertRaisesRegex(TypeError,
                                    r'Cannot subclass typing\.TypeIs'):
            class E(TypeIs):
                pass
        with self.assertRaisesRegex(TypeError,
                                    r'Cannot subclass typing\.TypeIs\[int\]'):
            class F(TypeIs[int]):
                pass


    def test_cannot_init(self):
        with self.assertRaises(TypeError):
            TypeIs()
        with self.assertRaises(TypeError):
            type(TypeIs)()
        with self.assertRaises(TypeError):
            type(TypeIs[Optional[int]])()


    def test_no_isinstance(self):
        with self.assertRaises(TypeError):
            isinstance(1, TypeIs[int])
        with self.assertRaises(TypeError):
            issubclass(int, TypeIs)




class NeverTests(HarnessCase):
    def test_repr(self):
        self.assertEqual(repr(Never), 'typing.Never')


    def test_get_type_hints(self):
        def some(arg: Never) -> Never: ...
        def some_str(arg: 'Never') -> 'typing.Never': ...

        expected = {'arg': Never, 'return': Never}
        for target in [some, some_str]:
            with self.subTest(target=target):
                self.assertEqual(gth(target), expected)


class NativeQualifierRegression(HarnessCase):
    # CPython _strip_annotations, including the native Unpack representation.
    def test_readonly_and_unpack_nested_metadata(self):
        class C:
            field: ReadOnly[Required[Annotated['int', 'metadata']]]
        self.assertEqual(get_type_hints(C), {'field': int})
        self.assertEqual(get_type_hints(C, include_extras=True),
                         {'field': ReadOnly[Required[Annotated[int, 'metadata']]]})
        def func(value: Unpack[tuple[Annotated['int', 'metadata'], ...]]): pass
        self.assertEqual(get_type_hints(func), {'value': Unpack[tuple[int, ...]]})
        self.assertEqual(get_type_hints(func, include_extras=True),
                         {'value': Unpack[tuple[Annotated[int, 'metadata'], ...]]})

if __name__ == '__main__': unittest.main()
