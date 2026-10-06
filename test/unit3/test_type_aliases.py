# Ten unchanged CPython 3.14 type-alias methods at 18ef0f0cb52.
# Additional scope/laziness cases below are checked against the same CPython.
import unittest
import types
from typing import TypeAliasType, get_args

class TypeParamsAliasValueTest(unittest.TestCase):

    def test_alias_value_01(self):
        type TA1 = int

        self.assertIsInstance(TA1, TypeAliasType)
        self.assertEqual(TA1.__value__, int)
        self.assertEqual(TA1.__parameters__, ())
        self.assertEqual(TA1.__type_params__, ())

        type TA2 = TA1 | str

        self.assertIsInstance(TA2, TypeAliasType)
        a, b = TA2.__value__.__args__
        self.assertEqual(a, TA1)
        self.assertEqual(b, str)
        self.assertEqual(TA2.__parameters__, ())
        self.assertEqual(TA2.__type_params__, ())

    def test_raising(self):
        type MissingName = list[_My_X]
        with self.assertRaisesRegex(
            NameError,
            "cannot access free variable '_My_X' where it is not associated with a value",
        ):
            MissingName.__value__
        _My_X = int
        self.assertEqual(MissingName.__value__, list[int])
        del _My_X
        # Cache should still work:
        self.assertEqual(MissingName.__value__, list[int])

        # Explicit exception:
        type ExprException = 1 / 0
        with self.assertRaises(ZeroDivisionError):
            ExprException.__value__

class TypeAliasConstructorTest(unittest.TestCase):

    def test_basic(self):
        TA = TypeAliasType("TA", int)
        self.assertEqual(TA.__name__, "TA")
        self.assertIs(TA.__value__, int)
        self.assertEqual(TA.__type_params__, ())
        self.assertEqual(TA.__module__, __name__)

    def test_attributes_with_exec(self):
        ns = {}
        exec("type TA = int", ns, ns)
        TA = ns["TA"]
        self.assertEqual(TA.__name__, "TA")
        self.assertIs(TA.__value__, int)
        self.assertEqual(TA.__type_params__, ())
        self.assertIs(TA.__module__, None)

    def test_not_generic(self):
        TA = TypeAliasType("TA", list[int], type_params=())
        self.assertEqual(TA.__name__, "TA")
        self.assertEqual(TA.__value__, list[int])
        self.assertEqual(TA.__type_params__, ())
        self.assertEqual(TA.__module__, __name__)
        with self.assertRaisesRegex(
            TypeError,
            "Only generic type aliases are subscriptable",
        ):
            TA[int]

    def test_keywords(self):
        TA = TypeAliasType(name="TA", value=int)
        self.assertEqual(TA.__name__, "TA")
        self.assertIs(TA.__value__, int)
        self.assertEqual(TA.__type_params__, ())
        self.assertEqual(TA.__module__, __name__)

    def test_errors(self):
        with self.assertRaises(TypeError):
            TypeAliasType()
        with self.assertRaises(TypeError):
            TypeAliasType("TA")
        with self.assertRaises(TypeError):
            TypeAliasType("TA", list, ())
        with self.assertRaises(TypeError):
            TypeAliasType("TA", list, type_params=42)

class TypeAliasTypeTest(unittest.TestCase):

    def test_immutable(self):
        with self.assertRaises(TypeError):
            TypeAliasType.whatever = "not allowed"

    def test_no_subclassing(self):
        with self.assertRaisesRegex(TypeError, "not an acceptable base type"):
            class MyAlias(TypeAliasType):
                pass

    def test_union(self):
        type Alias1 = int
        type Alias2 = str
        union = Alias1 | Alias2
        self.assertIsInstance(union, types.UnionType)
        self.assertEqual(get_args(union), (Alias1, Alias2))
        union2 = Alias1 | list[float]
        self.assertIsInstance(union2, types.UnionType)
        self.assertEqual(get_args(union2), (Alias1, list[float]))
        union3 = list[range] | Alias1
        self.assertIsInstance(union3, types.UnionType)
        self.assertEqual(get_args(union3), (list[range], Alias1))

