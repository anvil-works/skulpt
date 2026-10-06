# CPython 3.14 Lib/test/test_type_params.py at 18ef0f0cb52.
# Sixty-three upstream methods: 61 unchanged and two with only the make_base
# import redirected to this port. Harness helpers are adapted for Skulpt.
import unittest
import textwrap
import types
from typing import Generic, TypeVar, TypeVarTuple, ParamSpec, NoDefault, get_args
from test_type_parameters import run_code, check_syntax_error, SubTest

def global_generic_func[T](): pass

def run_no_yield_async_fn(async_fn, /, *args, **kwargs):
    coro = async_fn(*args, **kwargs)
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    else:
        raise AssertionError("coroutine did not complete")
    finally:
        coro.close()


class GlobalGenericClass[T]:
    pass

def make_base(arg):
    class Base:
        __arg__ = arg
    return Base

class TypeParamsInvalidTest(unittest.TestCase):
    def test_name_collisions(self):
        check_syntax_error(self, 'def func[**A, A](): ...', "duplicate type parameter 'A'")
        check_syntax_error(self, 'def func[A, *A](): ...', "duplicate type parameter 'A'")
        check_syntax_error(self, 'def func[*A, **A](): ...', "duplicate type parameter 'A'")

        check_syntax_error(self, 'class C[**A, A](): ...', "duplicate type parameter 'A'")
        check_syntax_error(self, 'class C[A, *A](): ...', "duplicate type parameter 'A'")
        check_syntax_error(self, 'class C[*A, **A](): ...', "duplicate type parameter 'A'")


    def test_disallowed_expressions(self):
        check_syntax_error(self, "type X = (yield)")
        check_syntax_error(self, "type X = (yield from x)")
        check_syntax_error(self, "type X = (await 42)")
        check_syntax_error(self, "async def f(): type X = (yield)")
        check_syntax_error(self, "type X = (y := 3)")
        check_syntax_error(self, "class X[T: (yield)]: pass")
        check_syntax_error(self, "class X[T: (yield from x)]: pass")
        check_syntax_error(self, "class X[T: (await 42)]: pass")
        check_syntax_error(self, "class X[T: (y := 3)]: pass")
        check_syntax_error(self, "class X[T](y := Sequence[T]): pass")
        check_syntax_error(self, "def f[T](y: (x := Sequence[T])): pass")
        check_syntax_error(self, "class X[T]([(x := 3) for _ in range(2)] and B): pass")
        check_syntax_error(self, "def f[T: [(x := 3) for _ in range(2)]](): pass")
        check_syntax_error(self, "type T = [(x := 3) for _ in range(2)]")


    def test_compile_error_in_type_param_bound(self):
        # This should not crash, see gh-145187
        check_syntax_error(
            self,
            "if True:\n class h[l:{7for*()in 0}]:2"
        )


    def subTest(self, *args, **kwargs): return SubTest()
    def test_name_non_collision_06(self):
        ns = run_code("""
            class ClassA[X]:
                def func(self, X): return X
            """
        )
        cls = ns["ClassA"]
        self.assertEqual(cls().func(1), 1)
        X, = cls.__type_params__
        self.assertEqual(X.__name__, "X")


    def test_name_non_collision_07(self):
        ns = run_code("""
            class ClassA[X]:
                def func(self):
                    X = 1
                    return X
            """
        )
        cls = ns["ClassA"]
        self.assertEqual(cls().func(), 1)
        X, = cls.__type_params__
        self.assertEqual(X.__name__, "X")


    def test_name_non_collision_08(self):
        ns = run_code("""
            class ClassA[X]:
                def func(self):
                    return [X for X in [1, 2]]
            """
        )
        cls = ns["ClassA"]
        self.assertEqual(cls().func(), [1, 2])
        X, = cls.__type_params__
        self.assertEqual(X.__name__, "X")


    def test_name_non_collision_9(self):
        ns = run_code("""
            class ClassA[X]:
                def func[X](self):
                    ...
            """
        )
        cls = ns["ClassA"]
        outer_X, = cls.__type_params__
        inner_X, = cls.func.__type_params__
        self.assertEqual(outer_X.__name__, "X")
        self.assertEqual(inner_X.__name__, "X")
        self.assertIsNot(outer_X, inner_X)


    def test_name_non_collision_10(self):
        ns = run_code("""
            class ClassA[X]:
                X: int
            """
        )
        cls = ns["ClassA"]
        X, = cls.__type_params__
        self.assertEqual(X.__name__, "X")
        self.assertIs(cls.__annotations__["X"], int)


    def test_incorrect_mro_explicit_object(self):
        with self.assertRaisesRegex(TypeError, r"\(MRO\) for bases object, Generic"):
            class My[X](object): ...


