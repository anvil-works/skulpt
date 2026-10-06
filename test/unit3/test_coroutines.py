# Selected unchanged CPython 3.14 coroutine methods at 18ef0f0cb52.
import types
import unittest

# inspect's code flag constants, copied as harness fixtures until inspect is ported.
class support:
    MISSING_C_DOCSTRINGS = False

class inspect:
    CO_GENERATOR = 0x20
    CO_COROUTINE = 0x80

class AsyncYieldFrom:
    def __init__(self, obj):
        self.obj = obj

    def __await__(self):
        yield from self.obj


class AsyncYield:
    def __init__(self, value):
        self.value = value

    def __await__(self):
        yield self.value


def run_async(coro):
    assert coro.__class__ in {types.GeneratorType, types.CoroutineType}

    buffer = []
    result = None
    while True:
        try:
            buffer.append(coro.send(None))
        except StopIteration as ex:
            result = ex.args[0] if ex.args else None
            break
    return buffer, result


def run_async__await__(coro):
    assert coro.__class__ is types.CoroutineType
    aw = coro.__await__()
    buffer = []
    result = None
    i = 0
    while True:
        try:
            if i % 2:
                buffer.append(next(aw))
            else:
                buffer.append(aw.send(None))
            i += 1
        except StopIteration as ex:
            result = ex.args[0] if ex.args else None
            break
    return buffer, result