class TypeAliasScopes(unittest.TestCase):
    def test_lazy_recursive_and_live_lookup(self):
        calls = []
        def evaluate():
            calls.append('eval')
            return later
        type Alias = evaluate()
        self.assertEqual(calls, [])
        with self.assertRaises(NameError): Alias.__value__
        later = list[int]
        self.assertEqual(Alias.__value__, later)
        later = str
        self.assertEqual(Alias.__value__, list[int])
        self.assertEqual(Alias.evaluate_value(), str)
        self.assertEqual(calls, ['eval', 'eval', 'eval'])
        type Recursive = Recursive
        self.assertIs(Recursive.__value__, Recursive)
        self.assertEqual(repr(Recursive), 'Recursive')
        type X = list[Y]
        type Y = list[X]
        self.assertEqual(X.__value__, list[Y])
        self.assertEqual(Y.__value__, list[X])
        self.assertEqual(Alias.evaluate_value.__name__, 'Alias')
        self.assertEqual(Alias.evaluate_value.__defaults__, (1,))
        self.assertEqual(Alias.evaluate_value.__code__.co_varnames, ('.format',))
        self.assertEqual(Alias.evaluate_value.__code__.co_posonlyargcount, 1)
        with self.assertRaises(TypeError): Alias.evaluate_value(format=1)
        with self.assertRaises(TypeError): Alias.evaluate_value(**{'.format': 1})

    def test_class_scope_and_closures(self):
        value = float
        class C:
            value = int
            type Alias = value
        self.assertIs(C.Alias.__value__, int)
        C.value = str
        self.assertIs(C.Alias.__value__, int)
        self.assertIs(C.Alias.evaluate_value(), str)
        class D:
            type Alias = value
        self.assertIs(D.Alias.__value__, float)
        class E:
            type Alias = E
        self.assertIs(E.Alias.__value__, E)
        type WithComprehension = [value for _ in range(2)]
        self.assertEqual(WithComprehension.__value__, [float, float])

    def test_future_and_syntax(self):
        ns = {}
        exec('from __future__ import annotations\ntype Alias = int | str', ns)
        self.assertEqual(ns['Alias'].__value__, int | str)
        for source in ('type Alias = (x := int)', 'type Alias = (yield int)', 'type Alias = (yield from [])', 'type Alias = await x'):
            with self.assertRaises(SyntaxError): compile(source, '<test>', 'exec')
        class C: pass
        alias = TypeAliasType('A', C)
        for name in ('__name__', '__module__', '__value__', '__type_params__', '__parameters__'):
            with self.assertRaises(AttributeError): setattr(alias, name, None)
            with self.assertRaises(AttributeError): delattr(alias, name)

    def test_constant_evaluator_and_alias_scope_restrictions(self):
        evaluator = TypeAliasType('A', int).evaluate_value
        for format in (-1, 0, 1, 2, 3, 5, True): self.assertIs(evaluator(format), int)
        self.assertEqual(evaluator(4), 'int')
        self.assertEqual(TypeAliasType('A', (int, str)).evaluate_value(4), '(int, str)')
        self.assertEqual(TypeAliasType('A', type(None)).evaluate_value(4), 'None')
        class Index:
            def __index__(self): return 1
        self.assertIs(evaluator(Index()), int)
        for args in ((), (1, 2), (1.0,), ('1',)):
            with self.assertRaises(TypeError): evaluator(*args)
        with self.assertRaises(TypeError): evaluator(format=1)
        for format in (-2**31-1, 2**31, 2**100):
            with self.assertRaises(OverflowError): evaluator(format)
        for source in ('type A = [(x := int) for _ in range(1)]',
                       'type A = ((x := int) for _ in range(1))'):
            with self.assertRaisesRegex(SyntaxError, 'assignment expression within a comprehension cannot be used in a type alias'):
                compile(source, '<test>', 'exec')
        type A = lambda: (x := int)
        self.assertIs(A.__value__(), int)
        self.assertEqual(A.__value__.__qualname__, type(self).test_constant_evaluator_and_alias_scope_restrictions.__qualname__ + '.<locals>.<lambda>')
        ns = {}
        exec('type A = lambda: 1\nclass C:\n type A = lambda: 2', ns)
        self.assertEqual(ns['A'].__value__.__qualname__, '<lambda>')
        self.assertEqual(ns['C'].A.__value__.__qualname__, 'C.<lambda>')

if __name__ == '__main__': unittest.main()
