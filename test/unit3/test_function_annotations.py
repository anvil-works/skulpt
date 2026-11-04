# Unchanged CPython 3.14 type annotation methods at 18ef0f0cb52.
import types
import unittest

class FunctionAnnotationTests(unittest.TestCase):
    def test_manual_function_annotate(self):
        # The upstream helper also covers classes/modules in their next increment.
        def f(): pass
        self.check_annotations(f)

    def check_annotations(self, f):
        self.assertEqual(f.__annotations__, {})
        self.assertIs(f.__annotate__, None)

        with self.assertRaisesRegex(TypeError, "__annotate__ must be callable or None"):
            f.__annotate__ = 42
        f.__annotate__ = lambda: 42
        with self.assertRaisesRegex(TypeError, r"takes 0 positional arguments but 1 was given"):
            print(f.__annotations__)

        f.__annotate__ = lambda x: 42
        with self.assertRaisesRegex(TypeError, r"__annotate__ returned non-dict of type 'int'"):
            print(f.__annotations__)

        f.__annotate__ = lambda x: {"x": x}
        self.assertEqual(f.__annotations__, {"x": 1})

        # Setting annotate to None does not invalidate the cached __annotations__
        f.__annotate__ = None
        self.assertEqual(f.__annotations__, {"x": 1})

        # But setting it to a new callable does
        f.__annotate__ = lambda x: {"y": x}
        self.assertEqual(f.__annotations__, {"y": 1})

        # Setting f.__annotations__ also clears __annotate__
        f.__annotations__ = {"z": 43}
        self.assertIs(f.__annotate__, None)

    # CPython-checked cache, generated code and variadic regressions.
    def test_generated_annotate_format_code_and_cache(self):
        scope = {}
        exec("""
seen = []
def mark(value):
    seen.append(value)
    return value
value = 1
def f(a: mark(value), /, b: mark(value + 1)) -> mark(value + 2): pass
""", scope)
        f = scope['f']
        annotate = f.__annotate__
        self.assertIs(type(annotate), types.FunctionType)
        self.assertEqual(annotate.__name__, '__annotate__')
        self.assertEqual(annotate.__qualname__, 'f.__annotate__')
        self.assertEqual(annotate.__code__.co_varnames, ('format',))
        self.assertEqual(annotate.__code__.co_argcount, 1)
        self.assertEqual(annotate.__code__.co_posonlyargcount, 1)
        self.assertEqual(scope['seen'], [])
        for value in [3, 4]:
            with self.assertRaises(NotImplementedError): annotate(value)
        with self.assertRaises(TypeError): annotate(None)
        with self.assertRaisesRegex(TypeError, "missing.*'format'"): annotate()
        with self.assertRaisesRegex(TypeError, "positional.only.*'format'"): annotate(format=1)
        self.assertEqual(scope['seen'], [])
        first = f.__annotations__
        self.assertEqual(list(first), ['b', 'a', 'return'])
        self.assertEqual(first, {'a': 1, 'b': 2, 'return': 3})
        self.assertEqual(scope['seen'], [2, 1, 3])
        self.assertIs(first, f.__annotations__)
        scope['value'] = 10
        self.assertEqual(annotate(2), {'a': 10, 'b': 11, 'return': 12})
        self.assertIs(first, f.__annotations__)

    def test_cache_deletion_assignment_and_invalid_callback(self):
        def f(x: Missing): pass
        for clear in [lambda: setattr(f, '__annotations__', None),
                      lambda: delattr(f, '__annotations__')]:
            f.__annotate__ = lambda format: {'format': format}
            clear()
            self.assertIsNone(f.__annotate__)
            self.assertEqual(f.__annotations__, {})
        with self.assertRaises(TypeError): del f.__annotate__
        callback = lambda format: {'format': format}
        f.__annotate__ = callback
        with self.assertRaises(TypeError): f.__annotations__ = 42
        self.assertIs(f.__annotate__, callback)
        self.assertEqual(f.__annotations__, {'format': 1})

    def test_future_annotate_and_variadic_annotation(self):
        scope = {}
        exec("""from __future__ import annotations
def f(x: Missing) -> Missing: pass
""", scope)
        f = scope['f']
        self.assertIs(type(f.__annotate__), types.FunctionType)
        self.assertEqual(f.__annotate__(1), {'x': 'Missing', 'return': 'Missing'})
        self.assertEqual(f.__annotations__, {'x': 'Missing', 'return': 'Missing'})
        self.assertIsNone(f.__annotate__.__closure__)
        seq = [int]
        def variadic(*args: *seq): pass
        self.assertEqual(variadic.__annotations__, {'args': int})
        seq.append(str)
        with self.assertRaises(ValueError): variadic.__annotate__(1)
        self.assertEqual(variadic.__annotations__, {'args': int})
        scope = {}
        exec(compile("def outer():\n def f(x: [(y:=i) for i in xs]): pass\n return f", 'future.py', 'exec', flags=0x1000000), scope)
        f = scope['outer']()
        self.assertIsNone(f.__annotate__.__closure__)
        self.assertEqual(f.__annotations__, {'x': '[(y := i) for i in xs]'})

    def test_function(self):
        def func(x: undefined, /, y: undefined, *args: undefined, z: undefined, **kwargs: undefined) -> undefined:
            pass

        with self.assertRaises(NameError):
            func.__annotations__

        undefined = 1
        self.assertEqual(func.__annotations__, {
            "x": 1,
            "y": 1,
            "args": 1,
            "z": 1,
            "kwargs": 1,
            "return": 1,
        })


if __name__ == "__main__": unittest.main()