class CoroutineTest(unittest.TestCase):
    def test_coroutine_names(self):
        async def f(): pass
        f.__name__ = 'custom'
        f.__qualname__ = 'qualified'
        coro = f()
        self.assertEqual(coro.__name__, 'custom')
        self.assertEqual(coro.__qualname__, 'qualified')
        class Name(str): pass
        name = Name('new')
        coro.__name__ = name
        coro.__qualname__ = name
        self.assertIs(coro.__name__, name)
        self.assertIs(coro.__qualname__, name)
        for attribute in ['__name__', '__qualname__']:
            with self.assertRaises(TypeError): setattr(coro, attribute, 1)
            with self.assertRaises(TypeError): delattr(coro, attribute)
        coro.close()

    def test_corotype_1(self):
        ct = types.CoroutineType
        if not support.MISSING_C_DOCSTRINGS:
            self.assertIn('into coroutine', ct.send.__doc__)
            self.assertIn('inside coroutine', ct.close.__doc__)
            self.assertIn('in coroutine', ct.throw.__doc__)
            self.assertIn('of the coroutine', ct.__dict__['__name__'].__doc__)
            self.assertIn('of the coroutine', ct.__dict__['__qualname__'].__doc__)
        self.assertEqual(ct.__name__, 'coroutine')

        async def f(): pass
        c = f()
        self.assertIn('coroutine object', repr(c))
        c.close()

    def test_custom_await_delegate_and_next_only_iterator(self):
        class Awaitable:
            def __init__(self): self.iterator = iter(self.values())
            def values(self):
                yield 1
                return 42
            def __await__(self): return self.iterator
        value = Awaitable()
        async def f(): return await value
        coro = f()
        self.assertEqual(coro.send(None), 1)
        self.assertIs(coro.cr_await, value.iterator)
        with self.assertRaises(StopIteration) as cm: coro.send(None)
        self.assertEqual(cm.exception.value, 42)
        self.assertIsNone(coro.cr_await)
        class NextOnly:
            def __next__(self): raise StopIteration(42)
        class Custom:
            def __await__(self): return NextOnly()
        async def g(): return await Custom()
        self.assertEqual(run_async(g()), ([], 42))

    def test_coroutine_close_returns_value(self):
        async def f():
            try: await AsyncYield(1)
            except GeneratorExit: return 42
        coro = f()
        self.assertEqual(coro.send(None), 1)
        self.assertEqual(coro.close(), 42)
        self.assertIsNone(coro.close())

    def test_async_definition_and_await_scope(self):
        for source in ['await thing', 'def f():\n await thing',
                       'async def f():\n yield from thing',
                       'async def f():\n def g():\n  await thing']:
            with self.assertRaises(SyntaxError): compile(source, '<coroutine>', 'exec')
        namespace = {}
        exec('async def f(x=42, /, *, scale=2): return x * scale', namespace)
        self.assertEqual(run_async(namespace['f']()), ([], 84))
        def gen():
            if False: return 1
            yield 42
        self.assertEqual(list(gen()), [42])

    def test_badsyntax_3(self):
        with self.assertRaises(SyntaxError):
            compile("async = 1", "<test>", "exec")

    def test_func_7(self):
        async def bar():
            return 10
        coro = bar()

        def foo():
            yield from coro

        with self.assertRaisesRegex(
                TypeError,
                "cannot 'yield from' a coroutine object in "
                "a non-coroutine generator"):
            list(foo())

        coro.close()

    def test_func_1(self):
        async def foo():
            return 10

        f = foo()
        self.assertIsInstance(f, types.CoroutineType)
        self.assertTrue(bool(foo.__code__.co_flags & inspect.CO_COROUTINE))
        self.assertFalse(bool(foo.__code__.co_flags & inspect.CO_GENERATOR))
        self.assertTrue(bool(f.cr_code.co_flags & inspect.CO_COROUTINE))
        self.assertFalse(bool(f.cr_code.co_flags & inspect.CO_GENERATOR))
        self.assertEqual(run_async(f), ([], 10))

        self.assertEqual(run_async__await__(foo()), ([], 10))

        def bar(): pass
        self.assertFalse(bool(bar.__code__.co_flags & inspect.CO_COROUTINE))

    def test_func_2(self):
        async def foo():
            raise StopIteration

        with self.assertRaisesRegex(
                RuntimeError, "coroutine raised StopIteration"):

            run_async(foo())

    def test_func_4(self):
        async def foo():
            raise StopIteration
        coro = foo()

        check = lambda: self.assertRaisesRegex(
            TypeError, "'coroutine' object is not iterable")

        with check():
            list(coro)

        with check():
            tuple(coro)

        with check():
            sum(coro)

        with check():
            iter(coro)

        with check():
            for i in coro:
                pass

        with check():
            [i for i in coro]

        coro.close()

    def test_func_11(self):
        async def func(): pass
        coro = func()
        # Test that PyCoro_Type and _PyCoroWrapper_Type types were properly
        # initialized
        self.assertIn('__await__', dir(coro))
        self.assertIn('__iter__', dir(coro.__await__()))
        self.assertIn('coroutine_wrapper', repr(coro.__await__()))
        coro.close() # avoid RuntimeWarning

    def test_func_12(self):
        async def g():
            me.send(None)
            await foo
        me = g()
        with self.assertRaisesRegex(ValueError,
                                    "coroutine already executing"):
            me.send(None)

    def test_func_13(self):
        async def g():
            pass

        coro = g()
        with self.assertRaisesRegex(
                TypeError,
                "can't send non-None value to a just-started coroutine"):
            coro.send('spam')

        coro.close()

    def test_func_15(self):
        # See http://bugs.python.org/issue25887 for details

        async def spammer():
            return 'spam'
        async def reader(coro):
            return await coro

        spammer_coro = spammer()

        with self.assertRaisesRegex(StopIteration, 'spam'):
            reader(spammer_coro).send(None)

        with self.assertRaisesRegex(RuntimeError,
                                    'cannot reuse already awaited coroutine'):
            reader(spammer_coro).send(None)

    def test_func_17(self):
        # See http://bugs.python.org/issue25887 for details

        async def coroutine():
            return 'spam'

        coro = coroutine()
        with self.assertRaisesRegex(StopIteration, 'spam'):
            coro.send(None)

        with self.assertRaisesRegex(RuntimeError,
                                    'cannot reuse already awaited coroutine'):
            coro.send(None)

        with self.assertRaisesRegex(RuntimeError,
                                    'cannot reuse already awaited coroutine'):
            coro.throw(Exception('wat'))

        # Closing a coroutine shouldn't raise any exception even if it's
        # already closed/exhausted (similar to generators)
        coro.close()
        coro.close()

    def test_func_18(self):
        # See http://bugs.python.org/issue25887 for details

        async def coroutine():
            return 'spam'

        coro = coroutine()
        await_iter = coro.__await__()
        it = iter(await_iter)

        with self.assertRaisesRegex(StopIteration, 'spam'):
            it.send(None)

        with self.assertRaisesRegex(RuntimeError,
                                    'cannot reuse already awaited coroutine'):
            it.send(None)

        with self.assertRaisesRegex(RuntimeError,
                                    'cannot reuse already awaited coroutine'):
            # Although the iterator protocol requires iterators to
            # raise another StopIteration here, we don't want to do
            # that.  In this particular case, the iterator will raise
            # a RuntimeError, so that 'yield from' and 'await'
            # expressions will trigger the error, instead of silently
            # ignoring the call.
            next(it)

        with self.assertRaisesRegex(RuntimeError,
                                    'cannot reuse already awaited coroutine'):
            it.throw(Exception('wat'))

        with self.assertRaisesRegex(RuntimeError,
                                    'cannot reuse already awaited coroutine'):
            it.throw(Exception('wat'))

        # Closing a coroutine shouldn't raise any exception even if it's
        # already closed/exhausted (similar to generators)
        it.close()
        it.close()

    def test_coro_wrapper_send_tuple(self):
        async def foo():
            return (10,)

        result = run_async__await__(foo())
        self.assertEqual(result, ([], (10,)))

    def test_coro_wrapper_send_stop_iterator(self):
        async def foo():
            return StopIteration(10)

        result = run_async__await__(foo())
        self.assertIsInstance(result[1], StopIteration)
        self.assertEqual(result[1].value, 10)

    def test_await_1(self):

        async def foo():
            await 1
        with self.assertRaisesRegex(TypeError, "'int' object can.t be awaited"):
            run_async(foo())

    def test_await_2(self):
        async def foo():
            await []
        with self.assertRaisesRegex(TypeError, "'list' object can.t be awaited"):
            run_async(foo())

    def test_await_3(self):
        async def foo():
            await AsyncYieldFrom([1, 2, 3])

        self.assertEqual(run_async(foo()), ([1, 2, 3], None))
        self.assertEqual(run_async__await__(foo()), ([1, 2, 3], None))

    def test_await_4(self):
        async def bar():
            return 42

        async def foo():
            return await bar()

        self.assertEqual(run_async(foo()), ([], 42))

    def test_await_5(self):
        class Awaitable:
            def __await__(self):
                return

        async def foo():
            return (await Awaitable())

        with self.assertRaisesRegex(
            TypeError, "__await__.*returned non-iterator of type"):

            run_async(foo())

    def test_await_6(self):
        class Awaitable:
            def __await__(self):
                return iter([52])

        async def foo():
            return (await Awaitable())

        self.assertEqual(run_async(foo()), ([52], None))

    def test_await_7(self):
        class Awaitable:
            def __await__(self):
                yield 42
                return 100

        async def foo():
            return (await Awaitable())

        self.assertEqual(run_async(foo()), ([42], 100))

    def test_await_8(self):
        class Awaitable:
            pass

        async def foo(): return await Awaitable()

        with self.assertRaisesRegex(
            TypeError, "'Awaitable' object can't be awaited"):

            run_async(foo())

    def test_await_9(self):
        def wrap():
            return bar

        async def bar():
            return 42

        async def foo():
            db = {'b':  lambda: wrap}

            class DB:
                b = wrap

            return (await bar() + await wrap()() + await db['b']()()() +
                    await bar() * 1000 + await DB.b()())

        async def foo2():
            return -await bar()

        self.assertEqual(run_async(foo()), ([], 42168))
        self.assertEqual(run_async(foo2()), ([], -42))

    def test_await_10(self):
        async def baz():
            return 42

        async def bar():
            return baz()

        async def foo():
            return await (await bar())

        self.assertEqual(run_async(foo()), ([], 42))

    def test_await_11(self):
        def ident(val):
            return val

        async def bar():
            return 'spam'

        async def foo():
            return ident(val=await bar())

        async def foo2():
            return await bar(), 'ham'

        self.assertEqual(run_async(foo2()), ([], ('spam', 'ham')))

    def test_await_12(self):
        async def coro():
            return 'spam'
        c = coro()

        class Awaitable:
            def __await__(self):
                return c

        async def foo():
            return await Awaitable()

        with self.assertRaisesRegex(
                TypeError, r"__await__\(\) returned a coroutine"):
            run_async(foo())

        c.close()

    def test_await_13(self):
        class Awaitable:
            def __await__(self):
                return self

        async def foo():
            return await Awaitable()

        with self.assertRaisesRegex(
            TypeError, "__await__.*returned non-iterator of type"):

            run_async(foo())

    def test_await_14(self):
        class Wrapper:
            # Forces the interpreter to use CoroutineType.__await__
            def __init__(self, coro):
                assert coro.__class__ is types.CoroutineType
                self.coro = coro
            def __await__(self):
                return self.coro.__await__()

        class FutureLike:
            def __await__(self):
                return (yield)

        class Marker(Exception):
            pass

        async def coro1():
            try:
                return await FutureLike()
            except ZeroDivisionError:
                raise Marker
        async def coro2():
            return await Wrapper(coro1())

        c = coro2()
        c.send(None)
        with self.assertRaisesRegex(StopIteration, 'spam'):
            c.send('spam')

        c = coro2()
        c.send(None)
        with self.assertRaises(Marker):
            c.throw(ZeroDivisionError)

    def test_await_16(self):
        # See https://bugs.python.org/issue29600 for details.

        async def f():
            return ValueError()

        async def g():
            try:
                raise KeyError
            except KeyError:
                return await f()

        _, result = run_async(g())
        self.assertIsNone(result.__context__)


if __name__ == "__main__":
    unittest.main()
