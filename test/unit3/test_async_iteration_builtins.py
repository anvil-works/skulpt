# Unchanged CPython 3.14 async iteration builtin methods at 18ef0f0cb52.
import types
import unittest

_no_default = object()

class AwaitException(Exception):
    pass


def run_until_complete(coro):
    exc = False
    while True:
        try:
            if exc:
                exc = False
                fut = coro.throw(AwaitException)
            else:
                fut = coro.send(None)
        except StopIteration as ex:
            return ex.args[0] if ex.args else None

        if fut == ('throw',):
            exc = True


def py_anext(iterator, default=_no_default):
    """Pure-Python implementation of anext() for testing purposes.

    Closely matches the builtin anext() C implementation.
    Can be used to compare the built-in implementation of the inner
    coroutines machinery to C-implementation of __anext__() and send()
    or throw() on the returned generator.
    """

    try:
        __anext__ = type(iterator).__anext__
    except AttributeError:
        raise TypeError(f'{iterator!r} is not an async iterator')

    if default is _no_default:
        return __anext__(iterator)

    async def anext_impl():
        try:
            # The C code is way more low-level than this, as it implements
            # all methods of the iterator protocol. In this implementation
            # we're relying on higher-level coroutine concepts, but that's
            # exactly what we want -- crosstest pure-Python high-level
            # implementation and low-level C anext() iterators.
            return await __anext__(iterator)
        except StopAsyncIteration:
            return default

    return anext_impl()


class closing:
    """Context to automatically close something at the end of a block.

    Code like this:

        with closing(<module>.open(<arguments>)) as f:
            <block>

    is equivalent to this:

        f = <module>.open(<arguments>)
        try:
            <block>
        finally:
            f.close()

    """
    def __init__(self, thing):
        self.thing = thing
    def __enter__(self):
        return self.thing
    def __exit__(self, *exc_info):
        self.thing.close()


# Harness adapters: actual protocol execution uses the upstream coroutine driver.
# The driver permits an empty StopIteration.args for asyncio tests returning None.
# SubTest preserves its assertions and exception propagation without grouping reports.
class contextlib:
    closing = closing

class Loop:
    run_until_complete = staticmethod(run_until_complete)

class SubTest:
    def __enter__(self): pass
    def __exit__(self, *args): return False

