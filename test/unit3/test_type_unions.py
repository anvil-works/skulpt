# CPython 3.14 Lib/test/test_types.py at 18ef0f0cb52.
# Five upstream methods unchanged; the final methods select non-typing cases
# from the same suite until the typing library is implemented.
import unittest
import types
class SubTest:
    def __enter__(self): return self
    def __exit__(self, *args): return False
class UnionTests(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def assertIsSubclass(self, cls, superclass):
        self.assertTrue(issubclass(cls, superclass))
    def assertNotIsSubclass(self, cls, superclass):
        self.assertFalse(issubclass(cls, superclass))

    def test_union_of_unhashable(self):
        class UnhashableMeta(type):
            __hash__ = None

        class A(metaclass=UnhashableMeta): ...
        class B(metaclass=UnhashableMeta): ...

        self.assertEqual((A | B).__args__, (A, B))
        union1 = A | B
        with self.assertRaisesRegex(TypeError, "unhashable type: 'UnhashableMeta'"):
            hash(union1)

        union2 = int | B
        with self.assertRaisesRegex(TypeError, "unhashable type: 'UnhashableMeta'"):
            hash(union2)

        union3 = A | int
        with self.assertRaisesRegex(TypeError, "unhashable type: 'UnhashableMeta'"):
            hash(union3)

    def test_unhashable_becomes_hashable(self):
        is_hashable = False
        class UnhashableMeta(type):
            def __hash__(self):
                if is_hashable:
                    return 1
                else:
                    raise TypeError("not hashable")

        class A(metaclass=UnhashableMeta): ...
        class B(metaclass=UnhashableMeta): ...

        union = A | B
        self.assertEqual(union.__args__, (A, B))

        with self.assertRaisesRegex(TypeError, "not hashable"):
            hash(union)

        is_hashable = True

        with self.assertRaisesRegex(TypeError, "union contains 2 unhashable elements"):
            hash(union)

    def test_bad_instancecheck(self):
        class BadMeta(type):
            def __instancecheck__(cls, inst):
                1/0
        x = int | BadMeta('A', (), {})
        self.assertTrue(isinstance(1, x))
        self.assertRaises(ZeroDivisionError, isinstance, [], x)

    def test_bad_subclasscheck(self):
        class BadMeta(type):
            def __subclasscheck__(cls, sub):
                1/0
        x = int | BadMeta('A', (), {})
        self.assertIsSubclass(int, x)
        self.assertRaises(ZeroDivisionError, issubclass, list, x)

    def test_or_type_operator_with_bad_module(self):
        class BadMeta(type):
            __qualname__ = 'TypeVar'
            @property
            def __module__(self):
                1 / 0
        TypeVar = BadMeta('TypeVar', (), {})
        _SpecialForm = BadMeta('_SpecialForm', (), {})
        # Crashes in Issue44483
        with self.assertRaises((TypeError, ZeroDivisionError)):
            str | TypeVar()
        with self.assertRaises((TypeError, ZeroDivisionError)):
            str | _SpecialForm()

    def test_union_operator_and_arguments(self):
        self.assertIs(int | int, int)
        for union, expected in (
            (int | str, (int, str)),
            ((int | str) | list, (int, str, list)),
            (int | (str | list), (int, str, list)),
            ((str | int) | (int | list), (str, int, list)),
            (int | None, (int, type(None))),
            (None | int, (type(None), int)),
            (list[int] | int | list[int], (list[int], int)),
        ):
            self.assertEqual(union.__args__, expected)
            self.assertEqual(union.__parameters__, ())
            self.assertIs(type(union), types.UnionType)
            self.assertIs(union.__origin__, types.UnionType)
            self.assertEqual(union.__name__, 'Union')
            with self.assertRaises(TypeError): union[int]
            with self.assertRaises(AttributeError): union.__args__ = ()
        self.assertEqual(int | str, str | int)
        self.assertEqual(hash(int | str), hash(str | int))
        self.assertNotEqual(int | str, int | list)
        self.assertNotEqual(int | str, {})
        self.assertEqual(repr(int | None), "int | None")
        self.assertEqual(repr(int | list[int]), "int | list[int]")
        self.assertEqual(repr(list[int] | list[str]), "list[int] | list[str]")
        for source in ('int | 3', '3 | int', '(int | str) < (int | str)'):
            with self.assertRaises(TypeError): eval(source)
        self.assertIs(types.UnionType[int], int)
        self.assertIs(types.UnionType[int, int], int)
        self.assertIs(types.UnionType[None], type(None))
        self.assertEqual(types.UnionType[int, str], int | str)
        self.assertIs(types.UnionType[42], 42)
        self.assertEqual(((int | str) | 42).__args__, (int, str, 42))
        with self.assertRaises(TypeError): types.UnionType[()]
        with self.assertRaises(TypeError): (int | str) | ()
        with self.assertRaises(TypeError): types.UnionType()
        with self.assertRaises(TypeError):
            class SubUnion(types.UnionType): pass

    def test_instance_and_subclass_order(self):
        union = int | str
        for value in (1, True, 'a'): self.assertIsInstance(value, union)
        self.assertNotIsInstance(None, union)
        for cls in (int, bool, str): self.assertIsSubclass(cls, union)
        self.assertNotIsSubclass(type(None), union)
        self.assertIsInstance(None, int | None)
        self.assertIsSubclass(type(None), int | None)
        self.assertIsInstance(1, int | list[int])
        self.assertIsSubclass(int, int | list[int])
        for union in (list[int] | int, list[int] | str):
            with self.assertRaises(TypeError): isinstance(1, union)
            with self.assertRaises(TypeError): issubclass(int, union)
        with self.assertRaises(TypeError): isinstance([], int | list[int])
        with self.assertRaises(TypeError): issubclass(list, int | list[int])
        self.assertTrue(isinstance(1, (int | str, list[int])))

    def test_metaclass_operator_and_comparison(self):
        class Meta(type):
            def __or__(cls, other): return 'custom left'
            def __ror__(cls, other): return 'custom right'
        class A(metaclass=Meta): pass
        self.assertEqual(A | int, 'custom left')
        self.assertEqual(int | A, 'custom right')
        class BadType(type):
            def __eq__(self, other): return 1 / 0
        bt = BadType('bt', (), {})
        bt2 = BadType('bt2', (), {})
        with self.assertRaises(ZeroDivisionError): bt | bt2
        with self.assertRaises(ZeroDivisionError): (int | bt) == (int | bt2)

    def test_stored_hashes_and_class_parameters(self):
        hashes = []
        enabled = True
        class Meta(type):
            def __hash__(cls):
                if not enabled: raise ValueError('hash disabled')
                hashes.append(cls)
                if len(hashes) > 3: raise ValueError('rehashed')
                return 123
            @property
            def __parameters__(cls): raise ValueError('class parameters queried')
        class A(metaclass=Meta): pass
        union = A | int
        self.assertEqual(hashes, [A, A, A])
        self.assertEqual(union.__parameters__, ())
        enabled = False
        self.assertEqual(hash(union), hash(union))
        self.assertEqual(union, union)
        # Independent unions still compare using their stored entry hashes.
        enabled = True
        hashes.clear()
        other = int | A
        enabled = False
        self.assertEqual(union, other)
        self.assertEqual(hash(union), hash(other))

if __name__ == '__main__': unittest.main()
