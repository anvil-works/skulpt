# CPython 3.14 Lib/test/test_typing.py and test_type_params.py at 18ef0f0cb52.
# Twenty-three upstream method bodies unchanged.
import unittest
import textwrap
NOT_A_BASE_TYPE = "type 'typing.%s' is not an acceptable base type"
CANNOT_SUBCLASS_INSTANCE = "Cannot subclass an instance of %s"
from typing import TypeVar, TypeVarTuple, ParamSpec, ParamSpecArgs, ParamSpecKwargs, Unpack, NoDefault
from test_type_parameters import run_code, check_syntax_error

class TypeVarTupleTests(unittest.TestCase):
    def test_name(self):
        Ts = TypeVarTuple('Ts')
        self.assertEqual(Ts.__name__, 'Ts')
        Ts2 = TypeVarTuple('Ts2')
        self.assertEqual(Ts2.__name__, 'Ts2')


    def test_module(self):
        Ts = TypeVarTuple('Ts')
        self.assertEqual(Ts.__module__, __name__)


    def test_exec(self):
        ns = {}
        exec('from typing import TypeVarTuple; Ts = TypeVarTuple("Ts")', ns)
        Ts = ns['Ts']
        self.assertEqual(Ts.__name__, 'Ts')
        self.assertIs(Ts.__module__, None)


    def test_instance_is_equal_to_itself(self):
        Ts = TypeVarTuple('Ts')
        self.assertEqual(Ts, Ts)


    def test_different_instances_are_different(self):
        self.assertNotEqual(TypeVarTuple('Ts'), TypeVarTuple('Ts'))


    def test_instance_isinstance_of_typevartuple(self):
        Ts = TypeVarTuple('Ts')
        self.assertIsInstance(Ts, TypeVarTuple)


    def test_cannot_call_instance(self):
        Ts = TypeVarTuple('Ts')
        with self.assertRaises(TypeError):
            Ts()


    def test_unpacked_typevartuple_is_equal_to_itself(self):
        Ts = TypeVarTuple('Ts')
        self.assertEqual((*Ts,)[0], (*Ts,)[0])
        self.assertEqual(Unpack[Ts], Unpack[Ts])


class ParamSpecTests(unittest.TestCase):
    def test_basic_plain(self):
        P = ParamSpec('P')
        self.assertEqual(P, P)
        self.assertIsInstance(P, ParamSpec)
        self.assertEqual(P.__name__, 'P')
        self.assertEqual(P.__module__, __name__)


    def test_basic_with_exec(self):
        ns = {}
        exec('from typing import ParamSpec; P = ParamSpec("P")', ns, ns)
        P = ns['P']
        self.assertIsInstance(P, ParamSpec)
        self.assertEqual(P.__name__, 'P')
        self.assertIs(P.__module__, None)


    def test_args_kwargs(self):
        P = ParamSpec('P')
        P_2 = ParamSpec('P_2')
        self.assertIn('args', dir(P))
        self.assertIn('kwargs', dir(P))
        self.assertIsInstance(P.args, ParamSpecArgs)
        self.assertIsInstance(P.kwargs, ParamSpecKwargs)
        self.assertIs(P.args.__origin__, P)
        self.assertIs(P.kwargs.__origin__, P)
        self.assertEqual(P.args, P.args)
        self.assertEqual(P.kwargs, P.kwargs)
        self.assertNotEqual(P.args, P_2.args)
        self.assertNotEqual(P.kwargs, P_2.kwargs)
        self.assertNotEqual(P.args, P.kwargs)
        self.assertNotEqual(P.kwargs, P.args)
        self.assertNotEqual(P.args, P_2.kwargs)
        self.assertEqual(repr(P.args), "P.args")
        self.assertEqual(repr(P.kwargs), "P.kwargs")


    def test_paramspec_bound(self):
        P = ParamSpec('P', bound=[int, str])
        self.assertEqual(P.__bound__, [int, str])
        P2 = ParamSpec('P2', bound=(int, str))
        self.assertEqual(P2.__bound__, (int, str))
        obj = object()
        P3 = ParamSpec('P3', bound=obj)
        self.assertIs(P3.__bound__, obj)
        P4 = ParamSpec('P4')
        self.assertIs(P4.__bound__, None)


    def test_cannot_subclass(self):
        with self.assertRaisesRegex(TypeError, NOT_A_BASE_TYPE % 'ParamSpec'):
            class C(ParamSpec): pass
        with self.assertRaisesRegex(TypeError, NOT_A_BASE_TYPE % 'ParamSpecArgs'):
            class D(ParamSpecArgs): pass
        with self.assertRaisesRegex(TypeError, NOT_A_BASE_TYPE % 'ParamSpecKwargs'):
            class E(ParamSpecKwargs): pass
        P = ParamSpec('P')
        with self.assertRaisesRegex(TypeError,
                CANNOT_SUBCLASS_INSTANCE % 'ParamSpec'):
            class F(P): pass
        with self.assertRaisesRegex(TypeError,
                CANNOT_SUBCLASS_INSTANCE % 'ParamSpecArgs'):
            class G(P.args): pass
        with self.assertRaisesRegex(TypeError,
                CANNOT_SUBCLASS_INSTANCE % 'ParamSpecKwargs'):
            class H(P.kwargs): pass