class TypeParamsNonlocalTest(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def test_nonlocal_disallowed_03(self):
        code = """
            class Cls[T]:
                nonlocal T
        """
        check_syntax_error(self, textwrap.dedent(code))


class TypeParamsAccessTest(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def test_class_access_01(self):
        ns = run_code("""
            class ClassA[A, B](dict[A, B]):
                ...
            """
        )
        cls = ns["ClassA"]
        A, B = cls.__type_params__
        self.assertEqual(types.get_original_bases(cls), (dict[A, B], Generic[A, B]))


    def test_class_access_02(self):
        ns = run_code("""
            class MyMeta[A, B](type): ...
            class ClassA[A, B](metaclass=MyMeta[A, B]):
                ...
            """
        )
        meta = ns["MyMeta"]
        cls = ns["ClassA"]
        A1, B1 = meta.__type_params__
        A2, B2 = cls.__type_params__
        self.assertIsNot(A1, A2)
        self.assertIsNot(B1, B2)
        self.assertIs(type(cls), meta)


    def test_class_access_03(self):
        code = """
            def my_decorator(a):
                ...
            @my_decorator(A)
            class ClassA[A, B]():
                ...
            """

        with self.assertRaisesRegex(NameError, "name 'A' is not defined"):
            run_code(code)


    def test_nested_access_01(self):
        ns = run_code("""
            class ClassA[A]:
                def funcB[B](self):
                    class ClassC[C]:
                        def funcD[D](self):
                            return lambda: (A, B, C, D)
                    return ClassC
            """
        )
        cls = ns["ClassA"]
        A, = cls.__type_params__
        B, = cls.funcB.__type_params__
        classC = cls().funcB()
        C, = classC.__type_params__
        D, = classC.funcD.__type_params__
        self.assertEqual(classC().funcD()(), (A, B, C, D))


    def test_out_of_scope_01(self):
        code = """
            class ClassA[T]: ...
            x = T
            """

        with self.assertRaisesRegex(NameError, "name 'T' is not defined"):
            run_code(code)


    def test_out_of_scope_02(self):
        code = """
            class ClassA[A]:
                def funcB[B](self): ...

                x = B
            """

        with self.assertRaisesRegex(NameError, "name 'B' is not defined"):
            run_code(code)


    def test_class_scope_interaction_01(self):
        ns = run_code("""
            class C:
                x = 1
                def method[T](self, arg: x): pass
        """)
        cls = ns["C"]
        self.assertEqual(cls.method.__annotations__["arg"], 1)


    def test_class_scope_interaction_02(self):
        ns = run_code("""
            class C:
                class Base: pass
                class Child[T](Base): pass
        """)
        cls = ns["C"]
        self.assertEqual(cls.Child.__bases__, (cls.Base, Generic))
        T, = cls.Child.__type_params__
        self.assertEqual(types.get_original_bases(cls.Child), (cls.Base, Generic[T]))


    def test_class_deref(self):
        ns = run_code("""
            class C[T]:
                T = "class"
                type Alias = T
        """)
        cls = ns["C"]
        self.assertEqual(cls.Alias.__value__, "class")


    def test_shadowing_nonlocal(self):
        ns = run_code("""
            def outer[T]():
                T = "outer"
                def inner():
                    nonlocal T
                    T = "inner"
                    return T
                return lambda: T, inner
        """)
        outer = ns["outer"]
        T, = outer.__type_params__
        self.assertEqual(T.__name__, "T")
        getter, inner = outer()
        self.assertEqual(getter(), "outer")
        self.assertEqual(inner(), "inner")
        self.assertEqual(getter(), "inner")


    def test_class_base_containing_lambda(self):
        # Test that scopes nested inside hidden functions work correctly
        outer_var = "outer"
        class Base[T]: ...
        class Child[T](Base[lambda: (int, outer_var, T)]): ...
        base, _ = types.get_original_bases(Child)
        func, = get_args(base)
        T, = Child.__type_params__
        self.assertEqual(func(), (int, "outer", T))


    def test_comprehension_01(self):
        type Alias[T: ([T for T in (T, [1])[1]], T)] = [T for T in T.__name__]
        self.assertEqual(Alias.__value__, ["T"])
        T, = Alias.__type_params__
        self.assertEqual(T.__constraints__, ([1], T))


    def test_comprehension_02(self):
        type Alias[T: [lambda: T for T in (T, [1])[1]]] = [lambda: T for T in T.__name__]
        func, = Alias.__value__
        self.assertEqual(func(), "T")
        T, = Alias.__type_params__
        func, = T.__bound__
        self.assertEqual(func(), 1)


    def test_comprehension_03(self):
        def F[T: [lambda: T for T in (T, [1])[1]]](): return [lambda: T for T in T.__name__]
        func, = F()
        self.assertEqual(func(), "T")
        T, = F.__type_params__
        func, = T.__bound__
        self.assertEqual(func(), 1)


    def test_gen_exp_in_nested_class(self):
        code = """
            from test_generic_classes import make_base

            class C[T]:
                T = "class"
                class Inner(make_base(T for _ in (1,)), make_base(T)):
                    pass
        """
        C = run_code(code)["C"]
        T, = C.__type_params__
        base1, base2 = C.Inner.__bases__
        self.assertEqual(list(base1.__arg__), [T])
        self.assertEqual(base2.__arg__, "class")


    def test_gen_exp_in_nested_generic_class(self):
        code = """
            from test_generic_classes import make_base

            class C[T]:
                T = "class"
                class Inner[U](make_base(T for _ in (1,)), make_base(T)):
                    pass
        """
        ns = run_code(code)
        inner = ns["C"].Inner
        base1, base2, _ = inner.__bases__
        self.assertEqual(list(base1.__arg__), [ns["C"].__type_params__[0]])
        self.assertEqual(base2.__arg__, "class")


    def test_listcomp_in_nested_class(self):
        code = """
            from test_generic_classes import make_base

            class C[T]:
                T = "class"
                class Inner(make_base([T for _ in (1,)]), make_base(T)):
                    pass
        """
        C = run_code(code)["C"]
        T, = C.__type_params__
        base1, base2 = C.Inner.__bases__
        self.assertEqual(base1.__arg__, [T])
        self.assertEqual(base2.__arg__, "class")


    def test_listcomp_in_nested_generic_class(self):
        code = """
            from test_generic_classes import make_base

            class C[T]:
                T = "class"
                class Inner[U](make_base([T for _ in (1,)]), make_base(T)):
                    pass
        """
        ns = run_code(code)
        inner = ns["C"].Inner
        base1, base2, _ = inner.__bases__
        self.assertEqual(base1.__arg__, [ns["C"].__type_params__[0]])
        self.assertEqual(base2.__arg__, "class")


    def test_gen_exp_in_generic_method(self):
        code = """
            class C[T]:
                T = "class"
                def meth[U](x: (T for _ in (1,)), y: T):
                    pass
        """
        ns = run_code(code)
        meth = ns["C"].meth
        self.assertEqual(list(meth.__annotations__["x"]), [ns["C"].__type_params__[0]])
        self.assertEqual(meth.__annotations__["y"], "class")


    def test_lambda_in_alias_in_generic_class(self):
        code = """
            class C[T]:
                T = "class"
                type Alias = lambda: T
        """
        C = run_code(code)["C"]
        self.assertIs(C.Alias.__value__(), C.__type_params__[0])


    def test_lambda_in_generic_alias_in_generic_class(self):
        # A lambda nested in the alias cannot see the class scope, but can see
        # a surrounding annotation scope.
        code = """
            class C[T, U]:
                T = "class"
                U = "class"
                type Alias[T] = lambda: (T, U)
        """
        C = run_code(code)["C"]
        T, U = C.Alias.__value__()
        self.assertIs(T, C.Alias.__type_params__[0])
        self.assertIs(U, C.__type_params__[1])


    def test_type_special_case(self):
        # https://github.com/python/cpython/issues/119011
        self.assertEqual(type.__type_params__, ())
        self.assertEqual(object.__type_params__, ())


class TypeParamsLazyEvaluationTest(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def test_qualname(self):
        class Foo[T]:
            pass

        def func[T]():
            pass

        self.assertEqual(Foo.__qualname__, "TypeParamsLazyEvaluationTest.test_qualname.<locals>.Foo")
        self.assertEqual(func.__qualname__, "TypeParamsLazyEvaluationTest.test_qualname.<locals>.func")
        self.assertEqual(global_generic_func.__qualname__, "global_generic_func")
        self.assertEqual(GlobalGenericClass.__qualname__, "GlobalGenericClass")


    def test_recursive_class(self):
        class Foo[T: Foo, U: (Foo, Foo)]:
            pass

        type_params = Foo.__type_params__
        self.assertEqual(len(type_params), 2)
        self.assertEqual(type_params[0].__name__, "T")
        self.assertIs(type_params[0].__bound__, Foo)
        self.assertEqual(type_params[0].__constraints__, ())
        self.assertIs(type_params[0].__default__, NoDefault)

        self.assertEqual(type_params[1].__name__, "U")
        self.assertIs(type_params[1].__bound__, None)
        self.assertEqual(type_params[1].__constraints__, (Foo, Foo))
        self.assertIs(type_params[1].__default__, NoDefault)


    def test_evaluation_error(self):
        class Foo[T: Undefined, U: (Undefined,)]:
            pass

        type_params = Foo.__type_params__
        with self.assertRaises(NameError):
            type_params[0].__bound__
        self.assertEqual(type_params[0].__constraints__, ())
        self.assertIs(type_params[1].__bound__, None)
        self.assertIs(type_params[0].__default__, NoDefault)
        self.assertIs(type_params[1].__default__, NoDefault)
        with self.assertRaises(NameError):
            type_params[1].__constraints__

        Undefined = "defined"
        self.assertEqual(type_params[0].__bound__, "defined")
        self.assertEqual(type_params[0].__constraints__, ())

        self.assertIs(type_params[1].__bound__, None)
        self.assertEqual(type_params[1].__constraints__, ("defined",))


class TypeParamsClassScopeTest(unittest.TestCase):
    def test_explicit_global(self):
        ns = run_code("""
            x = "global"
            def outer():
                x = "nonlocal"
                class Cls:
                    global x
                    type Alias = x
                Cls.x = "class"
                return Cls
        """)
        cls = ns["outer"]()
        self.assertEqual(cls.Alias.__value__, "global")


    def test_explicit_global_with_no_static_bound(self):
        ns = run_code("""
            def outer():
                class Cls:
                    global x
                    type Alias = x
                Cls.x = "class"
                return Cls
        """)
        ns["x"] = "global"
        cls = ns["outer"]()
        self.assertEqual(cls.Alias.__value__, "global")


    def test_explicit_global_with_assignment(self):
        ns = run_code("""
            x = "global"
            def outer():
                x = "nonlocal"
                class Cls:
                    global x
                    type Alias = x
                    x = "global from class"
                Cls.x = "class"
                return Cls
        """)
        cls = ns["outer"]()
        self.assertEqual(cls.Alias.__value__, "global from class")


    def test_explicit_nonlocal(self):
        ns = run_code("""
            x = "global"
            def outer():
                x = "nonlocal"
                class Cls:
                    nonlocal x
                    type Alias = x
                    x = "class"
                return Cls
        """)
        cls = ns["outer"]()
        self.assertEqual(cls.Alias.__value__, "class")


    def subTest(self, *args, **kwargs): return SubTest()
    def test_nested_free(self):
        ns = run_code("""
            def f():
                T = str
                class C:
                    T = int
                    class D[U](T):
                        x = T
                return C
        """)
        C = ns["f"]()
        self.assertIn(int, C.D.__bases__)
        self.assertIs(C.D.x, str)


class DynamicClassTest(unittest.TestCase):
    def _set_type_params(self, ns, params): ns["__type_params__"] = params
    def subTest(self, *args, **kwargs): return SubTest()
    def test_types_new_class_with_callback(self):
        T = TypeVar('T', infer_variance=True)
        Klass = types.new_class('Klass', (Generic[T],), {},
                                lambda ns: self._set_type_params(ns, (T,)))

        self.assertEqual(Klass.__bases__, (Generic,))
        self.assertEqual(Klass.__orig_bases__, (Generic[T],))
        self.assertEqual(Klass.__type_params__, (T,))
        self.assertEqual(Klass.__parameters__, (T,))


    def test_types_new_class_no_callback(self):
        T = TypeVar('T', infer_variance=True)
        Klass = types.new_class('Klass', (Generic[T],), {})

        self.assertEqual(Klass.__bases__, (Generic,))
        self.assertEqual(Klass.__orig_bases__, (Generic[T],))
        self.assertEqual(Klass.__type_params__, ())  # must be explicitly set
        self.assertEqual(Klass.__parameters__, (T,))


class TypeParamsManglingTest(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def test_mangling(self):
        class Foo[__T]:
            param = __T
            def meth[__U](self, arg: __T, arg2: __U):
                return (__T, __U)
            type Alias[__V] = (__T, __V)

        T = Foo.__type_params__[0]
        self.assertEqual(T.__name__, "__T")
        U = Foo.meth.__type_params__[0]
        self.assertEqual(U.__name__, "__U")
        V = Foo.Alias.__type_params__[0]
        self.assertEqual(V.__name__, "__V")

        anno = Foo.meth.__annotations__
        self.assertIs(anno["arg"], T)
        self.assertIs(anno["arg2"], U)
        self.assertEqual(Foo().meth(1, 2), (T, U))

        self.assertEqual(Foo.Alias.__value__, (T, V))


    def test_no_leaky_mangling_in_module(self):
        ns = run_code("""
            __before = "before"
            class X[T]: pass
            __after = "after"
        """)
        self.assertEqual(ns["__before"], "before")
        self.assertEqual(ns["__after"], "after")


    def test_no_leaky_mangling_in_function(self):
        ns = run_code("""
            def f():
                class X[T]: pass
                _X_foo = 2
                __foo = 1
                assert locals()['__foo'] == 1
                return __foo
        """)
        self.assertEqual(ns["f"](), 1)


    def test_no_leaky_mangling_in_class(self):
        ns = run_code("""
            class Outer:
                __before = "before"
                class Inner[T]:
                    __x = "inner"
                __after = "after"
        """)
        Outer = ns["Outer"]
        self.assertEqual(Outer._Outer__before, "before")
        self.assertEqual(Outer.Inner._Inner__x, "inner")
        self.assertEqual(Outer._Outer__after, "after")


    def test_no_mangling_in_bases(self):
        ns = run_code("""
            class __Base:
                def __init_subclass__(self, **kwargs):
                    self.kwargs = kwargs

            class Derived[T](__Base, __kwarg=1):
                pass
        """)
        Derived = ns["Derived"]
        self.assertEqual(Derived.__bases__, (ns["__Base"], Generic))
        self.assertEqual(Derived.kwargs, {"__kwarg": 1})


    def test_no_mangling_in_nested_scopes(self):
        ns = run_code("""
            from test_generic_classes import make_base

            class __X:
                pass

            class Y[T: __X](
                make_base(lambda: __X),
                # doubly nested scope
                make_base(lambda: (lambda: __X)),
                # list comprehension
                make_base([__X for _ in (1,)]),
                # genexp
                make_base(__X for _ in (1,)),
            ):
                pass
        """)
        Y = ns["Y"]
        T, = Y.__type_params__
        self.assertIs(T.__bound__, ns["__X"])
        base0 = Y.__bases__[0]
        self.assertIs(base0.__arg__(), ns["__X"])
        base1 = Y.__bases__[1]
        self.assertIs(base1.__arg__()(), ns["__X"])
        base2 = Y.__bases__[2]
        self.assertEqual(base2.__arg__, [ns["__X"]])
        base3 = Y.__bases__[3]
        self.assertEqual(list(base3.__arg__), [ns["__X"]])


    def test_type_params_are_mangled(self):
        ns = run_code("""
            from test_generic_classes import make_base

            class Foo[__T, __U: __T](make_base(__T), make_base(lambda: __T)):
                param = __T
        """)
        Foo = ns["Foo"]
        T, U = Foo.__type_params__
        self.assertEqual(T.__name__, "__T")
        self.assertEqual(U.__name__, "__U")
        self.assertIs(U.__bound__, T)
        self.assertIs(Foo.param, T)

        base1, base2, *_ = Foo.__bases__
        self.assertIs(base1.__arg__, T)
        self.assertIs(base2.__arg__(), T)


class TypeParamsComplexCallsTest(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def test_defaults(self):
        # Generic functions with both defaults and kwdefaults trigger a specific code path
        # in the compiler.
        def func[T](a: T = "a", *, b: T = "b"):
            return (a, b)

        T, = func.__type_params__
        self.assertIs(func.__annotations__["a"], T)
        self.assertIs(func.__annotations__["b"], T)
        self.assertEqual(func(), ("a", "b"))
        self.assertEqual(func(1), (1, "b"))
        self.assertEqual(func(b=2), ("a", 2))


    def test_complex_base(self):
        class Base:
            def __init_subclass__(cls, **kwargs) -> None:
                cls.kwargs = kwargs

        kwargs = {"c": 3}
        # Base classes with **kwargs trigger a different code path in the compiler.
        class C[T](Base, a=1, b=2, **kwargs):
            pass

        T, = C.__type_params__
        self.assertEqual(T.__name__, "T")
        self.assertEqual(C.kwargs, {"a": 1, "b": 2, "c": 3})
        self.assertEqual(C.__bases__, (Base, Generic))

        bases = (Base,)
        class C2[T](*bases, **kwargs):
            pass

        T, = C2.__type_params__
        self.assertEqual(T.__name__, "T")
        self.assertEqual(C2.kwargs, {"c": 3})
        self.assertEqual(C2.__bases__, (Base, Generic))


    def test_starargs_base(self):
        class C1[T](*()): pass

        T, = C1.__type_params__
        self.assertEqual(T.__name__, "T")
        self.assertEqual(C1.__bases__, (Generic,))

        class Base: pass
        bases = [Base]
        class C2[T](*bases): pass

        T, = C2.__type_params__
        self.assertEqual(T.__name__, "T")
        self.assertEqual(C2.__bases__, (Base, Generic))


class TypeParamsTraditionalTypeVarsTest(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def test_traditional_01(self):
        code = """
            from typing import Generic
            class ClassA[T](Generic[T]): ...
        """

        with self.assertRaisesRegex(TypeError, r"Cannot inherit from Generic\[...\] multiple times."):
            run_code(code)


    def test_traditional_02(self):
        from typing import TypeVar
        S = TypeVar("S")
        with self.assertRaises(TypeError):
            class ClassA[T](dict[T, S]): ...


    def test_traditional_03(self):
        # This does not generate a runtime error, but it should be
        # flagged as an error by type checkers.
        from typing import TypeVar
        S = TypeVar("S")
        def func[T](a: T, b: S) -> T | S:
            return a


class TypeParamsTypeParamsDunder(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def test_typeparams_dunder_class_01(self):
        class Outer[A, B]:
            class Inner[C, D]:
                @staticmethod
                def get_typeparams():
                    return A, B, C, D

        a, b, c, d = Outer.Inner.get_typeparams()
        self.assertEqual(Outer.__type_params__, (a, b))
        self.assertEqual(Outer.Inner.__type_params__, (c, d))

        self.assertEqual(Outer.__parameters__, (a, b))
        self.assertEqual(Outer.Inner.__parameters__, (c, d))


    def test_typeparams_dunder_class_02(self):
        class ClassA:
            pass

        self.assertEqual(ClassA.__type_params__, ())


    def test_typeparams_dunder_class_03(self):
        code = """
            class ClassA[A]():
                pass
            ClassA.__type_params__ = ()
            params = ClassA.__type_params__
        """

        ns = run_code(code)
        self.assertEqual(ns["params"], ())


class TypeParamsRuntimeTest(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def test_name_error(self):
        # gh-109118: This crashed the interpreter due to a refcounting bug
        code = """
        class name_2[name_5]:
            class name_4[name_5](name_0):
                pass
        """
        with self.assertRaises(NameError):
            run_code(code)

        # Crashed with a slightly different stack trace
        code = """
        class name_2[name_5]:
            class name_4[name_5: name_5](name_0):
                pass
        """
        with self.assertRaises(NameError):
            run_code(code)


    def test_broken_class_namespace(self):
        code = """
        class WeirdMapping(dict):
            def __missing__(self, key):
                if key == "T":
                    raise RuntimeError
                raise KeyError(key)

        class Meta(type):
            def __prepare__(name, bases):
                return WeirdMapping()

        class MyClass[V](metaclass=Meta):
            class Inner[U](T):
                pass
        """
        with self.assertRaises(RuntimeError):
            run_code(code)


class DefaultsTest(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def test_defaults_on_class(self):
        ns = run_code("""
            class C[T=int, **U=float, *V=None]:
                pass
        """)

        T, U, V = ns["C"].__type_params__
        self.assertIs(T.__default__, int)
        self.assertIs(U.__default__, float)
        self.assertIs(V.__default__, None)


    def test_nondefault_after_default(self):
        check_syntax_error(self, "def func[T=int, U](): pass", "non-default type parameter 'U' follows default type parameter")
        check_syntax_error(self, "class C[T=int, U]: pass", "non-default type parameter 'U' follows default type parameter")
        check_syntax_error(self, "type A[T=int, U] = int", "non-default type parameter 'U' follows default type parameter")


class TypeParamsTypeVarTest(unittest.TestCase):
    def test_typevar_coroutine(self):
        def get_coroutine[A]():
            async def coroutine[B]():
                return (A, B)
            return coroutine

        co = get_coroutine()

        a, b = run_no_yield_async_fn(co)

        self.assertIsInstance(a, TypeVar)
        self.assertEqual(a.__name__, "A")
        self.assertIsInstance(b, TypeVar)
        self.assertEqual(b.__name__, "B")


# CPython-checked public compiler/runtime contracts beyond the upstream cases.
class GenericClassRegressions(unittest.TestCase):
    def test_specialization_defaults_and_mutable_alias_metadata(self):
        class Box[T=int]:
            def get(self): return T
        T, = Box.__type_params__
        self.assertEqual(Box[()].__args__, (int,))
        self.assertIs(Box[str]().get(), T)
        self.assertEqual(Box[str]().__orig_class__, Box[str])
        alias = Box[str]
        self.assertIs(Box[str], alias)
        self.assertEqual(alias.__dict__['__origin__'], Box)
        self.assertEqual(alias.__dict__['__args__'], (str,))
        self.assertEqual(alias.__module__, Box.__module__)
        alias.__args__ = (float,)
        self.assertEqual(alias.__args__, (float,))
        self.assertIs(Box[str], alias)
        self.assertEqual(Box[str].__args__, (float,))
        partial = Box[T]
        self.assertIs(partial[int], partial[int])
        partial[int].__args__ = (bytes,)
        self.assertEqual(partial[int].__args__, (bytes,))
        alias.custom = 3
        self.assertEqual(Box.custom, 3)
        with self.assertRaises(AttributeError): alias.__unpacked__
        with self.assertRaises(TypeError): isinstance(Box(), Box[int])
        with self.assertRaises(TypeError): Generic[T][int]
        class Derived(Box): pass
        self.assertEqual(Derived.__type_params__, ())
        self.assertEqual(Derived.__parameters__, ())
        Box.__type_params__ = None
        self.assertIs(Box.__type_params__, None)
        with self.assertRaises(TypeError): del Box.__type_params__
        self.assertEqual(int.__type_params__, ())

    def test_variadic_specialization_and_cached_compiler_base(self):
        import typing
        class C[T, *Ts, **P]: pass
        self.assertEqual(C[int, str, float, [int]].__args__, (int, str, float, (int,)))
        self.assertEqual(C[int, []].__args__, (int, ()))
        with self.assertRaises(TypeError): C[int]
        T = TypeVar('T')
        with self.assertRaises(TypeError): Generic[T, T]
        with self.assertRaises(TypeError): Generic[int]
        with self.assertRaises(TypeError): Generic[()]
        original = typing.Generic.__dict__["__class_getitem__"]
        try:
            def broken(cls, args): raise RuntimeError('patched Generic')
            typing.Generic.__class_getitem__ = classmethod(broken)
            class Safe[T]: pass
            self.assertEqual(Safe.__bases__, (typing.Generic,))
        finally:
            typing.Generic.__class_getitem__ = original

    def test_private_parameter_mangling_and_definition_order(self):
        events = []
        def decorate(cls):
            events.append('decorator')
            self.assertEqual(cls.__type_params__[0].__name__, '__T')
            return cls
        def base():
            events.append('base')
            return object
        class Root:
            def __init_subclass__(cls, **kwargs):
                events.append('init_subclass')
                super().__init_subclass__(**kwargs)
        @decorate
        class __Foo[__T](Root):
            events.append('body')
            param = __T
        self.assertEqual(events, ['body', 'init_subclass', 'decorator'])
        self.assertIs(__Foo.param, __Foo.__type_params__[0])
        class __Private:
            __value = 1
        self.assertEqual(__Private._Private__value, 1)
        generic = run_code('class Reused[T]: pass')['Reused']
        ordinary = run_code('class Reused:\n    __field: int')['Reused']
        self.assertEqual(ordinary.__annotations__, {'_Reused__field': int})
        self.assertEqual(generic.__type_params__[0].__name__, 'T')
        with self.assertRaisesRegex(TypeError, 'for bases object, Generic'):
            class Bad[T](base()): pass
        self.assertEqual(events[-1], 'base')

if __name__ == '__main__': unittest.main()
