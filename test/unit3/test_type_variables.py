# CPython 3.14 Lib/test/test_typing.py at 18ef0f0cb52.
# Nineteen upstream method bodies unchanged; focused parameter tests below.
import unittest
import typing
from typing import TypeVar, NoDefault, Union, get_args
T = TypeVar('T')
NOT_A_BASE_TYPE = "type 'typing.%s' is not an acceptable base type"
CANNOT_SUBCLASS_INSTANCE = "Cannot subclass an instance of %s"
class TypeVarTests(unittest.TestCase):

    def test_basic_plain(self):
        T = TypeVar('T')
        # T equals itself.
        self.assertEqual(T, T)
        # T is an instance of TypeVar
        self.assertIsInstance(T, TypeVar)
        self.assertEqual(T.__name__, 'T')
        self.assertEqual(T.__constraints__, ())
        self.assertIs(T.__bound__, None)
        self.assertIs(T.__covariant__, False)
        self.assertIs(T.__contravariant__, False)
        self.assertIs(T.__infer_variance__, False)
        self.assertEqual(T.__module__, __name__)

    def test_basic_with_exec(self):
        ns = {}
        exec('from typing import TypeVar; T = TypeVar("T", bound=float)', ns, ns)
        T = ns['T']
        self.assertIsInstance(T, TypeVar)
        self.assertEqual(T.__name__, 'T')
        self.assertEqual(T.__constraints__, ())
        self.assertIs(T.__bound__, float)
        self.assertIs(T.__covariant__, False)
        self.assertIs(T.__contravariant__, False)
        self.assertIs(T.__infer_variance__, False)
        self.assertIs(T.__module__, None)

    def test_attributes(self):
        T_bound = TypeVar('T_bound', bound=int)
        self.assertEqual(T_bound.__name__, 'T_bound')
        self.assertEqual(T_bound.__constraints__, ())
        self.assertIs(T_bound.__bound__, int)

        T_constraints = TypeVar('T_constraints', int, str)
        self.assertEqual(T_constraints.__name__, 'T_constraints')
        self.assertEqual(T_constraints.__constraints__, (int, str))
        self.assertIs(T_constraints.__bound__, None)

        T_co = TypeVar('T_co', covariant=True)
        self.assertEqual(T_co.__name__, 'T_co')
        self.assertIs(T_co.__covariant__, True)
        self.assertIs(T_co.__contravariant__, False)
        self.assertIs(T_co.__infer_variance__, False)

        T_contra = TypeVar('T_contra', contravariant=True)
        self.assertEqual(T_contra.__name__, 'T_contra')
        self.assertIs(T_contra.__covariant__, False)
        self.assertIs(T_contra.__contravariant__, True)
        self.assertIs(T_contra.__infer_variance__, False)

        T_infer = TypeVar('T_infer', infer_variance=True)
        self.assertEqual(T_infer.__name__, 'T_infer')
        self.assertIs(T_infer.__covariant__, False)
        self.assertIs(T_infer.__contravariant__, False)
        self.assertIs(T_infer.__infer_variance__, True)

    def test_typevar_instance_type_error(self):
        T = TypeVar('T')
        with self.assertRaises(TypeError):
            isinstance(42, T)

    def test_typevar_subclass_type_error(self):
        T = TypeVar('T')
        with self.assertRaises(TypeError):
            issubclass(int, T)
        with self.assertRaises(TypeError):
            issubclass(T, int)

    def test_constrained_error(self):
        with self.assertRaises(TypeError):
            X = TypeVar('X', int)
            X

    def test_no_redefinition(self):
        self.assertNotEqual(TypeVar('T'), TypeVar('T'))
        self.assertNotEqual(TypeVar('T', int, str), TypeVar('T', int, str))

    def test_cannot_subclass(self):
        with self.assertRaisesRegex(TypeError, NOT_A_BASE_TYPE % 'TypeVar'):
            class V(TypeVar): pass
        T = TypeVar("T")
        with self.assertRaisesRegex(TypeError,
                CANNOT_SUBCLASS_INSTANCE % 'TypeVar'):
            class W(T): pass

    def test_cannot_instantiate_vars(self):
        with self.assertRaises(TypeError):
            TypeVar('A')()

    def test_missing__name__(self):
        # See bpo-39942
        code = ("import typing\n"
                "T = typing.TypeVar('T')\n"
                )
        exec(code, {})

    def test_no_bivariant(self):
        with self.assertRaises(ValueError):
            TypeVar('T', covariant=True, contravariant=True)

    def test_cannot_combine_explicit_and_infer(self):
        with self.assertRaises(ValueError):
            TypeVar('T', covariant=True, infer_variance=True)
        with self.assertRaises(ValueError):
            TypeVar('T', contravariant=True, infer_variance=True)

    def test_constructor(self):
        T = TypeVar(name="T")
        self.assertEqual(T.__name__, "T")
        self.assertEqual(T.__constraints__, ())
        self.assertIs(T.__bound__, None)
        self.assertIs(T.__default__, typing.NoDefault)
        self.assertIs(T.__covariant__, False)
        self.assertIs(T.__contravariant__, False)
        self.assertIs(T.__infer_variance__, False)

        T = TypeVar(name="T", bound=type)
        self.assertEqual(T.__name__, "T")
        self.assertEqual(T.__constraints__, ())
        self.assertIs(T.__bound__, type)
        self.assertIs(T.__default__, typing.NoDefault)
        self.assertIs(T.__covariant__, False)
        self.assertIs(T.__contravariant__, False)
        self.assertIs(T.__infer_variance__, False)

        T = TypeVar(name="T", default=())
        self.assertEqual(T.__name__, "T")
        self.assertEqual(T.__constraints__, ())
        self.assertIs(T.__bound__, None)
        self.assertIs(T.__default__, ())
        self.assertIs(T.__covariant__, False)
        self.assertIs(T.__contravariant__, False)
        self.assertIs(T.__infer_variance__, False)

        T = TypeVar(name="T", covariant=True)
        self.assertEqual(T.__name__, "T")
        self.assertEqual(T.__constraints__, ())
        self.assertIs(T.__bound__, None)
        self.assertIs(T.__default__, typing.NoDefault)
        self.assertIs(T.__covariant__, True)
        self.assertIs(T.__contravariant__, False)
        self.assertIs(T.__infer_variance__, False)

        T = TypeVar(name="T", contravariant=True)
        self.assertEqual(T.__name__, "T")
        self.assertEqual(T.__constraints__, ())
        self.assertIs(T.__bound__, None)
        self.assertIs(T.__default__, typing.NoDefault)
        self.assertIs(T.__covariant__, False)
        self.assertIs(T.__contravariant__, True)
        self.assertIs(T.__infer_variance__, False)

        T = TypeVar(name="T", infer_variance=True)
        self.assertEqual(T.__name__, "T")
        self.assertEqual(T.__constraints__, ())
        self.assertIs(T.__bound__, None)
        self.assertIs(T.__default__, typing.NoDefault)
        self.assertIs(T.__covariant__, False)
        self.assertIs(T.__contravariant__, False)
        self.assertIs(T.__infer_variance__, True)

    def test_defaults_and_evaluators(self):
        T = TypeVar('T')
        self.assertIs(T.__default__, NoDefault)
        self.assertFalse(T.has_default())
        self.assertIs(T.evaluate_bound, None)
        self.assertIs(T.evaluate_constraints, None)
        self.assertIs(T.evaluate_default(1), NoDefault)
        self.assertEqual(repr(NoDefault), 'typing.NoDefault')
        self.assertIs(type(NoDefault)(), NoDefault)
        with self.assertRaises(TypeError): type(NoDefault)(1)
        T = TypeVar('T', bound=int, default=None)
        self.assertTrue(T.has_default())
        self.assertIs(T.__default__, None)
        self.assertIs(T.evaluate_bound(1), int)
        self.assertEqual(T.evaluate_bound(4), 'int')
        self.assertIs(T.evaluate_default(1), None)
        T = TypeVar('T', int, str, default=float)
        self.assertEqual(T.evaluate_constraints(1), (int, str))
        self.assertEqual(T.evaluate_constraints(4), '(int, str)')
        self.assertIs(T.evaluate_default(1), float)
        T.extra = 'custom'
        T.__module__ = 'other'
        self.assertEqual(T.extra, 'custom')
        with self.assertRaises(AttributeError): T.__dict__
        self.assertEqual(T.__module__, 'other')
        for name in ('__name__', '__bound__', '__constraints__', '__default__', '__covariant__'):
            with self.assertRaises(AttributeError): setattr(T, name, None)

    def test_generic_and_union_substitution(self):
        T, S = TypeVar('T'), TypeVar('S', default=int)
        self.assertEqual(list[T].__parameters__, (T,))
        self.assertEqual(dict[T, list[S]].__parameters__, (T, S))
        self.assertEqual(dict[T, list[S]][str], dict[str, list[int]])
        self.assertEqual(dict[T, list[S]][str, float], dict[str, list[float]])
        self.assertEqual(dict[T, T][int], dict[int, int])
        self.assertEqual(list[T][None], list[type(None)])
        self.assertEqual((int | T).__parameters__, (T,))
        self.assertIs((int | T)[int], int)
        self.assertEqual((list[T] | list[S])[str], list[str] | list[int])
        self.assertEqual((T | int)[str], str | int)
        self.assertTrue(isinstance(1, int | T))
        self.assertTrue(issubclass(int, int | T))
        with self.assertRaises(TypeError): isinstance(1, T | int)
        with self.assertRaises(TypeError): issubclass(int, T | int)
        for source in ('list[T][int, str]', 'dict[T, S][()]', 'list[T][(int, str),]', 'list[int][str]'):
            with self.assertRaises(TypeError): eval(source)


    def test_preparation_hooks_and_list_subclass_iteration(self):
        from types import GenericAlias
        T = TypeVar('T')
        with self.assertRaises(ValueError): T.__typing_prepare_subst__(list[int], ())
        calls = []
        class Parameter:
            def __init__(self, first): self.first = first
            def __typing_prepare_subst__(self, alias, args):
                calls.append(args)
                if self.first: return int
                self_arg, = args
                return self_arg, str
            def __typing_subst__(self, arg): return arg
        first, second = Parameter(True), Parameter(False)
        alias = GenericAlias(list, (first, second))
        self.assertEqual(alias[float], list[int, str])
        self.assertEqual(calls, [(float,), (int,)])
        class BadList(list):
            def __iter__(self): raise ValueError('list iteration')
        alias = GenericAlias(list, (BadList([T]),))
        with self.assertRaises(ValueError): alias.__parameters__
        class LiveList(list):
            def __iter__(self): return iter(self.current)
        values = LiveList([T])
        values.current = [T]
        alias = GenericAlias(list, (values,))
        self.assertEqual(alias.__parameters__, (T,))
        values.current = [int]
        self.assertEqual(alias[str].__args__, ([int],))


