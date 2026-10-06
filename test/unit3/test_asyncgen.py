# Selected unchanged CPython 3.14 test_asyncgen methods at 18ef0f0cb52.
import types
import unittest

class AwaitException(Exception):
    pass


@types.coroutine
def awaitable(*, throw=False):
    if throw:
        yield ('throw',)
    else:
        yield ('result',)


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
            return ex.args[0]

        if fut == ('throw',):
            exc = True


def to_list(gen):
    async def iterate():
        res = []
        async for i in gen:
            res.append(i)
        return res

    return run_until_complete(iterate())


class AsyncGenSyntaxTest(unittest.TestCase):

    def test_async_gen_syntax_01(self):
        code = '''async def foo():
            await abc
            yield from 123
        '''

        with self.assertRaisesRegex(SyntaxError, 'yield from.*inside async'):
            exec(code, {}, {})

    def test_async_gen_syntax_02(self):
        code = '''async def foo():
            yield from 123
        '''

        with self.assertRaisesRegex(SyntaxError, 'yield from.*inside async'):
            exec(code, {}, {})

    def test_async_gen_syntax_03(self):
        code = '''async def foo():
            await abc
            yield
            return 123
        '''

        with self.assertRaisesRegex(SyntaxError, 'return.*value.*async gen'):
            exec(code, {}, {})

    def test_async_gen_syntax_04(self):
        code = '''async def foo():
            yield
            return 123
        '''

        with self.assertRaisesRegex(SyntaxError, 'return.*value.*async gen'):
            exec(code, {}, {})

    def test_async_gen_syntax_05(self):
        code = '''async def foo():
            if 0:
                yield
            return 12
        '''

        with self.assertRaisesRegex(SyntaxError, 'return.*value.*async gen'):
            exec(code, {}, {})


