# CPython 3.14 Lib/test/test_collections.py at 18ef0f0cb52.
# Seven complete methods and validation helpers unchanged; assertion harness adapted.
# Async protocol methods are retained on the separate async stack.
import unittest
import types
from collections.abc import Iterable, Iterator, Generator, Callable

def _test_gen():
    yield

class CompilerProtocolTests(unittest.TestCase):
    def assertIsSubclass(self, cls, base): self.assertTrue(issubclass(cls, base))
    def assertNotIsSubclass(self, cls, base): self.assertFalse(issubclass(cls, base))

    def validate_abstract_methods(self, abc, *names):
        methodstubs = dict.fromkeys(names, lambda s, *args: 0)

        # everything should work will all required methods are present
        C = type('C', (abc,), methodstubs)
        C()

        # instantiation should fail if a required method is missing
        for name in names:
            stubs = methodstubs.copy()
            del stubs[name]
            C = type('C', (abc,), stubs)
            self.assertRaises(TypeError, C)

    def validate_isinstance(self, abc, name):
        stub = lambda s, *args: 0

        C = type('C', (object,), {'__hash__': None})
        setattr(C, name, stub)
        self.assertIsInstance(C(), abc)
        self.assertIsSubclass(C, abc)

        C = type('C', (object,), {'__hash__': None})
        self.assertNotIsInstance(C(), abc)
        self.assertNotIsSubclass(C, abc)




    def test_Iterable(self):
        # Check some non-iterables
        non_samples = [None, 42, 3.14, 1j]
        for x in non_samples:
            self.assertNotIsInstance(x, Iterable)
            self.assertNotIsSubclass(type(x), Iterable)
        # Check some iterables
        samples = [bytes(), str(),
                   tuple(), list(), set(), frozenset(), dict(),
                   dict().keys(), dict().items(), dict().values(),
                   _test_gen(),
                   (x for x in []),
                   ]
        for x in samples:
            self.assertIsInstance(x, Iterable)
            self.assertIsSubclass(type(x), Iterable)
        # Check direct subclassing
        class I(Iterable):
            def __iter__(self):
                return super().__iter__()
        self.assertEqual(list(I()), [])
        self.assertNotIsSubclass(str, I)
        self.validate_abstract_methods(Iterable, '__iter__')
        self.validate_isinstance(Iterable, '__iter__')
        # Check None blocking
        class It:
            def __iter__(self): return iter([])
        class ItBlocked(It):
            __iter__ = None
        self.assertIsSubclass(It, Iterable)
        self.assertIsInstance(It(), Iterable)
        self.assertNotIsSubclass(ItBlocked, Iterable)
        self.assertNotIsInstance(ItBlocked(), Iterable)

    def test_Generator(self):
        class NonGen1:
            def __iter__(self): return self
            def __next__(self): return None
            def close(self): pass
            def throw(self, typ, val=None, tb=None): pass

        class NonGen2:
            def __iter__(self): return self
            def __next__(self): return None
            def close(self): pass
            def send(self, value): return value

        class NonGen3:
            def close(self): pass
            def send(self, value): return value
            def throw(self, typ, val=None, tb=None): pass

        non_samples = [
            None, 42, 3.14, 1j, b"", "", (), [], {}, set(),
            iter(()), iter([]), NonGen1(), NonGen2(), NonGen3()]
        for x in non_samples:
            self.assertNotIsInstance(x, Generator)
            self.assertNotIsSubclass(type(x), Generator)

        class Gen:
            def __iter__(self): return self
            def __next__(self): return None
            def close(self): pass
            def send(self, value): return value
            def throw(self, typ, val=None, tb=None): pass

        class MinimalGen(Generator):
            def send(self, value):
                return value
            def throw(self, typ, val=None, tb=None):
                super().throw(typ, val, tb)

        def gen():
            yield 1

        samples = [gen(), (lambda: (yield))(), Gen(), MinimalGen()]
        for x in samples:
            self.assertIsInstance(x, Iterator)
            self.assertIsInstance(x, Generator)
            self.assertIsSubclass(type(x), Generator)
        self.validate_abstract_methods(Generator, 'send', 'throw')

        # mixin tests
        mgen = MinimalGen()
        self.assertIs(mgen, iter(mgen))
        self.assertIs(mgen.send(None), next(mgen))
        self.assertEqual(2, mgen.send(2))
        self.assertIsNone(mgen.close())
        self.assertRaises(ValueError, mgen.throw, ValueError)
        self.assertRaisesRegex(ValueError, "^huhu$",
                               mgen.throw, ValueError, ValueError("huhu"))
        self.assertRaises(StopIteration, mgen.throw, StopIteration())

        class FailOnClose(Generator):
            def send(self, value): return value
            def throw(self, *args): raise ValueError

        self.assertRaises(ValueError, FailOnClose().close)

        class IgnoreGeneratorExit(Generator):
            def send(self, value): return value
            def throw(self, *args): pass

        self.assertRaises(RuntimeError, IgnoreGeneratorExit().close)


    def test_Callable(self):
        non_samples = [None, 42, 3.14, 1j,
                       "", b"", (), [], {}, set(),
                       _test_gen(),
                       (x for x in []),
                       ]
        for x in non_samples:
            self.assertNotIsInstance(x, Callable)
            self.assertNotIsSubclass(type(x), Callable)
        samples = [lambda: None,
                   type, int, object,
                   len,
                   list.append, [].append,
                   ]
        for x in samples:
            self.assertIsInstance(x, Callable)
            self.assertIsSubclass(type(x), Callable)
        self.validate_abstract_methods(Callable, '__call__')
        self.validate_isinstance(Callable, '__call__')


class CallableAliasRegressions(unittest.TestCase):
    def test_callable_alias_retains_native_subclass(self):
        from typing import ParamSpec, TypeVar, Concatenate
        P = ParamSpec('P')
        T = TypeVar('T')
        alias = Callable[P, T]
        self.assertEqual(alias[[int, str], float], Callable[[int, str], float])
        self.assertEqual(repr(alias[[int, str], float]), 'collections.abc.Callable[[int, str], float]')
        self.assertIs(type(alias), type(alias[[int, str], float]))
        self.assertEqual(Callable[Concatenate[int, P], T][[str], float], Callable[[int, str], float])
        class Alias(types.GenericAlias): pass
        native = Alias(list, (int,))
        self.assertIs(type(native), Alias)
        self.assertEqual(native.__origin__, list)
        self.assertEqual(native.__args__, (int,))
        self.assertEqual(native(), [])
        class Text(str):
            def __str__(self): return 'converted'
        class Meta(type):
            def __getattribute__(cls, name):
                if name == '__module__': return Text('builtins')
                if name == '__qualname__': return Text('raw')
                return super().__getattribute__(name)
        class C(metaclass=Meta): pass
        self.assertEqual(repr(types.GenericAlias(C, (int,))), 'converted[int]')

if __name__ == '__main__': unittest.main()
