# CPython 3.14 Lib/test/test_type_params.py at 18ef0f0cb52.
# Upstream method bodies unchanged; class/variadic parameter tests follow separately.
import unittest
import textwrap
from typing import TypeVar

def run_code(code):
    namespace = {}
    exec(textwrap.dedent(code), namespace)
    return namespace

def check_syntax_error(test, code, message=None):
    with test.assertRaises(SyntaxError) as caught:
        compile(textwrap.dedent(code), "<test>", "exec")
    if message is not None:
        test.assertIn(message, str(caught.exception))

class TypeParamsInvalidTest(unittest.TestCase):
    def test_name_non_collision_02(self):
        ns = run_code("""def func[A](A): return A""")
        func = ns["func"]
        self.assertEqual(func(1), 1)
        A, = func.__type_params__
        self.assertEqual(A.__name__, "A")


    def test_name_non_collision_03(self):
        ns = run_code("""def func[A](*A): return A""")
        func = ns["func"]
        self.assertEqual(func(1), (1,))
        A, = func.__type_params__
        self.assertEqual(A.__name__, "A")


    def test_name_non_collision_04(self):
        # Mangled names should not cause a conflict.
        ns = run_code("""
            class ClassA:
                def func[__A](self, __A): return __A
            """
        )
        cls = ns["ClassA"]
        self.assertEqual(cls().func(1), 1)
        A, = cls.func.__type_params__
        self.assertEqual(A.__name__, "__A")


    def test_name_non_collision_05(self):
        ns = run_code("""
            class ClassA:
                def func[_ClassA__A](self, __A): return __A
            """
        )
        cls = ns["ClassA"]
        self.assertEqual(cls().func(1), 1)
        A, = cls.func.__type_params__
        self.assertEqual(A.__name__, "_ClassA__A")


    def test_name_non_collision_13(self):
        ns = run_code("""
            X = 1
            def outer():
                def inner[X]():
                    global X
                    X = 2
                return inner
            """
        )
        self.assertEqual(ns["X"], 1)
        outer = ns["outer"]
        outer()()
        self.assertEqual(ns["X"], 2)


class TypeParamsNonlocalTest(unittest.TestCase):
    def test_nonlocal_disallowed_01(self):
        code = """
            def outer():
                X = 1
                def inner[X]():
                    nonlocal X
                return X
            """
        check_syntax_error(self, code)


    def test_nonlocal_disallowed_02(self):
        code = """
            def outer2[T]():
                def inner1():
                    nonlocal T
        """
        check_syntax_error(self, textwrap.dedent(code))


    def test_nonlocal_allowed(self):
        code = """
            def func[T]():
                T = "func"
                def inner():
                    nonlocal T
                    T = "inner"
                inner()
                assert T == "inner"
        """
        ns = run_code(code)
        func = ns["func"]
        T, = func.__type_params__
        self.assertEqual(T.__name__, "T")


class SubTest:
    def __enter__(self): return self
    def __exit__(self, *args): return False