class AsyncGenTest(unittest.TestCase):
    def test_yield_values_and_operation_reuse(self):
        async def gen():
            value = yield None
            yield value
        g = gen()
        self.assertIs(type(g), types.AsyncGeneratorType)
        self.assertIs(g.ag_code, gen.__code__)
        self.assertTrue(gen.__code__.co_flags & 0x200)
        self.assertFalse(gen.__code__.co_flags & 0xa0)
        self.assertFalse(g.ag_running)
        op = g.__anext__()
        self.assertIs(op.__await__(), op)
        with self.assertRaises(StopIteration) as cm: next(op)
        self.assertEqual(cm.exception.args, (None,))
        self.assertFalse(g.ag_running)
        with self.assertRaisesRegex(RuntimeError, 'cannot reuse'): op.send(None)
        op = g.asend(7)
        with self.assertRaises(StopIteration) as cm: op.__next__()
        self.assertEqual(cm.exception.args, (7,))
        with self.assertRaises(StopAsyncIteration): g.__anext__().send(None)
        with self.assertRaises(StopIteration): g.aclose().send(None)

    def test_close_awaits_cleanup_and_tracks_owner(self):
        seen = []
        async def cleanup():
            await awaitable()
            seen.append('cleanup')
        async def gen():
            try: yield 1
            finally: await cleanup()
        g = gen()
        with self.assertRaises(StopIteration): g.__anext__().send(None)
        op = g.aclose()
        self.assertEqual(op.send(None), ('result',))
        self.assertTrue(g.ag_running)
        self.assertIsInstance(g.ag_await, types.CoroutineType)
        with self.assertRaisesRegex(RuntimeError, 'already running'): g.aclose().send(None)
        with self.assertRaises(StopIteration): op.send(None)
        self.assertFalse(g.ag_running)
        self.assertIsNone(g.ag_await)
        self.assertEqual(seen, ['cleanup'])
        with self.assertRaisesRegex(RuntimeError, 'cannot reuse'): op.send(None)
        with self.assertRaises(StopAsyncIteration): g.__anext__().send(None)

    def test_throw_yields_and_exception_cause(self):
        async def gen():
            try: yield 1
            except ValueError as error:
                await awaitable()
                yield error
        g = gen()
        with self.assertRaises(StopIteration): g.__anext__().send(None)
        error = ValueError('injected')
        op = g.athrow(error)
        self.assertEqual(op.send(None), ('result',))
        with self.assertRaises(StopIteration) as cm: op.send(None)
        self.assertIs(cm.exception.value, error)
        with self.assertRaises(StopIteration): g.aclose().send(None)
        for exception in [StopIteration('stop'), StopAsyncIteration('stop')]:
            async def bad():
                yield 1
                raise exception
            g = bad()
            with self.assertRaises(StopIteration): g.__anext__().send(None)
            with self.assertRaises(RuntimeError) as cm: g.__anext__().send(None)
            self.assertIs(cm.exception.__cause__, exception)
            self.assertIs(cm.exception.__context__, exception)

    def compare_generators(self, sync_gen, async_gen):
        def sync_iterate(g):
            res = []
            while True:
                try:
                    res.append(g.__next__())
                except StopIteration:
                    res.append('STOP')
                    break
                except Exception as ex:
                    res.append(str(type(ex)))
            return res

        def async_iterate(g):
            res = []
            while True:
                an = g.__anext__()
                try:
                    while True:
                        try:
                            an.__next__()
                        except StopIteration as ex:
                            if ex.args:
                                res.append(ex.args[0])
                                break
                            else:
                                res.append('EMPTY StopIteration')
                                break
                        except StopAsyncIteration:
                            raise
                        except Exception as ex:
                            res.append(str(type(ex)))
                            break
                except StopAsyncIteration:
                    res.append('STOP')
                    break
            return res

        sync_gen_result = sync_iterate(sync_gen)
        async_gen_result = async_iterate(async_gen)
        self.assertEqual(sync_gen_result, async_gen_result)
        return async_gen_result

    def test_async_gen_iteration_01(self):
        async def gen():
            await awaitable()
            a = yield 123
            self.assertIs(a, None)
            await awaitable()
            yield 456
            await awaitable()
            yield 789

        self.assertEqual(to_list(gen()), [123, 456, 789])

    def test_async_gen_iteration_02(self):
        async def gen():
            await awaitable()
            yield 123
            await awaitable()

        g = gen()
        ai = g.__aiter__()

        an = ai.__anext__()
        self.assertEqual(an.__next__(), ('result',))

        try:
            an.__next__()
        except StopIteration as ex:
            self.assertEqual(ex.args[0], 123)
        else:
            self.fail('StopIteration was not raised')

        an = ai.__anext__()
        self.assertEqual(an.__next__(), ('result',))

        try:
            an.__next__()
        except StopAsyncIteration as ex:
            self.assertFalse(ex.args)
        else:
            self.fail('StopAsyncIteration was not raised')

    def test_async_gen_exception_03(self):
        async def gen():
            await awaitable()
            yield 123
            await awaitable(throw=True)
            yield 456

        with self.assertRaises(AwaitException):
            to_list(gen())

    def test_async_gen_exception_04(self):
        async def gen():
            await awaitable()
            yield 123
            1 / 0

        g = gen()
        ai = g.__aiter__()
        an = ai.__anext__()
        self.assertEqual(an.__next__(), ('result',))

        try:
            an.__next__()
        except StopIteration as ex:
            self.assertEqual(ex.args[0], 123)
        else:
            self.fail('StopIteration was not raised')

        with self.assertRaises(ZeroDivisionError):
            ai.__anext__().__next__()

    def test_async_gen_exception_05(self):
        async def gen():
            yield 123
            raise StopAsyncIteration

        with self.assertRaisesRegex(RuntimeError,
                                    'async generator.*StopAsyncIteration'):
            to_list(gen())

    def test_async_gen_exception_06(self):
        async def gen():
            yield 123
            raise StopIteration

        with self.assertRaisesRegex(RuntimeError,
                                    'async generator.*StopIteration'):
            to_list(gen())

    def test_async_gen_exception_07(self):
        def sync_gen():
            try:
                yield 1
                1 / 0
            finally:
                yield 2
                yield 3

            yield 100

        async def async_gen():
            try:
                yield 1
                1 / 0
            finally:
                yield 2
                yield 3

            yield 100

        self.compare_generators(sync_gen(), async_gen())

    def test_async_gen_exception_08(self):
        def sync_gen():
            try:
                yield 1
            finally:
                yield 2
                1 / 0
                yield 3

            yield 100

        async def async_gen():
            try:
                yield 1
                await awaitable()
            finally:
                await awaitable()
                yield 2
                1 / 0
                yield 3

            yield 100

        self.compare_generators(sync_gen(), async_gen())

    def test_async_gen_exception_09(self):
        def sync_gen():
            try:
                yield 1
                1 / 0
            finally:
                yield 2
                yield 3

            yield 100

        async def async_gen():
            try:
                await awaitable()
                yield 1
                1 / 0
            finally:
                yield 2
                await awaitable()
                yield 3

            yield 100

        self.compare_generators(sync_gen(), async_gen())

    def test_async_gen_exception_10(self):
        async def gen():
            yield 123
        with self.assertRaisesRegex(TypeError,
                                    "non-None value .* async generator"):
            gen().__anext__().send(100)

    def test_async_gen_exception_11(self):
        def sync_gen():
            yield 10
            yield 20

        def sync_gen_wrapper():
            yield 1
            sg = sync_gen()
            sg.send(None)
            try:
                sg.throw(GeneratorExit())
            except GeneratorExit:
                yield 2
            yield 3

        async def async_gen():
            yield 10
            yield 20

        async def async_gen_wrapper():
            yield 1
            asg = async_gen()
            await asg.asend(None)
            try:
                await asg.athrow(GeneratorExit())
            except GeneratorExit:
                yield 2
            yield 3

        self.compare_generators(sync_gen_wrapper(), async_gen_wrapper())

    def test_async_gen_asend_throw_concurrent_with_send(self):
        import types

        @types.coroutine
        def _async_yield(v):
            return (yield v)

        class MyExc(Exception):
            pass

        async def agenfn():
            while True:
                try:
                    await _async_yield(None)
                except MyExc:
                    pass
            return
            yield


        agen = agenfn()
        gen = agen.asend(None)
        gen.send(None)
        gen2 = agen.asend(None)

        with self.assertRaisesRegex(RuntimeError,
                r'anext\(\): asynchronous generator is already running'):
            gen2.throw(MyExc)

        with self.assertRaisesRegex(RuntimeError,
                r"cannot reuse already awaited __anext__\(\)/asend\(\)"):
            gen2.send(None)

    def test_async_gen_athrow_throw_concurrent_with_send(self):
        import types

        @types.coroutine
        def _async_yield(v):
            return (yield v)

        class MyExc(Exception):
            pass

        async def agenfn():
            while True:
                try:
                    await _async_yield(None)
                except MyExc:
                    pass
            return
            yield


        agen = agenfn()
        gen = agen.asend(None)
        gen.send(None)
        gen2 = agen.athrow(MyExc)

        with self.assertRaisesRegex(RuntimeError,
                r'athrow\(\): asynchronous generator is already running'):
            gen2.throw(MyExc)

        with self.assertRaisesRegex(RuntimeError,
                r"cannot reuse already awaited aclose\(\)/athrow\(\)"):
            gen2.send(None)

    def test_async_gen_asend_throw_concurrent_with_throw(self):
        import types

        @types.coroutine
        def _async_yield(v):
            return (yield v)

        class MyExc(Exception):
            pass

        async def agenfn():
            try:
                yield
            except MyExc:
                pass
            while True:
                try:
                    await _async_yield(None)
                except MyExc:
                    pass


        agen = agenfn()
        with self.assertRaises(StopIteration):
            agen.asend(None).send(None)

        gen = agen.athrow(MyExc)
        gen.throw(MyExc)
        gen2 = agen.asend(MyExc)

        with self.assertRaisesRegex(RuntimeError,
                r'anext\(\): asynchronous generator is already running'):
            gen2.throw(MyExc)

        with self.assertRaisesRegex(RuntimeError,
                r"cannot reuse already awaited __anext__\(\)/asend\(\)"):
            gen2.send(None)

    def test_async_gen_athrow_throw_concurrent_with_throw(self):
        import types

        @types.coroutine
        def _async_yield(v):
            return (yield v)

        class MyExc(Exception):
            pass

        async def agenfn():
            try:
                yield
            except MyExc:
                pass
            while True:
                try:
                    await _async_yield(None)
                except MyExc:
                    pass

        agen = agenfn()
        with self.assertRaises(StopIteration):
            agen.asend(None).send(None)

        gen = agen.athrow(MyExc)
        gen.throw(MyExc)
        gen2 = agen.athrow(None)

        with self.assertRaisesRegex(RuntimeError,
                r'athrow\(\): asynchronous generator is already running'):
            gen2.throw(MyExc)

        with self.assertRaisesRegex(RuntimeError,
                r"cannot reuse already awaited aclose\(\)/athrow\(\)"):
            gen2.send(None)

    def test_async_gen_asend_close_runtime_error(self):
        import types

        @types.coroutine
        def _async_yield(v):
            return (yield v)

        async def agenfn():
            try:
                await _async_yield(None)
            except GeneratorExit:
                await _async_yield(None)
            return
            yield

        agen = agenfn()
        gen = agen.asend(None)
        gen.send(None)
        with self.assertRaisesRegex(RuntimeError, "coroutine ignored GeneratorExit"):
            gen.close()

    def test_async_gen_athrow_close_runtime_error(self):
        import types

        @types.coroutine
        def _async_yield(v):
            return (yield v)

        class MyExc(Exception):
            pass

        async def agenfn():
            try:
                yield
            except MyExc:
                try:
                    await _async_yield(None)
                except GeneratorExit:
                    await _async_yield(None)

        agen = agenfn()
        with self.assertRaises(StopIteration):
            agen.asend(None).send(None)
        gen = agen.athrow(MyExc)
        gen.send(None)
        with self.assertRaisesRegex(RuntimeError, "coroutine ignored GeneratorExit"):
            gen.close()


if __name__ == "__main__":
    unittest.main()
