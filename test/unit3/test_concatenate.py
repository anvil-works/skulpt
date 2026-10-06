# CPython 3.14 Lib/test/test_typing.py at 18ef0f0cb52.
# Five complete ConcatenateTests methods unchanged. Harness subTest is adapted for Skulpt.
import unittest
import collections.abc
from typing import Callable, Concatenate, ParamSpec, TypeVar, Union, get_args, get_origin
from test_type_parameters import SubTest

class ConcatenateTests(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()

    def test_basics(self):
        P = ParamSpec('P')
        class MyClass: ...
        c = Concatenate[MyClass, P]
        self.assertNotEqual(c, Concatenate)

    def test_dir(self):
        P = ParamSpec('P')
        dir_items = set(dir(Concatenate[int, P]))
        for required_item in [
            '__args__', '__parameters__', '__origin__',
        ]:
            with self.subTest(required_item=required_item):
                self.assertIn(required_item, dir_items)

    def test_invalid_uses(self):
        with self.assertRaisesRegex(TypeError, 'Concatenate of no types'):
            Concatenate[()]
        with self.assertRaisesRegex(
            TypeError,
            (
                'The last parameter to Concatenate should be a '
                'ParamSpec variable or ellipsis'
            ),
        ):
            Concatenate[int]

    def test_var_substitution(self):
        T = TypeVar('T')
        P = ParamSpec('P')
        P2 = ParamSpec('P2')
        C = Concatenate[T, P]
        self.assertEqual(C[int, P2], Concatenate[int, P2])
        self.assertEqual(C[int, [str, float]], (int, str, float))
        self.assertEqual(C[int, []], (int,))
        self.assertEqual(C[int, Concatenate[str, P2]],
                         Concatenate[int, str, P2])
        self.assertEqual(C[int, ...], Concatenate[int, ...])

        C = Concatenate[int, P]
        self.assertEqual(C[P2], Concatenate[int, P2])
        self.assertEqual(C[[str, float]], (int, str, float))
        self.assertEqual(C[str, float], (int, str, float))
        self.assertEqual(C[[]], (int,))
        self.assertEqual(C[Concatenate[str, P2]], Concatenate[int, str, P2])
        self.assertEqual(C[...], Concatenate[int, ...])


    def test_valid_uses(self):
        P = ParamSpec('P')
        T = TypeVar('T')
        C1 = Callable[Concatenate[int, P], int]
        self.assertEqual(C1.__args__, (Concatenate[int, P], int))
        self.assertEqual(C1.__parameters__, (P,))
        C2 = Callable[Concatenate[int, T, P], T]
        self.assertEqual(C2.__args__, (Concatenate[int, T, P], T))
        self.assertEqual(C2.__parameters__, (T, P))

        # Test collections.abc.Callable too.
        C3 = collections.abc.Callable[Concatenate[int, P], int]
        self.assertEqual(C3.__args__, (Concatenate[int, P], int))
        self.assertEqual(C3.__parameters__, (P,))
        C4 = collections.abc.Callable[Concatenate[int, T, P], T]
        self.assertEqual(C4.__args__, (Concatenate[int, T, P], T))
        self.assertEqual(C4.__parameters__, (T, P))


class ConcatenateRegressions(unittest.TestCase):
    def test_compiler_parameters_and_checked_unions(self):
        class C[**P]: pass
        P, = C.__type_params__
        alias = Concatenate[int, P]
        self.assertIs(alias, Concatenate[int, P])
        self.assertIs(get_origin(alias), Concatenate)
        self.assertEqual(get_args(alias), (int, P))
        self.assertEqual(C[alias].__args__, (alias,))
        type Signature[**Q] = Concatenate[str, Q]
        self.assertEqual(Signature.__value__[[int, float]], (str, int, float))
        for operation in (lambda: Concatenate(), lambda: isinstance(1, Concatenate),
                          lambda: issubclass(int, Concatenate), lambda: iter(Concatenate),
                          lambda: Union[Concatenate, int]):
            with self.assertRaises(TypeError): operation()
        self.assertEqual((alias | int).__args__, (alias, int))
        events = []
        with self.assertRaisesRegex(TypeError, "Cannot subclass typing.Concatenate"):
            class Invalid(alias):
                events.append('body')
        self.assertEqual(events, [])

if __name__ == '__main__': unittest.main()
