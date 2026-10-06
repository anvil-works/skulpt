# CPython 3.14 Lib/test/test_typing.py at 18ef0f0cb52.
# Eighteen complete BaseCallableTests methods unchanged, run against both aliases.
# Type-hint evaluation, weakref and pickle methods follow with their corresponding runtime facilities.
import unittest
import typing
import collections.abc
import types
from typing import Callable, Generic, TypeVar, ParamSpec, TypeVarTuple, Concatenate, Any, NoReturn, Tuple, Union
from test_type_parameters import SubTest
T = TypeVar('T')
KT = TypeVar('KT')
VT = TypeVar('VT')

class BaseCallableTests:

    def test_self_subclass(self):
        Callable = self.Callable
        with self.assertRaises(TypeError):
            issubclass(types.FunctionType, Callable[[int], int])
        self.assertIsSubclass(types.FunctionType, Callable)
        self.assertIsSubclass(Callable, Callable)

    def test_eq_hash(self):
        Callable = self.Callable
        C = Callable[[int], int]
        self.assertEqual(C, Callable[[int], int])
        self.assertEqual(len({C, Callable[[int], int]}), 1)
        self.assertNotEqual(C, Callable[[int], str])
        self.assertNotEqual(C, Callable[[str], int])
        self.assertNotEqual(C, Callable[[int, int], int])
        self.assertNotEqual(C, Callable[[], int])
        self.assertNotEqual(C, Callable[..., int])
        self.assertNotEqual(C, Callable)

    def test_dir(self):
        Callable = self.Callable
        dir_items = set(dir(Callable[..., int]))
        for required_item in [
            '__args__', '__parameters__', '__origin__',
        ]:
            with self.subTest(required_item=required_item):
                self.assertIn(required_item, dir_items)

    def test_cannot_instantiate(self):
        Callable = self.Callable
        with self.assertRaises(TypeError):
            Callable()
        with self.assertRaises(TypeError):
            type(Callable)()
        c = Callable[[int], str]
        with self.assertRaises(TypeError):
            c()
        with self.assertRaises(TypeError):
            type(c)()

    def test_callable_wrong_forms(self):
        Callable = self.Callable
        with self.assertRaises(TypeError):
            Callable[int]

    def test_callable_instance_works(self):
        Callable = self.Callable
        def f():
            pass
        self.assertIsInstance(f, Callable)
        self.assertNotIsInstance(None, Callable)

    def test_callable_instance_type_error(self):
        Callable = self.Callable
        def f():
            pass
        with self.assertRaises(TypeError):
            isinstance(f, Callable[[], None])
        with self.assertRaises(TypeError):
            isinstance(f, Callable[[], Any])
        with self.assertRaises(TypeError):
            isinstance(None, Callable[[], None])
        with self.assertRaises(TypeError):
            isinstance(None, Callable[[], Any])

    def test_repr(self):
        Callable = self.Callable
        fullname = f'{Callable.__module__}.Callable'
        ct0 = Callable[[], bool]
        self.assertEqual(repr(ct0), f'{fullname}[[], bool]')
        ct2 = Callable[[str, float], int]
        self.assertEqual(repr(ct2), f'{fullname}[[str, float], int]')
        ctv = Callable[..., str]
        self.assertEqual(repr(ctv), f'{fullname}[..., str]')
        ct3 = Callable[[str, float], list[int]]
        self.assertEqual(repr(ct3), f'{fullname}[[str, float], list[int]]')


    def test_ellipsis_in_generic(self):
        Callable = self.Callable
        # Shouldn't crash; see https://github.com/python/typing/issues/259
        typing.List[Callable[..., str]]

    def test_or_and_ror(self):
        Callable = self.Callable
        self.assertEqual(Callable | Tuple, Union[Callable, Tuple])
        self.assertEqual(Tuple | Callable, Union[Tuple, Callable])

    def test_basic(self):
        Callable = self.Callable
        alias = Callable[[int, str], float]
        if Callable is collections.abc.Callable:
            self.assertIsInstance(alias, types.GenericAlias)
        self.assertIs(alias.__origin__, collections.abc.Callable)
        self.assertEqual(alias.__args__, (int, str, float))
        self.assertEqual(alias.__parameters__, ())

    def test_var_substitution(self):
        Callable = self.Callable
        fullname = f"{Callable.__module__}.Callable"
        C1 = Callable[[int, T], T]
        C2 = Callable[[KT, T], VT]
        C3 = Callable[..., T]
        self.assertEqual(C1[str], Callable[[int, str], str])
        self.assertEqual(C1[None], Callable[[int, type(None)], type(None)])
        self.assertEqual(C2[int, float, str], Callable[[int, float], str])
        self.assertEqual(C3[int], Callable[..., int])
        self.assertEqual(C3[NoReturn], Callable[..., NoReturn])

        # multi chaining
        C4 = C2[int, VT, str]
        self.assertEqual(repr(C4), f"{fullname}[[int, ~VT], str]")
        self.assertEqual(repr(C4[dict]), f"{fullname}[[int, dict], str]")
        self.assertEqual(C4[dict], Callable[[int, dict], str])

        # substitute a nested GenericAlias (both typing and the builtin
        # version)
        C5 = Callable[[typing.List[T], tuple[KT, T], VT], int]
        self.assertEqual(C5[int, str, float],
                         Callable[[typing.List[int], tuple[str, int], float], int])

    def test_type_subst_error(self):
        Callable = self.Callable
        P = ParamSpec('P')
        T = TypeVar('T')

        pat = "Expected a list of types, an ellipsis, ParamSpec, or Concatenate."

        with self.assertRaisesRegex(TypeError, pat):
            Callable[P, T][0, int]

    def test_type_erasure(self):
        Callable = self.Callable
        class C1(Callable):
            def __call__(self):
                return None
        a = C1[[int], T]
        self.assertIs(a().__class__, C1)
        self.assertEqual(a().__orig_class__, C1[[int], T])

    def test_paramspec(self):
        Callable = self.Callable
        fullname = f"{Callable.__module__}.Callable"
        P = ParamSpec('P')
        P2 = ParamSpec('P2')
        C1 = Callable[P, T]
        # substitution
        self.assertEqual(C1[[int], str], Callable[[int], str])
        self.assertEqual(C1[[int, str], str], Callable[[int, str], str])
        self.assertEqual(C1[[], str], Callable[[], str])
        self.assertEqual(C1[..., str], Callable[..., str])
        self.assertEqual(C1[P2, str], Callable[P2, str])
        self.assertEqual(C1[Concatenate[int, P2], str],
                         Callable[Concatenate[int, P2], str])
        self.assertEqual(repr(C1), f"{fullname}[~P, ~T]")
        self.assertEqual(repr(C1[[int, str], str]), f"{fullname}[[int, str], str]")
        with self.assertRaises(TypeError):
            C1[int, str]

        C2 = Callable[P, int]
        self.assertEqual(C2[[int]], Callable[[int], int])
        self.assertEqual(C2[[int, str]], Callable[[int, str], int])
        self.assertEqual(C2[[]], Callable[[], int])
        self.assertEqual(C2[...], Callable[..., int])
        self.assertEqual(C2[P2], Callable[P2, int])
        self.assertEqual(C2[Concatenate[int, P2]],
                         Callable[Concatenate[int, P2], int])
        # special case in PEP 612 where
        # X[int, str, float] == X[[int, str, float]]
        self.assertEqual(C2[int], Callable[[int], int])
        self.assertEqual(C2[int, str], Callable[[int, str], int])
        self.assertEqual(repr(C2), f"{fullname}[~P, int]")
        self.assertEqual(repr(C2[int, str]), f"{fullname}[[int, str], int]")

    def test_concatenate(self):
        Callable = self.Callable
        fullname = f"{Callable.__module__}.Callable"
        T = TypeVar('T')
        P = ParamSpec('P')
        P2 = ParamSpec('P2')
        C = Callable[Concatenate[int, P], T]
        self.assertEqual(repr(C),
                         f"{fullname}[typing.Concatenate[int, ~P], ~T]")
        self.assertEqual(C[P2, int], Callable[Concatenate[int, P2], int])
        self.assertEqual(C[[str, float], int], Callable[[int, str, float], int])
        self.assertEqual(C[[], int], Callable[[int], int])
        self.assertEqual(C[Concatenate[str, P2], int],
                         Callable[Concatenate[int, str, P2], int])
        self.assertEqual(C[..., int], Callable[Concatenate[int, ...], int])

        C = Callable[Concatenate[int, P], int]
        self.assertEqual(repr(C),
                         f"{fullname}[typing.Concatenate[int, ~P], int]")
        self.assertEqual(C[P2], Callable[Concatenate[int, P2], int])
        self.assertEqual(C[[str, float]], Callable[[int, str, float], int])
        self.assertEqual(C[str, float], Callable[[int, str, float], int])
        self.assertEqual(C[[]], Callable[[int], int])
        self.assertEqual(C[Concatenate[str, P2]],
                         Callable[Concatenate[int, str, P2], int])
        self.assertEqual(C[...], Callable[Concatenate[int, ...], int])

    def test_nested_paramspec(self):
        # Since Callable has some special treatment, we want to be sure
        # that substitution works correctly, see gh-103054
        Callable = self.Callable
        P = ParamSpec('P')
        P2 = ParamSpec('P2')
        T = TypeVar('T')
        T2 = TypeVar('T2')
        Ts = TypeVarTuple('Ts')
        class My(Generic[P, T]):
            pass

        self.assertEqual(My.__parameters__, (P, T))

        C1 = My[[int, T2], Callable[P2, T2]]
        self.assertEqual(C1.__args__, ((int, T2), Callable[P2, T2]))
        self.assertEqual(C1.__parameters__, (T2, P2))
        self.assertEqual(C1[str, [list[int], bytes]],
                         My[[int, str], Callable[[list[int], bytes], str]])

        C2 = My[[Callable[[T2], int], list[T2]], str]
        self.assertEqual(C2.__args__, ((Callable[[T2], int], list[T2]), str))
        self.assertEqual(C2.__parameters__, (T2,))
        self.assertEqual(C2[list[str]],
                         My[[Callable[[list[str]], int], list[list[str]]], str])

        C3 = My[[Callable[P2, T2], T2], T2]
        self.assertEqual(C3.__args__, ((Callable[P2, T2], T2), T2))
        self.assertEqual(C3.__parameters__, (P2, T2))
        self.assertEqual(C3[[], int],
                         My[[Callable[[], int], int], int])
        self.assertEqual(C3[[str, bool], int],
                         My[[Callable[[str, bool], int], int], int])
        self.assertEqual(C3[[str, bool], T][int],
                         My[[Callable[[str, bool], int], int], int])

        C4 = My[[Callable[[int, *Ts, str], T2], T2], T2]
        self.assertEqual(C4.__args__, ((Callable[[int, *Ts, str], T2], T2), T2))
        self.assertEqual(C4.__parameters__, (Ts, T2))
        self.assertEqual(C4[bool, bytes, float],
                         My[[Callable[[int, bool, bytes, str], float], float], float])

    def test_errors(self):
        Callable = self.Callable
        alias = Callable[[int, str], float]
        with self.assertRaisesRegex(TypeError, "is not a generic class"):
            alias[int]
        P = ParamSpec('P')
        C1 = Callable[P, T]
        with self.assertRaisesRegex(TypeError, "many arguments for"):
            C1[int, str, str]
        with self.assertRaisesRegex(TypeError, "few arguments for"):
            C1[int]


