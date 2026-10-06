# Unchanged CPython 3.14 types.CoroutineTests methods at 18ef0f0cb52.
import types
import unittest

class inspect:
    CO_ITERABLE_COROUTINE = 0x100
    CO_COROUTINE = 0x80

class CoroutineTests(unittest.TestCase):
    def test_code_replace_validation_and_generator_identity(self):
        def gen():
            yield 1
            return 2
        original = gen.__code__
        copy = original.replace()
        self.assertIsNot(copy, original)
        self.assertEqual(copy.co_flags, original.co_flags)
        with self.assertRaises(TypeError): original.replace(1)
        with self.assertRaises(TypeError): original.replace(co_flags=None)
        with self.assertRaises(ValueError): original.replace(co_flags=-1)
        with self.assertRaises(OverflowError): original.replace(co_flags=2**100)
        types.coroutine(gen)
        g = gen()
        self.assertIs(g.gi_code, gen.__code__)
        self.assertFalse(g.gi_suspended)
        self.assertEqual(next(g), 1)
        self.assertTrue(g.gi_suspended)
        with self.assertRaises(StopIteration): next(g)
        self.assertFalse(g.gi_suspended)

    def test_wrong_args(self):
        samples = [None, 1, object()]
        for sample in samples:
            with self.assertRaisesRegex(TypeError,
                                        'types.coroutine.*expects a callable'):
                types.coroutine(sample)

    def test_non_gen_values(self):
        @types.coroutine
        def foo():
            return 'spam'
        self.assertEqual(foo(), 'spam')

        class Awaitable:
            def __await__(self):
                return ()
        aw = Awaitable()
        @types.coroutine
        def foo():
            return aw
        self.assertIs(aw, foo())

        # decorate foo second time
        foo = types.coroutine(foo)
        self.assertIs(aw, foo())

    def test_async_def(self):
        # Test that types.coroutine passes 'async def' coroutines
        # without modification

        async def foo(): pass
        foo_code = foo.__code__
        foo_flags = foo.__code__.co_flags
        decorated_foo = types.coroutine(foo)
        self.assertIs(foo, decorated_foo)
        self.assertEqual(foo.__code__.co_flags, foo_flags)
        self.assertIs(decorated_foo.__code__, foo_code)

        foo_coro = foo()
        def bar(): return foo_coro
        for _ in range(2):
            bar = types.coroutine(bar)
            coro = bar()
            self.assertIs(foo_coro, coro)
            self.assertEqual(coro.cr_code.co_flags, foo_flags)
            coro.close()

    def test_duck_coro(self):
        class CoroLike:
            def send(self): pass
            def throw(self): pass
            def close(self): pass
            def __await__(self): return self

        coro = CoroLike()
        @types.coroutine
        def foo():
            return coro
        self.assertIs(foo(), coro)
        self.assertIs(foo().__await__(), coro)

    def test_duck_corogen(self):
        class CoroGenLike:
            def send(self): pass
            def throw(self): pass
            def close(self): pass
            def __await__(self): return self
            def __iter__(self): return self
            def __next__(self): pass

        coro = CoroGenLike()
        @types.coroutine
        def foo():
            return coro
        self.assertIs(foo(), coro)
        self.assertIs(foo().__await__(), coro)

    def test_duck_functional_gen(self):
        class Generator:
            """Emulates the following generator (very clumsy):

              def gen(fut):
                  result = yield fut
                  return result * 2
            """
            def __init__(self, fut):
                self._i = 0
                self._fut = fut
            def __iter__(self):
                return self
            def __next__(self):
                return self.send(None)
            def send(self, v):
                try:
                    if self._i == 0:
                        assert v is None
                        return self._fut
                    if self._i == 1:
                        raise StopIteration(v * 2)
                    if self._i > 1:
                        raise StopIteration
                finally:
                    self._i += 1
            def throw(self, tp, *exc):
                self._i = 100
                if tp is not GeneratorExit:
                    raise tp
            def close(self):
                self.throw(GeneratorExit)

        @types.coroutine
        def foo(): return Generator('spam')

        wrapper = foo()
        self.assertIsInstance(wrapper, types._GeneratorWrapper)

        async def corofunc():
            return await foo() + 100
        coro = corofunc()

        self.assertEqual(coro.send(None), 'spam')
        try:
            coro.send(20)
        except StopIteration as ex:
            self.assertEqual(ex.args[0], 140)
        else:
            self.fail('StopIteration was expected')

    def test_returning_itercoro(self):
        @types.coroutine
        def gen():
            yield

        gencoro = gen()

        @types.coroutine
        def foo():
            return gencoro

        self.assertIs(foo(), gencoro)

        # decorate foo second time
        foo = types.coroutine(foo)
        self.assertIs(foo(), gencoro)

    def test_genfunc(self):
        def gen(): yield
        self.assertIs(types.coroutine(gen), gen)
        self.assertIs(types.coroutine(types.coroutine(gen)), gen)

        self.assertTrue(gen.__code__.co_flags & inspect.CO_ITERABLE_COROUTINE)
        self.assertFalse(gen.__code__.co_flags & inspect.CO_COROUTINE)

        g = gen()
        self.assertTrue(g.gi_code.co_flags & inspect.CO_ITERABLE_COROUTINE)
        self.assertFalse(g.gi_code.co_flags & inspect.CO_COROUTINE)

        self.assertIs(types.coroutine(gen), gen)

    def test_wrapper_object(self):
        def gen():
            yield
        @types.coroutine
        def coro():
            return gen()

        wrapper = coro()
        self.assertIn('GeneratorWrapper', repr(wrapper))
        self.assertEqual(repr(wrapper), str(wrapper))
        self.assertTrue(set(dir(wrapper)).issuperset({
            '__await__', '__iter__', '__next__', 'cr_code', 'cr_running',
            'cr_frame', 'cr_suspended', 'gi_code', 'gi_frame', 'gi_running',
            'gi_suspended', 'send', 'close', 'throw'}))


if __name__ == '__main__':
    unittest.main()
