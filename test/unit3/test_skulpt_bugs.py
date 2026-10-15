"""Unit tests for zero-argument super() & related machinery."""

import unittest


class A:
    def __init__(self, foo):
        self.foo = foo

    def __str__(self):
        return f"{self.__class__.__name__}({self.foo})"


class B(A):
    def __init__(self, foo):
        super().__init__(foo)


class Meta(type):
    def __call__(cls, *args, **kws):
        return super().__call__(*args, **kws)


class I(metaclass=Meta):
    pass


class TestSuper(unittest.TestCase):
    def test_bug_1345(self):
        """defining a __str__ broke super"""
        try:
            B("foo")
        except Exception:
            self.fail("this shouldn't fail")

    def test_meta_call_override(self):
        i = I()  # should not result in an infinite loop!
        self.assertIsInstance(i, I)


class TestRegressions(unittest.TestCase):
    def test_bug_1470(self):
        global i
        i = 0

        def g():
            global i
            i += 1

        def f(x):
            pass

        f(x=g())

        self.assertEqual(i, 1)


class An:
    name: str
    __foo: int


class TestAnnotations(unittest.TestCase):
    def test_bug_1428(self):
        annotations = An.__annotations__
        self.assertEqual(annotations, {"name": str, "_An__foo": int})


class TestDict(unittest.TestCase):
    def test_override_dunder_dict(self):
        class D(dict):
            called = False

            def __getitem__(self, key):
                self.called = True
                return dict.__getitem__(self, key)

            def __setitem__(self, key, value):
                self.called = True
                return dict.__setitem__(self, key, value)

        class A:
            def __init__(self):
                self.__dict__ = D()

        a = A()

        self.assertFalse(a.__dict__.called)
        a.foo = "bar"
        self.assertFalse(a.__dict__.called)
        self.assertEqual(a.foo, "bar")
        self.assertFalse(a.__dict__.called)


class Wrapper:
    def __init__(self, fn):
        self.fn = fn

    def __get__(self, obj, ob_type=None):
        assert isinstance(ob_type, object)
        return self.fn.__get__(obj, ob_type)


class TestCompilerLiterals(unittest.TestCase):
    def test_literal_membership_and_chained_comparisons(self):
        # CPython test_peepholer's constant-list cases, checked through execution.
        self.assertTrue(2 in [1, 2, 3])
        self.assertTrue("z" not in ["a", "b", "c"])
        self.assertTrue(None in [None, 1, None])
        self.assertTrue((1, 2) in [(1, 2), 3, 4])
        self.assertTrue(1 in [1, 2] == [1, 2])
        self.assertTrue(1 < 2 in [1, 2, 3])

    def test_literal_iteration_and_mutable_elements(self):
        values = []
        for value in [None, True, False, (1, 2), b"xy"]:
            values.append(value)
        self.assertEqual(values, [None, True, False, (1, 2), b"xy"])
        self.assertEqual([x * 2 for x in [1, 2, 3]], [2, 4, 6])
        self.assertEqual(list(x * 2 for x in [1, 2, 3]), [2, 4, 6])
        self.assertEqual(list((x, y) for x in [1, 2] for y in [3, 4]),
                         [(1, 3), (1, 4), (2, 3), (2, 4)])

        def make():
            for value in [[0], ([],)]:
                yield value
        first = list(make())
        first[0].append(1)
        first[1][0].append(2)
        self.assertEqual(list(make()), [[0], ([],)])

    def test_literal_evaluation_order_and_ordinary_lists(self):
        events = []
        def mark(value):
            events.append(value)
            return value
        self.assertTrue(mark(2) in [mark(1), mark(2), mark(3)])
        self.assertEqual(events, [2, 1, 2, 3])
        items = [1, 2]
        self.assertTrue(2 in [*items, 3])
        def make():
            return [1, 2, 3]
        first = make()
        first.append(4)
        self.assertEqual(make(), [1, 2, 3])


class TestBugs(unittest.TestCase):
    def test_class_method_bug(self):
        class A:
            @classmethod
            @Wrapper
            def foo(cls):
                return 42

        self.assertEqual(A.foo(), 42)
        # shouldn't fail

    def test_with_statement(self):
        class W:
            def __enter__(self):
                return "a", "b"
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        with W() as (x, y):
            self.assertEqual(x, "a")
            self.assertEqual(y, "b")

    def test_object_ne_on_tuple_subclass_uses_object_slot(self):
        class C(tuple):
            __ne__ = object.__ne__

            def __eq__(self, other):
                return False

        a = C()
        self.assertFalse(a == a)
        self.assertTrue(a != a)


if __name__ == "__main__":
    unittest.main()