class TypeParamsAccessTest(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def test_function_access_01(self):
        ns = run_code("""
            def func[A, B](a: dict[A, B]):
                ...
            """
        )
        func = ns["func"]
        A, B = func.__type_params__
        self.assertEqual(func.__annotations__["a"], dict[A, B])


    def test_function_access_02(self):
        code = """
            def func[A](a = list[A]()):
                ...
            """

        with self.assertRaisesRegex(NameError, "name 'A' is not defined"):
            run_code(code)


    def test_function_access_03(self):
        code = """
            def my_decorator(a):
                ...
            @my_decorator(A)
            def func[A]():
                ...
            """

        with self.assertRaisesRegex(NameError, "name 'A' is not defined"):
            run_code(code)


    def test_method_access_01(self):
        ns = run_code("""
            class ClassA:
                x = int
                def func[T](self, a: x, b: T):
                    ...
            """
        )
        cls = ns["ClassA"]
        self.assertIs(cls.func.__annotations__["a"], int)
        T, = cls.func.__type_params__
        self.assertIs(cls.func.__annotations__["b"], T)


    def test_super(self):
        class Base:
            def meth(self):
                return "base"

        class Child(Base):
            # Having int in the annotation ensures the class gets cells for both
            # __class__ and __classdict__
            def meth[T](self, arg: int) -> T:
                return super().meth() + "child"

        c = Child()
        self.assertEqual(c.meth(1), "basechild")


    def test_type_alias_containing_lambda(self):
        type Alias[T] = lambda: T
        T, = Alias.__type_params__
        self.assertIs(Alias.__value__(), T)


    def test_nested_scope_in_generic_alias(self):
        code = """
            T = "global"
            class C:
                T = "class"
                {}
        """
        cases = [
            "type Alias[T] = (T for _ in (1,))",
            "type Alias = (T for _ in (1,))",
            "type Alias[T] = [T for _ in (1,)]",
            "type Alias = [T for _ in (1,)]",
        ]
        for case in cases:
            with self.subTest(case=case):
                ns = run_code(code.format(case))
                alias = ns["C"].Alias
                value = list(alias.__value__)[0]
                if alias.__type_params__:
                    self.assertIs(value, alias.__type_params__[0])
                else:
                    self.assertEqual(value, "global")


    def test_lambda_in_generic_alias_in_class(self):
        # A lambda nested in the alias cannot see the class scope, but can see
        # a surrounding annotation scope.
        code = """
            T = U = "global"
            class C:
                T = "class"
                U = "class"
                type Alias[T] = lambda: (T, U)
        """
        C = run_code(code)["C"]
        T, U = C.Alias.__value__()
        self.assertIs(T, C.Alias.__type_params__[0])
        self.assertEqual(U, "global")


class TypeParamsClassScopeTest(unittest.TestCase):
    def test_bound(self):
        class X:
            T = int
            def foo[U: T](self): ...
        self.assertIs(X.foo.__type_params__[0].__bound__, int)

        ns = run_code("""
            glb = "global"
            class X:
                cls = "class"
                def foo[T: glb, U: cls](self): ...
        """)
        cls = ns["X"]
        T, U = cls.foo.__type_params__
        self.assertEqual(T.__bound__, "global")
        self.assertEqual(U.__bound__, "class")


    def test_modified_later(self):
        class X:
            T = int
            def foo[U: T](self): ...
            type Alias = T
        X.T = float
        self.assertIs(X.foo.__type_params__[0].__bound__, float)
        self.assertIs(X.Alias.__value__, float)


    def test_binding_uses_global(self):
        ns = run_code("""
            x = "global"
            def outer():
                x = "nonlocal"
                class Cls:
                    type Alias = x
                    val = Alias.__value__
                    def meth[T: x](self, arg: x): ...
                    bound = meth.__type_params__[0].__bound__
                    annotation = meth.__annotations__["arg"]
                    x = "class"
                return Cls
        """)
        cls = ns["outer"]()
        self.assertEqual(cls.val, "global")
        self.assertEqual(cls.bound, "global")
        self.assertEqual(cls.annotation, "global")


    def test_no_binding_uses_nonlocal(self):
        ns = run_code("""
            x = "global"
            def outer():
                x = "nonlocal"
                class Cls:
                    type Alias = x
                    val = Alias.__value__
                    def meth[T: x](self, arg: x): ...
                    bound = meth.__type_params__[0].__bound__
                return Cls
        """)
        cls = ns["outer"]()
        self.assertEqual(cls.val, "nonlocal")
        self.assertEqual(cls.bound, "nonlocal")
        self.assertEqual(cls.meth.__annotations__["arg"], "nonlocal")


class TypeParamsTypeVarTest(unittest.TestCase):
    def test_typevar_01(self):
        def func1[A: str, B: str | int, C: (int, str)]():
            return (A, B, C)

        a, b, c = func1()

        self.assertIsInstance(a, TypeVar)
        self.assertEqual(a.__bound__, str)
        self.assertTrue(a.__infer_variance__)
        self.assertFalse(a.__covariant__)
        self.assertFalse(a.__contravariant__)

        self.assertIsInstance(b, TypeVar)
        self.assertEqual(b.__bound__, str | int)
        self.assertTrue(b.__infer_variance__)
        self.assertFalse(b.__covariant__)
        self.assertFalse(b.__contravariant__)

        self.assertIsInstance(c, TypeVar)
        self.assertEqual(c.__bound__, None)
        self.assertEqual(c.__constraints__, (int, str))
        self.assertTrue(c.__infer_variance__)
        self.assertFalse(c.__covariant__)
        self.assertFalse(c.__contravariant__)


    def test_typevar_generator(self):
        def get_generator[A]():
            def generator1[C]():
                yield C

            def generator2[B]():
                yield A
                yield B
                yield from generator1()
            return generator2

        gen = get_generator()

        a, b, c = [x for x in gen()]

        self.assertIsInstance(a, TypeVar)
        self.assertEqual(a.__name__, "A")
        self.assertIsInstance(b, TypeVar)
        self.assertEqual(b.__name__, "B")
        self.assertIsInstance(c, TypeVar)
        self.assertEqual(c.__name__, "C")


class TypeParamsTypeParamsDunder(unittest.TestCase):
    def test_typeparams_dunder_function_01(self):
        def outer[A, B]():
            def inner[C, D]():
                return A, B, C, D

            return inner

        inner = outer()
        a, b, c, d = inner()
        self.assertEqual(outer.__type_params__, (a, b))
        self.assertEqual(inner.__type_params__, (c, d))


    def test_typeparams_dunder_function_02(self):
        def func1():
            pass

        self.assertEqual(func1.__type_params__, ())


    def test_typeparams_dunder_function_03(self):
        code = """
            def func[A]():
                pass
            func.__type_params__ = ()
        """

        ns = run_code(code)
        self.assertEqual(ns["func"].__type_params__, ())


class DefaultsTest(unittest.TestCase):
    def test_symtable_key_regression_default(self):
        # Test against the bugs that would happen if we used .default_
        # as the key in the symtable.
        ns = run_code("""
            type X[T = [T for T in [T]]] = T
        """)

        T, = ns["X"].__type_params__
        self.assertEqual(T.__default__, [T])


    def test_symtable_key_regression_name(self):
        # Test against the bugs that would happen if we used .name
        # as the key in the symtable.
        ns = run_code("""
            type X1[T = A] = T
            type X2[T = B] = T
            A = "A"
            B = "B"
        """)

        self.assertEqual(ns["X1"].__type_params__[0].__default__, "A")
        self.assertEqual(ns["X2"].__type_params__[0].__default__, "B")



# CPython-checked regressions for wrapper arguments, metadata and lazy failures.
class TypeParameterCompilerRegressions(unittest.TestCase):
    def test_defaults_decorators_and_metadata(self):
        events = []
        def value(label):
            events.append(label)
            return label
        def decorator(label):
            events.append(label)
            def apply(fn):
                events.append('apply ' + label)
                self.assertEqual(fn.__type_params__[0].__name__, 'T')
                return fn
            return apply
        @decorator('outer')
        @decorator('inner')
        def f[T](x=value('pos'), *, a, b=value('kw')):
            return T, x, a, b
        self.assertEqual(events, ['outer', 'inner', 'pos', 'kw', 'apply inner', 'apply outer'])
        T, = f.__type_params__
        self.assertEqual(f(a=3), (T, 'pos', 3, 'kw'))
        self.assertEqual(f.__defaults__, ('pos',))
        self.assertEqual(f.__kwdefaults__, {'b': 'kw'})
        self.assertEqual(f.__qualname__, 'TypeParameterCompilerRegressions.test_defaults_decorators_and_metadata.<locals>.f')
        self.assertEqual(f.__code__.co_freevars, ('T',))
        f.__type_params__ = (1,)
        self.assertEqual(f.__type_params__, (1,))
        with self.assertRaises(TypeError): f.__type_params__ = []
        with self.assertRaises(TypeError): del f.__type_params__

    def test_lazy_cache_retry_and_self_reference(self):
        calls = []
        def bound():
            calls.append('bound')
            return missing
        def f[T: bound() = list[T], U: (T, int) = str]():
            return T, U
        T, U = f()
        self.assertEqual(calls, [])
        self.assertTrue(T.has_default())
        with self.assertRaises(NameError): T.__bound__
        missing = int
        self.assertIs(T.__bound__, int)
        missing = str
        self.assertIs(T.__bound__, int)
        self.assertIs(T.evaluate_bound(), str)
        self.assertEqual(calls, ['bound', 'bound', 'bound'])
        self.assertEqual(T.__default__, list[T])
        self.assertEqual(U.__constraints__, (T, int))
        self.assertEqual(T.evaluate_default.__code__.co_varnames, ('.format',))
        self.assertEqual(T.evaluate_default.__defaults__, (1,))
        self.assertEqual(T.evaluate_default.__code__.co_posonlyargcount, 1)
        with self.assertRaises(TypeError): T.evaluate_default(format=1)
        type A[T: T] = T
        self.assertIs(A.__type_params__[0].__bound__, A.__type_params__[0])
        self.assertEqual(A[int].__args__, (int,))
        self.assertIs(A[int].__origin__, A)

    def test_constructor_default_order_and_restricted_scopes(self):
        from typing import TypeAliasType, NoDefault
        T = TypeVar('T', default=int)
        U = TypeVar('U')
        A = TypeAliasType('A', list[T], type_params=(T,))
        self.assertEqual(A.__parameters__, (T,))
        self.assertEqual(A.__type_params__, (T,))
        self.assertEqual(A[str].__args__, (str,))
        with self.assertRaises(TypeError): TypeAliasType('A', int, type_params=(T, U))
        with self.assertRaises(TypeError): TypeAliasType('A', int, type_params=(int,))
        events = []
        def default():
            events.append('default')
            return int
        def lazy[T=default()](): pass
        with self.assertRaises(TypeError): TypeAliasType('A', int, type_params=lazy.__type_params__ + (42,))
        self.assertEqual(events, ['default'])
        def failing[T=missing](): pass
        with self.assertRaises(NameError): TypeAliasType('A', int, type_params=failing.__type_params__ + (42,))
        for source in [
            'def f[T=int, U](): pass',
            'type A[T=int, U] = int',
            'def f[T, T](): pass',
            'def f[__classdict__](): pass',
            'def f[T: (yield)](): pass',
            'def f[T = (x := 1)](): pass',
            'def f[T: [(x := 1) for _ in range(2)]](): pass',
            'type A[T = [(x := 1) for _ in range(2)]] = T',
        ]:
            with self.assertRaises(SyntaxError): compile(source, '<test>', 'exec')
        type Allowed[T = (lambda: (x := 1))] = T
        self.assertEqual(Allowed.__type_params__[0].__default__(), 1)

if __name__ == '__main__': unittest.main()