class AsyncIterationBuiltinTest(unittest.TestCase):
    def test_creation_lookup_and_lazy_default_conversion(self):
        calls = []
        class Iterator:
            def __anext__(self):
                calls.append('next')
                return object()
        it = Iterator()
        it.__anext__ = lambda: calls.append('instance')
        plain = anext(it)
        self.assertIs(type(plain), object)
        wrapped = anext(it, None)
        self.assertEqual(calls, ['next', 'next'])
        with self.assertRaises(TypeError): wrapped.send(None)
        class Raising:
            def __anext__(self): raise StopAsyncIteration('call')
        with self.assertRaisesRegex(StopAsyncIteration, 'call'): anext(Raising(), None)
        class BadIterable:
            def __aiter__(self): return ()
        with self.assertRaisesRegex(TypeError, 'aiter.*not an async iterator'): aiter(BadIterable())
        with self.assertRaisesRegex(TypeError, 'not an async iterable'): aiter(1)

    def test_default_none_and_normal_return_none(self):
        async def gen(): yield None
        g = gen()
        for default in [None, 'end']:
            op = anext(g, default)
            with self.assertRaises(StopIteration) as cm: next(op)
            self.assertEqual(cm.exception.args, (None,) if default is None else ('end',))
        class Iterator:
            async def __anext__(self): return None
        op = anext(Iterator(), 'default')
        with self.assertRaises(StopIteration) as cm: op.send(None)
        self.assertEqual(cm.exception.args, ())

    def test_await_resolution_exhaustion_propagates(self):
        class Awaitable:
            def __await__(self): raise StopAsyncIteration('await lookup')
        class Iterator:
            def __anext__(self): return Awaitable()
        for operation in [lambda obj: next(obj), lambda obj: obj.send(None),
                          lambda obj: obj.throw(ValueError()), lambda obj: obj.close()]:
            with self.assertRaisesRegex(StopAsyncIteration, 'await lookup'):
                operation(anext(Iterator(), 'default'))

    def setUp(self): self.loop = Loop()
    def subTest(self, *args, **kwargs): return SubTest()
    def check_async_iterator_anext(self, ait_class):
        with self.subTest(anext="pure-Python"):
            self._check_async_iterator_anext(ait_class, py_anext)
        with self.subTest(anext="builtin"):
            self._check_async_iterator_anext(ait_class, anext)

    def _check_async_iterator_anext(self, ait_class, anext):
        g = ait_class()
        async def consume():
            results = []
            results.append(await anext(g))
            results.append(await anext(g))
            results.append(await anext(g, 'buckle my shoe'))
            return results
        res = self.loop.run_until_complete(consume())
        self.assertEqual(res, [1, 2, 'buckle my shoe'])
        with self.assertRaises(StopAsyncIteration):
            self.loop.run_until_complete(consume())

        async def test_2():
            g1 = ait_class()
            self.assertEqual(await anext(g1), 1)
            self.assertEqual(await anext(g1), 2)
            with self.assertRaises(StopAsyncIteration):
                await anext(g1)
            with self.assertRaises(StopAsyncIteration):
                await anext(g1)

            g2 = ait_class()
            self.assertEqual(await anext(g2, "default"), 1)
            self.assertEqual(await anext(g2, "default"), 2)
            self.assertEqual(await anext(g2, "default"), "default")
            self.assertEqual(await anext(g2, "default"), "default")

            return "completed"

        result = self.loop.run_until_complete(test_2())
        self.assertEqual(result, "completed")

        def test_send():
            p = ait_class()
            obj = anext(p, "completed")
            with self.assertRaises(StopIteration):
                with contextlib.closing(obj.__await__()) as g:
                    g.send(None)

        test_send()

        async def test_throw():
            p = ait_class()
            obj = anext(p, "completed")
            self.assertRaises(SyntaxError, obj.throw, SyntaxError)
            return "completed"

        result = self.loop.run_until_complete(test_throw())
        self.assertEqual(result, "completed")

    def test_async_generator_anext(self):
        async def agen():
            yield 1
            yield 2
        self.check_async_iterator_anext(agen)

    def test_python_async_iterator_anext(self):
        class MyAsyncIter:
            """Asynchronously yield 1, then 2."""
            def __init__(self):
                self.yielded = 0
            def __aiter__(self):
                return self
            async def __anext__(self):
                if self.yielded >= 2:
                    raise StopAsyncIteration()
                else:
                    self.yielded += 1
                    return self.yielded
        self.check_async_iterator_anext(MyAsyncIter)

    def test_python_async_iterator_types_coroutine_anext(self):
        import types
        class MyAsyncIterWithTypesCoro:
            """Asynchronously yield 1, then 2."""
            def __init__(self):
                self.yielded = 0
            def __aiter__(self):
                return self
            @types.coroutine
            def __anext__(self):
                if False:
                    yield "this is a generator-based coroutine"
                if self.yielded >= 2:
                    raise StopAsyncIteration()
                else:
                    self.yielded += 1
                    return self.yielded
        self.check_async_iterator_anext(MyAsyncIterWithTypesCoro)

    def test_async_gen_aiter(self):
        async def gen():
            yield 1
            yield 2
        g = gen()
        async def consume():
            return [i async for i in aiter(g)]
        res = self.loop.run_until_complete(consume())
        self.assertEqual(res, [1, 2])

    def test_async_gen_aiter_class(self):
        results = []
        class Gen:
            async def __aiter__(self):
                yield 1
                yield 2
        g = Gen()
        async def consume():
            ait = aiter(g)
            while True:
                try:
                    results.append(await anext(ait))
                except StopAsyncIteration:
                    break
        self.loop.run_until_complete(consume())
        self.assertEqual(results, [1, 2])

    def test_aiter_idempotent(self):
        async def gen():
            yield 1
        applied_once = aiter(gen())
        applied_twice = aiter(applied_once)
        self.assertIs(applied_once, applied_twice)

    def test_anext_bad_args(self):
        async def gen():
            yield 1
        async def call_with_too_few_args():
            await anext()
        async def call_with_too_many_args():
            await anext(gen(), 1, 3)
        async def call_with_wrong_type_args():
            await anext(1, gen())
        async def call_with_kwarg():
            await anext(aiterator=gen())
        with self.assertRaises(TypeError):
            self.loop.run_until_complete(call_with_too_few_args())
        with self.assertRaises(TypeError):
            self.loop.run_until_complete(call_with_too_many_args())
        with self.assertRaises(TypeError):
            self.loop.run_until_complete(call_with_wrong_type_args())
        with self.assertRaises(TypeError):
            self.loop.run_until_complete(call_with_kwarg())

    def test_anext_bad_await(self):
        async def bad_awaitable():
            class BadAwaitable:
                def __await__(self):
                    return 42
            class MyAsyncIter:
                def __aiter__(self):
                    return self
                def __anext__(self):
                    return BadAwaitable()
            regex = r"__await__.*iterator"
            awaitable = anext(MyAsyncIter(), "default")
            with self.assertRaisesRegex(TypeError, regex):
                await awaitable
            awaitable = anext(MyAsyncIter())
            with self.assertRaisesRegex(TypeError, regex):
                await awaitable
            return "completed"
        result = self.loop.run_until_complete(bad_awaitable())
        self.assertEqual(result, "completed")

    async def check_anext_returning_iterator(self, aiter_class):
        awaitable = anext(aiter_class(), "default")
        with self.assertRaises(TypeError):
            await awaitable
        awaitable = anext(aiter_class())
        with self.assertRaises(TypeError):
            await awaitable
        return "completed"

    def test_anext_return_iterator(self):
        class WithIterAnext:
            def __aiter__(self):
                return self
            def __anext__(self):
                return iter("abc")
        result = self.loop.run_until_complete(self.check_anext_returning_iterator(WithIterAnext))
        self.assertEqual(result, "completed")

    def test_anext_return_generator(self):
        class WithGenAnext:
            def __aiter__(self):
                return self
            def __anext__(self):
                yield
        result = self.loop.run_until_complete(self.check_anext_returning_iterator(WithGenAnext))
        self.assertEqual(result, "completed")

    def test_anext_await_raises(self):
        class RaisingAwaitable:
            def __await__(self):
                raise ZeroDivisionError()
                yield
        class WithRaisingAwaitableAnext:
            def __aiter__(self):
                return self
            def __anext__(self):
                return RaisingAwaitable()
        async def do_test():
            awaitable = anext(WithRaisingAwaitableAnext())
            with self.assertRaises(ZeroDivisionError):
                await awaitable
            awaitable = anext(WithRaisingAwaitableAnext(), "default")
            with self.assertRaises(ZeroDivisionError):
                await awaitable
            return "completed"
        result = self.loop.run_until_complete(do_test())
        self.assertEqual(result, "completed")

    def test_anext_iter(self):
        @types.coroutine
        def _async_yield(v):
            return (yield v)

        class MyError(Exception):
            pass

        async def agenfn():
            try:
                await _async_yield(1)
            except MyError:
                await _async_yield(2)
            return
            yield

        def test1(anext):
            agen = agenfn()
            with contextlib.closing(anext(agen, "default").__await__()) as g:
                self.assertEqual(g.send(None), 1)
                self.assertEqual(g.throw(MyError()), 2)
                try:
                    g.send(None)
                except StopIteration as e:
                    err = e
                else:
                    self.fail('StopIteration was not raised')
                self.assertEqual(err.value, "default")

        def test2(anext):
            agen = agenfn()
            with contextlib.closing(anext(agen, "default").__await__()) as g:
                self.assertEqual(g.send(None), 1)
                self.assertEqual(g.throw(MyError()), 2)
                with self.assertRaises(MyError):
                    g.throw(MyError())

        def test3(anext):
            agen = agenfn()
            with contextlib.closing(anext(agen, "default").__await__()) as g:
                self.assertEqual(g.send(None), 1)
                g.close()
                with self.assertRaisesRegex(RuntimeError, 'cannot reuse'):
                    self.assertEqual(g.send(None), 1)

        def test4(anext):
            @types.coroutine
            def _async_yield(v):
                yield v * 10
                return (yield (v * 10 + 1))

            async def agenfn():
                try:
                    await _async_yield(1)
                except MyError:
                    await _async_yield(2)
                return
                yield

            agen = agenfn()
            with contextlib.closing(anext(agen, "default").__await__()) as g:
                self.assertEqual(g.send(None), 10)
                self.assertEqual(g.throw(MyError()), 20)
                with self.assertRaisesRegex(MyError, 'val'):
                    g.throw(MyError('val'))

        def test5(anext):
            @types.coroutine
            def _async_yield(v):
                yield v * 10
                return (yield (v * 10 + 1))

            async def agenfn():
                try:
                    await _async_yield(1)
                except MyError:
                    return
                yield 'aaa'

            agen = agenfn()
            with contextlib.closing(anext(agen, "default").__await__()) as g:
                self.assertEqual(g.send(None), 10)
                with self.assertRaisesRegex(StopIteration, 'default'):
                    g.throw(MyError())

        def test6(anext):
            @types.coroutine
            def _async_yield(v):
                yield v * 10
                return (yield (v * 10 + 1))

            async def agenfn():
                await _async_yield(1)
                yield 'aaa'

            agen = agenfn()
            with contextlib.closing(anext(agen, "default").__await__()) as g:
                with self.assertRaises(MyError):
                    g.throw(MyError())

        def run_test(test):
            with self.subTest('pure-Python anext()'):
                test(py_anext)
            with self.subTest('builtin anext()'):
                test(anext)

        run_test(test1)
        run_test(test2)
        run_test(test3)
        run_test(test4)
        run_test(test5)
        run_test(test6)

    def test_aiter_bad_args(self):
        async def gen():
            yield 1
        async def call_with_too_few_args():
            await aiter()
        async def call_with_too_many_args():
            await aiter(gen(), 1)
        async def call_with_wrong_type_arg():
            await aiter(1)
        with self.assertRaises(TypeError):
            self.loop.run_until_complete(call_with_too_few_args())
        with self.assertRaises(TypeError):
            self.loop.run_until_complete(call_with_too_many_args())
        with self.assertRaises(TypeError):
            self.loop.run_until_complete(call_with_wrong_type_arg())


if __name__ == '__main__':
    unittest.main()