class TypeVarUnionTests(unittest.TestCase):

    def test_union_unique(self):
        X = TypeVar('X')
        Y = TypeVar('Y')
        self.assertNotEqual(X, Y)
        self.assertEqual(Union[X], X)
        self.assertNotEqual(Union[X], Union[X, Y])
        self.assertEqual(Union[X, X], X)
        self.assertNotEqual(Union[X, int], Union[X])
        self.assertNotEqual(Union[X, int], Union[int])
        self.assertEqual(Union[X, int].__args__, (X, int))
        self.assertEqual(Union[X, int].__parameters__, (X,))
        self.assertIs(Union[X, int].__origin__, Union)

    def test_union_constrained(self):
        A = TypeVar('A', str, bytes)
        self.assertNotEqual(Union[A, str], Union[A])

class UnionParameterTests(unittest.TestCase):

    def test_union_parameter_chaining(self):
        T = typing.TypeVar("T")
        S = typing.TypeVar("S")

        self.assertEqual((float | list[T])[int], float | list[int])
        self.assertEqual(list[int | list[T]].__parameters__, (T,))
        self.assertEqual(list[int | list[T]][str], list[int | list[str]])
        self.assertEqual((list[T] | list[S]).__parameters__, (T, S))
        self.assertEqual((list[T] | list[S])[int, T], list[int] | list[T])
        self.assertEqual((list[T] | list[S])[int, int], list[int])

    def test_union_parameter_substitution_errors(self):
        T = typing.TypeVar("T")
        x = int | T
        with self.assertRaises(TypeError):
            x[int, str]

class GenericAliasParameterTests(unittest.TestCase):

    def test_union(self):
        a = typing.Union[list[int], list[str]]
        self.assertEqual(a.__args__, (list[int], list[str]))
        self.assertEqual(a.__parameters__, ())

    def test_union_generic(self):
        a = typing.Union[list[T], tuple[T, ...]]
        self.assertEqual(a.__args__, (list[T], tuple[T, ...]))
        self.assertEqual(a.__parameters__, (T,))
if __name__ == '__main__': unittest.main()
