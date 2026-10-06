"""Selected verbatim CPython 3.14 PEP 570 execution tests.

Source: Lib/test/test_positional_only_arg.py, commit 18ef0f0cb52.
Methods below are unchanged. Syntax/harness, pickle,
and async tests are outside this execution subset; their assertions have not
been weakened or silently removed from a selected method.
"""
import unittest


class PositionalOnlyTestCase(unittest.TestCase):
    def test_pos_only_definition(self):
        def f(a, b, c, /, d, e=1, *, f, g=2):
            pass

        self.assertEqual(5, f.__code__.co_argcount)  # 3 posonly + 2 "standard args"
        self.assertEqual(3, f.__code__.co_posonlyargcount)
        self.assertEqual((1,), f.__defaults__)

        def f(a, b, c=1, /, d=2, e=3, *, f, g=4):
            pass

        self.assertEqual(5, f.__code__.co_argcount)  # 3 posonly + 2 "standard args"
        self.assertEqual(3, f.__code__.co_posonlyargcount)
        self.assertEqual((1, 2, 3), f.__defaults__)

    def test_optional_positional_only_args(self):
        def f(a, b=10, /, c=100):
            return a + b + c

        self.assertEqual(f(1, 2, 3), 6)
        self.assertEqual(f(1, 2, c=3), 6)
        with self.assertRaisesRegex(TypeError, r"f\(\) got some positional-only arguments passed as keyword arguments: 'b'"):
            f(1, b=2, c=3)

        self.assertEqual(f(1, 2), 103)
        with self.assertRaisesRegex(TypeError, r"f\(\) got some positional-only arguments passed as keyword arguments: 'b'"):
            f(1, b=2)
        self.assertEqual(f(1, c=2), 13)

        def f(a=1, b=10, /, c=100):
            return a + b + c

        self.assertEqual(f(1, 2, 3), 6)
        self.assertEqual(f(1, 2, c=3), 6)
        with self.assertRaisesRegex(TypeError, r"f\(\) got some positional-only arguments passed as keyword arguments: 'b'"):
            f(1, b=2, c=3)

        self.assertEqual(f(1, 2), 103)
        with self.assertRaisesRegex(TypeError, r"f\(\) got some positional-only arguments passed as keyword arguments: 'b'"):
            f(1, b=2)
        self.assertEqual(f(1, c=2), 13)


    def test_pos_only_call_via_unpacking(self):
        def f(a, b, /):
            return a + b

        self.assertEqual(f(*[1, 2]), 3)


    def test_use_positional_as_keyword(self):
        def f(a, /):
            pass
        expected = r"f\(\) got some positional-only arguments passed as keyword arguments: 'a'"
        with self.assertRaisesRegex(TypeError, expected):
            f(a=1)

        def f(a, /, b):
            pass
        expected = r"f\(\) got some positional-only arguments passed as keyword arguments: 'a'"
        with self.assertRaisesRegex(TypeError, expected):
            f(a=1, b=2)

        def f(a, b, /):
            pass
        expected = r"f\(\) got some positional-only arguments passed as keyword arguments: 'a, b'"
        with self.assertRaisesRegex(TypeError, expected):
            f(a=1, b=2)


    def test_positional_only_and_arg_invalid_calls(self):
        def f(a, b, /, c):
            pass
        with self.assertRaisesRegex(TypeError, r"f\(\) missing 1 required positional argument: 'c'"):
            f(1, 2)
        with self.assertRaisesRegex(TypeError, r"f\(\) missing 2 required positional arguments: 'b' and 'c'"):
            f(1)
        with self.assertRaisesRegex(TypeError, r"f\(\) missing 3 required positional arguments: 'a', 'b', and 'c'"):
            f()
        with self.assertRaisesRegex(TypeError, r"f\(\) takes 3 positional arguments but 4 were given"):
            f(1, 2, 3, 4)


    def test_positional_only_and_optional_arg_invalid_calls(self):
        def f(a, b, /, c=3):
            pass
        f(1, 2)  # does not raise
        with self.assertRaisesRegex(TypeError, r"f\(\) missing 1 required positional argument: 'b'"):
            f(1)
        with self.assertRaisesRegex(TypeError, r"f\(\) missing 2 required positional arguments: 'a' and 'b'"):
            f()
        with self.assertRaisesRegex(TypeError, r"f\(\) takes from 2 to 3 positional arguments but 4 were given"):
            f(1, 2, 3, 4)


    def test_positional_only_and_kwonlyargs_invalid_calls(self):
        def f(a, b, /, c, *, d, e):
            pass
        f(1, 2, 3, d=1, e=2)  # does not raise
        with self.assertRaisesRegex(TypeError, r"missing 1 required keyword-only argument: 'd'"):
            f(1, 2, 3, e=2)
        with self.assertRaisesRegex(TypeError, r"missing 2 required keyword-only arguments: 'd' and 'e'"):
            f(1, 2, 3)
        with self.assertRaisesRegex(TypeError, r"f\(\) missing 1 required positional argument: 'c'"):
            f(1, 2)
        with self.assertRaisesRegex(TypeError, r"f\(\) missing 2 required positional arguments: 'b' and 'c'"):
            f(1)
        with self.assertRaisesRegex(TypeError, r" missing 3 required positional arguments: 'a', 'b', and 'c'"):
            f()
        with self.assertRaisesRegex(TypeError, r"f\(\) takes 3 positional arguments but 6 positional arguments "
                                               r"\(and 2 keyword-only arguments\) were given"):
            f(1, 2, 3, 4, 5, 6, d=7, e=8)
        with self.assertRaisesRegex(TypeError, r"f\(\) got an unexpected keyword argument 'f'"):
            f(1, 2, 3, d=1, e=4, f=56)


    def test_positional_only_invalid_calls(self):
        def f(a, b, /):
            pass
        f(1, 2)  # does not raise
        with self.assertRaisesRegex(TypeError, r"f\(\) missing 1 required positional argument: 'b'"):
            f(1)
        with self.assertRaisesRegex(TypeError, r"f\(\) missing 2 required positional arguments: 'a' and 'b'"):
            f()
        with self.assertRaisesRegex(TypeError, r"f\(\) takes 2 positional arguments but 3 were given"):
            f(1, 2, 3)


    def test_positional_only_with_optional_invalid_calls(self):
        def f(a, b=2, /):
            pass
        f(1)  # does not raise
        with self.assertRaisesRegex(TypeError, r"f\(\) missing 1 required positional argument: 'a'"):
            f()

        with self.assertRaisesRegex(TypeError, r"f\(\) takes from 1 to 2 positional arguments but 3 were given"):
            f(1, 2, 3)


    def test_no_standard_args_usage(self):
        def f(a, b, /, *, c):
            pass

        f(1, 2, c=3)
        with self.assertRaises(TypeError):
            f(1, b=2, c=3)


    def test_change_default_pos_only(self):
        def f(a, b=2, /, c=3):
            return a + b + c

        self.assertEqual((2,3), f.__defaults__)
        f.__defaults__ = (1, 2, 3)
        self.assertEqual(f(1, 2, 3), 6)


    def test_lambdas(self):
        x = lambda a, /, b: a + b
        self.assertEqual(x(1,2), 3)
        self.assertEqual(x(1,b=2), 3)

        x = lambda a, /, b=2: a + b
        self.assertEqual(x(1), 3)

        x = lambda a, b, /: a + b
        self.assertEqual(x(1, 2), 3)

        x = lambda a, b, /, : a + b
        self.assertEqual(x(1, 2), 3)


    def test_posonly_methods(self):
        class Example:
            def f(self, a, b, /):
                return a, b

        self.assertEqual(Example().f(1, 2), (1, 2))
        self.assertEqual(Example.f(Example(), 1, 2), (1, 2))
        self.assertRaises(TypeError, Example.f, 1, 2)
        expected = r"f\(\) got some positional-only arguments passed as keyword arguments: 'b'"
        with self.assertRaisesRegex(TypeError, expected):
            Example().f(1, b=2)


    def test_closures(self):
        def f(x,y):
            def g(x2,/,y2):
                return x + y + x2 + y2
            return g

        self.assertEqual(f(1,2)(3,4), 10)
        with self.assertRaisesRegex(TypeError, r"g\(\) missing 1 required positional argument: 'y2'"):
            f(1,2)(3)
        with self.assertRaisesRegex(TypeError, r"g\(\) takes 2 positional arguments but 3 were given"):
            f(1,2)(3,4,5)

        def f(x,/,y):
            def g(x2,y2):
                return x + y + x2 + y2
            return g

        self.assertEqual(f(1,2)(3,4), 10)

        def f(x,/,y):
            def g(x2,/,y2):
                return x + y + x2 + y2
            return g

        self.assertEqual(f(1,2)(3,4), 10)
        with self.assertRaisesRegex(TypeError, r"g\(\) missing 1 required positional argument: 'y2'"):
            f(1,2)(3)
        with self.assertRaisesRegex(TypeError, r"g\(\) takes 2 positional arguments but 3 were given"):
            f(1,2)(3,4,5)


    def test_annotations_in_closures(self):

        def inner_has_pos_only():
            def f(x: int, /): ...
            return f

        assert inner_has_pos_only().__annotations__ == {'x': int}

        class Something:
            def method(self):
                def f(x: int, /): ...
                return f

        assert Something().method().__annotations__ == {'x': int}

        def multiple_levels():
            def inner_has_pos_only():
                def f(x: int, /): ...
                return f
            return inner_has_pos_only()

        assert multiple_levels().__annotations__ == {'x': int}


    def test_same_keyword_as_positional_with_kwargs(self):
        def f(something,/,**kwargs):
            return (something, kwargs)

        self.assertEqual(f(42, something=42), (42, {'something': 42}))

        with self.assertRaisesRegex(TypeError, r"f\(\) missing 1 required positional argument: 'something'"):
            f(something=42)

        self.assertEqual(f(42), (42, {}))


    def test_mangling(self):
        class X:
            def f(self, __a=42, /):
                return __a

            def f2(self, __a=42, /, __b=43):
                return (__a, __b)

            def f3(self, __a=42, /, __b=43, *, __c=44):
                return (__a, __b, __c)

        self.assertEqual(X().f(), 42)
        self.assertEqual(X().f2(), (42, 43))
        self.assertEqual(X().f3(), (42, 43, 44))


    def test_generator(self):

        def f(a=1, /, b=2):
            yield a, b

        with self.assertRaisesRegex(TypeError, r"f\(\) got some positional-only arguments passed as keyword arguments: 'a'"):
            f(a=1, b=2)

        gen = f(1, 2)
        self.assertEqual(next(gen), (1, 2))
        gen = f(1, b=2)
        self.assertEqual(next(gen), (1, 2))
        gen = f(1)
        self.assertEqual(next(gen), (1, 2))
        gen = f()
        self.assertEqual(next(gen), (1, 2))


    def test_super(self):

        sentinel = object()

        class A:
            def method(self):
                return sentinel

        class C(A):
            def method(self, /):
                return super().method()

        self.assertEqual(C().method(), sentinel)


if __name__ == "__main__":
    unittest.main()