class TypeParamsTypeVarTupleTest(unittest.TestCase):
    def test_typevartuple_01(self):
        code = """def func1[*A: str](): pass"""
        check_syntax_error(self, code, "cannot use bound with TypeVarTuple")
        code = """def func1[*A: (int, str)](): pass"""
        check_syntax_error(self, code, "cannot use constraints with TypeVarTuple")
        code = """class X[*A: str]: pass"""
        check_syntax_error(self, code, "cannot use bound with TypeVarTuple")
        code = """class X[*A: (int, str)]: pass"""
        check_syntax_error(self, code, "cannot use constraints with TypeVarTuple")
        code = """type X[*A: str] = int"""
        check_syntax_error(self, code, "cannot use bound with TypeVarTuple")
        code = """type X[*A: (int, str)] = int"""
        check_syntax_error(self, code, "cannot use constraints with TypeVarTuple")


    def test_typevartuple_02(self):
        def func1[*A]():
            return A

        a = func1()
        self.assertIsInstance(a, TypeVarTuple)


class TypeParamsTypeVarParamSpecTest(unittest.TestCase):
    def test_paramspec_01(self):
        code = """def func1[**A: str](): pass"""
        check_syntax_error(self, code, "cannot use bound with ParamSpec")
        code = """def func1[**A: (int, str)](): pass"""
        check_syntax_error(self, code, "cannot use constraints with ParamSpec")
        code = """class X[**A: str]: pass"""
        check_syntax_error(self, code, "cannot use bound with ParamSpec")
        code = """class X[**A: (int, str)]: pass"""
        check_syntax_error(self, code, "cannot use constraints with ParamSpec")
        code = """type X[**A: str] = int"""
        check_syntax_error(self, code, "cannot use bound with ParamSpec")
        code = """type X[**A: (int, str)] = int"""
        check_syntax_error(self, code, "cannot use constraints with ParamSpec")


    def test_paramspec_02(self):
        def func1[**A]():
            return A

        a = func1()
        self.assertIsInstance(a, ParamSpec)
        self.assertTrue(a.__infer_variance__)
        self.assertFalse(a.__covariant__)
        self.assertFalse(a.__contravariant__)


class DefaultsTest(unittest.TestCase):
    def test_defaults_on_func(self):
        ns = run_code("""
            def func[T=int, **U=float, *V=None]():
                pass
        """)

        T, U, V = ns["func"].__type_params__
        self.assertIs(T.__default__, int)
        self.assertIs(U.__default__, float)
        self.assertIs(V.__default__, None)


    def test_defaults_on_type_alias(self):
        ns = run_code("""
            type Alias[T = int, **U = float, *V = None] = int
        """)

        T, U, V = ns["Alias"].__type_params__
        self.assertIs(T.__default__, int)
        self.assertIs(U.__default__, float)
        self.assertIs(V.__default__, None)


    def test_starred_invalid(self):
        check_syntax_error(self, "type Alias[T = *int] = int")
        check_syntax_error(self, "type Alias[**P = *int] = int")


    def test_starred_typevartuple(self):
        ns = run_code("""
            default = tuple[int, str]
            type Alias[*Ts = *default] = Ts
        """)

        Ts, = ns["Alias"].__type_params__
        self.assertEqual(Ts.__default__, next(iter(ns["default"])))


    def test_lazy_evaluation(self):
        ns = run_code("""
            type Alias[T = Undefined, *U = Undefined, **V = Undefined] = int
        """)

        T, U, V = ns["Alias"].__type_params__

        with self.assertRaises(NameError):
            T.__default__
        with self.assertRaises(NameError):
            U.__default__
        with self.assertRaises(NameError):
            V.__default__

        ns["Undefined"] = "defined"
        self.assertEqual(T.__default__, "defined")
        self.assertEqual(U.__default__, "defined")
        self.assertEqual(V.__default__, "defined")

        # Now it is cached
        ns["Undefined"] = "redefined"
        self.assertEqual(T.__default__, "defined")
        self.assertEqual(U.__default__, "defined")
        self.assertEqual(V.__default__, "defined")


class BaseTest(unittest.TestCase):
    def test_unpack(self):
        alias = tuple[str, ...]
        self.assertIs(alias.__unpacked__, False)
        unpacked = (*alias,)[0]
        self.assertIs(unpacked.__unpacked__, True)