class Harness(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def assertIsSubclass(self, cls, base): self.assertTrue(issubclass(cls, base))
    def assertNotIsSubclass(self, cls, base): self.assertFalse(issubclass(cls, base))

class TypingCallableTests(BaseCallableTests, Harness):
    Callable = typing.Callable
    def test_consistency(self):
        # bpo-42195
        # Testing collections.abc.Callable's consistency with typing.Callable
        c1 = typing.Callable[[int, str], dict]
        c2 = collections.abc.Callable[[int, str], dict]
        self.assertEqual(c1.__args__, c2.__args__)
        self.assertEqual(hash(c1.__args__), hash(c2.__args__))


class CollectionsCallableTests(BaseCallableTests, Harness):
    Callable = collections.abc.Callable


class CallableCompilerRegressions(unittest.TestCase):
    def test_lazy_callable_alias_and_cached_mutable_metadata(self):
        type Signature[**P, T=int] = Callable[Concatenate[str, P], T]
        concrete = Signature.__value__[[float], bytes]
        self.assertEqual(concrete, Callable[[str, float], bytes])
        self.assertEqual(typing.get_args(concrete), ([str, float], bytes))
        self.assertIs(typing.get_origin(Callable), collections.abc.Callable)
        alias = Callable[[int], str]
        self.assertIs(alias, Callable[[int], str])
        original_args = alias.__args__
        try:
            alias.__args__ = (float, bytes)
            self.assertEqual(typing.get_args(Callable[[int], str]), ([float], bytes))
            self.assertEqual(typing.get_args(collections.abc.Callable[[int], str]), ([int], str))
        finally:
            alias.__args__ = original_args

if __name__ == '__main__': unittest.main()