# Public compiler/substitution paths checked against the same CPython build.
class VariadicCompilerRegressions(unittest.TestCase):
    def test_variadic_substitution_and_nested_aliases(self):
        Ts = TypeVarTuple('Ts')
        T = TypeVar('T')
        U = TypeVar('U')
        A = tuple[T, *Ts, U]
        self.assertEqual(A[int, str].__args__, (int, str))
        self.assertEqual(A[int, float, bool, str].__args__, (int, float, bool, str))
        with self.assertRaises(TypeError): A[int]
        self.assertEqual(list[tuple[*Ts]][int, str], list[tuple[int, str]])
        self.assertEqual(tuple[*Ts][()], tuple[()])
        self.assertEqual(tuple[*Ts][*tuple[int, str]], tuple[int, str])
        self.assertIs(tuple[int].__class__, type(tuple[int]))
        self.assertFalse(isinstance(tuple[int], type))
        starred, = tuple[int]
        self.assertNotEqual(starred, tuple[int])
        self.assertEqual(len({starred, tuple[int]}), 2)
        self.assertEqual((starred | tuple[int]).__args__, (starred, tuple[int]))
        self.assertEqual(tuple[T, *Ts, U][*tuple[float, ...]].__args__, (float, *tuple[float, ...], float))
        with self.assertRaises(TypeError): tuple[*Ts, *TypeVarTuple('Us')][int]
        with self.assertRaises(TypeError): tuple[Ts][int]
        self.assertEqual(repr(*tuple[*Ts]), '*tuple[typing.Unpack[Ts]]')
        type Ordinary[T] = T
        self.assertIs(Ordinary.__parameters__, Ordinary.__type_params__)
        type Alias[*Xs] = tuple[*Xs]
        self.assertEqual(Alias.__parameters__, (Unpack[Alias.__type_params__[0]],))
        self.assertEqual(tuple[*Alias].__args__, (Unpack[Alias],))
        self.assertEqual(tuple[*Alias[int, str]].__args__, (*Alias[int, str],))

    def test_paramspec_substitution(self):
        P = ParamSpec('P')
        T = TypeVar('T')
        self.assertEqual(P.__typing_subst__([None, int]), (type(None), int))
        self.assertIs(P.__typing_subst__(...), ...)
        self.assertIs(P.__typing_subst__(P), P)
        for arg in (42, int, None, T, int | str):
            with self.assertRaises(TypeError): P.__typing_subst__(arg)
        self.assertEqual(tuple[P][int, str].__args__, ((int, str),))
        self.assertEqual(tuple[P][[int, str]].__args__, ((int, str),))
        self.assertEqual(tuple[P][...].__args__, (...,))
        self.assertEqual(tuple[P, T][[int, str], float].__args__, ((int, str), float))
        self.assertEqual(tuple[P, T][[T], int][str].__args__, ((str,), int))
        with self.assertRaises(TypeError): tuple[P][()]
        with self.assertRaises(TypeError): tuple[P][P, int]
        self.assertEqual(repr(ParamSpecArgs(42)), '42.args')
        with self.assertRaises(TypeError): hash(P.args)
        self.assertEqual((P | int).__args__, (P, int))
        self.assertEqual((int | P).__args__, (int, P))
        self.assertEqual((Unpack[int] | str).__args__, (Unpack[int], str))
        self.assertIs(Unpack[None].__args__[0], type(None))
        for value in ((), (int,), (int, str)):
            with self.assertRaises(TypeError): Unpack[value]
        from typing import get_origin, get_args
        self.assertIs(get_origin(P.args), P)
        self.assertEqual(get_args(P.args), ())
        self.assertIs(get_origin(Unpack[TypeVarTuple('Ts')]), Unpack)

    def test_lazy_variadic_defaults(self):
        type A[*Ts = *tuple[int, str], **P = [int, str]] = tuple[*Ts, P]
        Ts, P = A.__type_params__
        self.assertTrue(Ts.has_default())
        self.assertTrue(P.has_default())
        self.assertEqual(Ts.__default__, *tuple[int, str])
        self.assertEqual(P.__default__, [int, str])
        self.assertEqual(tuple[*Ts][()], tuple[[int, str]])
        self.assertEqual(tuple[P][()].__args__, ((int, str),))
        self.assertEqual(Ts.evaluate_default.__code__.co_varnames, ('.format',))
        self.assertEqual(P.evaluate_default.__code__.co_varnames, ('.format',))
        with self.assertRaises(TypeError): TypeVarTuple('Ts', int)
        with self.assertRaises(TypeError): ParamSpec('P', int)

class VariadicProtocolOrder(unittest.TestCase):
    def test_unpack_flag_precedes_substitution(self):
        events = []
        class Raising:
            @property
            def __typing_is_unpacked_typevartuple__(self):
                raise ValueError('unpack flag')
            def __typing_subst__(self, value):
                events.append('subst')
                return value
        with self.assertRaises(ValueError): tuple[Raising()][int]
        self.assertEqual(events, [])
        class Mutating:
            __typing_is_unpacked_typevartuple__ = False
            def __typing_subst__(self, value):
                self.__typing_is_unpacked_typevartuple__ = True
                return (value,)
        self.assertEqual(tuple[Mutating()][int].__args__, ((int,),))

if __name__ == '__main__': unittest.main()
