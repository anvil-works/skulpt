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


async def asynciter(iterable):
    """Convert an iterable to an asynchronous iterator."""
    for x in iterable:
        yield x


class CoroutineTest(unittest.TestCase):
    def test_async_comprehension_scope_and_lazy_generators(self):
        async def value(x): return x + 1
        def make(): return (await value(i) for i in range(3))
        gen = make()
        self.assertIs(type(gen), types.AsyncGeneratorType)
        self.assertTrue(gen.ag_code.co_flags & 0x200)
        async def consume(): return [i async for i in gen]
        self.assertEqual(run_async(consume()), ([], [1, 2, 3]))
        namespace = {'value': value}
        exec('gen = (await value(i) for i in range(2))', namespace)
        async def consume_module(): return [i async for i in namespace['gen']]
        self.assertEqual(run_async(consume_module()), ([], [1, 2]))
        for source in ['[await value(i) for i in range(2)]',
                       'def f():\n    [i async for i in gen]',
                       'class C:\n    [i async for i in gen]',
                       'def f():\n    [[await value(i) for i in xs] for xs in []]',
                       'def f():\n    (i for i in await value(1))']:
            with self.assertRaises(SyntaxError): compile(source, 'comp.py', 'exec')

    def test_async_comprehension_locals_after_error(self):
        async def values():
            yield 1
            raise ValueError('iteration')
        async def f():
            i = 'outer'
            try: result = [i async for i in values()]
            except ValueError:
                self.assertEqual(i, 'outer')
                self.assertEqual(locals()['i'], 'outer')
            try: result = [i for i in [1, 2] if 1 / 0]
            except ZeroDivisionError:
                self.assertEqual(locals()['i'], 'outer')
        self.assertEqual(run_async(f()), ([], None))

    def test_comp_1(self):
        async def f(i):
            return i

        async def run_list():
            return [await c for c in [f(1), f(41)]]

        async def run_set():
            return {await c for c in [f(1), f(41)]}

        async def run_dict1():
            return {await c: 'a' for c in [f(1), f(41)]}

        async def run_dict2():
            return {i: await c for i, c in enumerate([f(1), f(41)])}

        self.assertEqual(run_async(run_list()), ([], [1, 41]))
        self.assertEqual(run_async(run_set()), ([], {1, 41}))
        self.assertEqual(run_async(run_dict1()), ([], {1: 'a', 41: 'a'}))
        self.assertEqual(run_async(run_dict2()), ([], {0: 1, 1: 41}))

    def test_comp_2(self):
        async def f(i):
            return i

        async def run_list():
            return [s for c in [f(''), f('abc'), f(''), f(['de', 'fg'])]
                    for s in await c]

        self.assertEqual(
            run_async(run_list()),
            ([], ['a', 'b', 'c', 'de', 'fg']))

        async def run_set():
            return {d
                    for c in [f([f([10, 30]),
                                 f([20])])]
                    for s in await c
                    for d in await s}

        self.assertEqual(
            run_async(run_set()),
            ([], {10, 20, 30}))

        async def run_set2():
            return {await s
                    for c in [f([f(10), f(20)])]
                    for s in await c}

        self.assertEqual(
            run_async(run_set2()),
            ([], {10, 20}))

    def test_comp_3(self):
        async def f(it):
            for i in it:
                yield i

        async def run_list():
            return [i + 1 async for i in f([10, 20])]
        self.assertEqual(
            run_async(run_list()),
            ([], [11, 21]))

        async def run_set():
            return {i + 1 async for i in f([10, 20])}
        self.assertEqual(
            run_async(run_set()),
            ([], {11, 21}))

        async def run_dict():
            return {i + 1: i + 2 async for i in f([10, 20])}
        self.assertEqual(
            run_async(run_dict()),
            ([], {11: 12, 21: 22}))

        async def run_gen():
            gen = (i + 1 async for i in f([10, 20]))
            return [g + 100 async for g in gen]
        self.assertEqual(
            run_async(run_gen()),
            ([], [111, 121]))

    def test_comp_4(self):
        async def f(it):
            for i in it:
                yield i

        async def run_list():
            return [i + 1 async for i in f([10, 20]) if i > 10]
        self.assertEqual(
            run_async(run_list()),
            ([], [21]))

        async def run_set():
            return {i + 1 async for i in f([10, 20]) if i > 10}
        self.assertEqual(
            run_async(run_set()),
            ([], {21}))

        async def run_dict():
            return {i + 1: i + 2 async for i in f([10, 20]) if i > 10}
        self.assertEqual(
            run_async(run_dict()),
            ([], {21: 22}))

        async def run_gen():
            gen = (i + 1 async for i in f([10, 20]) if i > 10)
            return [g + 100 async for g in gen]
        self.assertEqual(
            run_async(run_gen()),
            ([], [121]))

    def test_comp_4_2(self):
        async def f(it):
            for i in it:
                yield i

        async def run_list():
            return [i + 10 async for i in f(range(5)) if 0 < i < 4]
        self.assertEqual(
            run_async(run_list()),
            ([], [11, 12, 13]))

        async def run_set():
            return {i + 10 async for i in f(range(5)) if 0 < i < 4}
        self.assertEqual(
            run_async(run_set()),
            ([], {11, 12, 13}))

        async def run_dict():
            return {i + 10: i + 100 async for i in f(range(5)) if 0 < i < 4}
        self.assertEqual(
            run_async(run_dict()),
            ([], {11: 101, 12: 102, 13: 103}))

        async def run_gen():
            gen = (i + 10 async for i in f(range(5)) if 0 < i < 4)
            return [g + 100 async for g in gen]
        self.assertEqual(
            run_async(run_gen()),
            ([], [111, 112, 113]))

    def test_comp_5(self):
        async def f(it):
            for i in it:
                yield i

        async def run_list():
            return [i + 1 for pair in ([10, 20], [30, 40]) if pair[0] > 10
                    async for i in f(pair) if i > 30]
        self.assertEqual(
            run_async(run_list()),
            ([], [41]))

    def test_comp_6(self):
        async def f(it):
            for i in it:
                yield i

        async def run_list():
            return [i + 1 async for seq in f([(10, 20), (30,)])
                    for i in seq]

        self.assertEqual(
            run_async(run_list()),
            ([], [11, 21, 31]))

    def test_comp_7(self):
        async def f():
            yield 1
            yield 2
            raise Exception('aaa')

        async def run_list():
            return [i async for i in f()]

        with self.assertRaisesRegex(Exception, 'aaa'):
            run_async(run_list())

    def test_comp_8(self):
        async def f():
            return [i for i in [1, 2, 3]]

        self.assertEqual(
            run_async(f()),
            ([], [1, 2, 3]))

    def test_comp_9(self):
        async def gen():
            yield 1
            yield 2
        async def f():
            l = [i async for i in gen()]
            return [i for i in l]

        self.assertEqual(
            run_async(f()),
            ([], [1, 2]))

    def test_comp_10(self):
        async def f():
            xx = {i for i in [1, 2, 3]}
            return {x: x for x in xx}

        self.assertEqual(
            run_async(f()),
            ([], {1: 1, 2: 2, 3: 3}))

    def test_nested_comp(self):
        async def run_list_inside_list():
            return [[i + j async for i in asynciter([1, 2])] for j in [10, 20]]
        self.assertEqual(
            run_async(run_list_inside_list()),
            ([], [[11, 12], [21, 22]]))

        async def run_set_inside_list():
            return [{i + j async for i in asynciter([1, 2])} for j in [10, 20]]
        self.assertEqual(
            run_async(run_set_inside_list()),
            ([], [{11, 12}, {21, 22}]))

        async def run_list_inside_set():
            return {sum([i async for i in asynciter(range(j))]) for j in [3, 5]}
        self.assertEqual(
            run_async(run_list_inside_set()),
            ([], {3, 10}))

        async def run_dict_inside_dict():
            return {j: {i: i + j async for i in asynciter([1, 2])} for j in [10, 20]}
        self.assertEqual(
            run_async(run_dict_inside_dict()),
            ([], {10: {1: 11, 2: 12}, 20: {1: 21, 2: 22}}))

        async def run_list_inside_gen():
            gen = ([i + j async for i in asynciter([1, 2])] for j in [10, 20])
            return [x async for x in gen]
        self.assertEqual(
            run_async(run_list_inside_gen()),
            ([], [[11, 12], [21, 22]]))

        async def run_gen_inside_list():
            gens = [(i async for i in asynciter(range(j))) for j in [3, 5]]
            return [x for g in gens async for x in g]
        self.assertEqual(
            run_async(run_gen_inside_list()),
            ([], [0, 1, 2, 0, 1, 2, 3, 4]))

        async def run_gen_inside_gen():
            gens = ((i async for i in asynciter(range(j))) for j in [3, 5])
            return [x for g in gens async for x in g]
        self.assertEqual(
            run_async(run_gen_inside_gen()),
            ([], [0, 1, 2, 0, 1, 2, 3, 4]))

        async def run_list_inside_list_inside_list():
            return [[[i + j + k async for i in asynciter([1, 2])]
                     for j in [10, 20]]
                    for k in [100, 200]]
        self.assertEqual(
            run_async(run_list_inside_list_inside_list()),
            ([], [[[111, 112], [121, 122]], [[211, 212], [221, 222]]]))

    def test_for_assign_raising_stop_async_iteration(self):
        class BadTarget:
            def __setitem__(self, key, value):
                raise StopAsyncIteration(42)
        tgt = BadTarget()
        async def source():
            yield 10

        async def run_for():
            with self.assertRaises(StopAsyncIteration) as cm:
                async for tgt[0] in source():
                    pass
            self.assertEqual(cm.exception.args, (42,))
            return 'end'
        self.assertEqual(run_async(run_for()), ([], 'end'))

        async def run_list():
            with self.assertRaises(StopAsyncIteration) as cm:
                return [0 async for tgt[0] in source()]
            self.assertEqual(cm.exception.args, (42,))
            return 'end'
        self.assertEqual(run_async(run_list()), ([], 'end'))

        async def run_gen():
            gen = (0 async for tgt[0] in source())
            a = gen.asend(None)
            with self.assertRaises(RuntimeError) as cm:
                await a
            self.assertIsInstance(cm.exception.__cause__, StopAsyncIteration)
            self.assertEqual(cm.exception.__cause__.args, (42,))
            return 'end'
        self.assertEqual(run_async(run_gen()), ([], 'end'))

    def test_for_assign_raising_stop_async_iteration_2(self):
        class BadIterable:
            def __iter__(self):
                raise StopAsyncIteration(42)
        async def badpairs():
            yield BadIterable()

        async def run_for():
            with self.assertRaises(StopAsyncIteration) as cm:
                async for i, j in badpairs():
                    pass
            self.assertEqual(cm.exception.args, (42,))
            return 'end'
        self.assertEqual(run_async(run_for()), ([], 'end'))

        async def run_list():
            with self.assertRaises(StopAsyncIteration) as cm:
                return [0 async for i, j in badpairs()]
            self.assertEqual(cm.exception.args, (42,))
            return 'end'
        self.assertEqual(run_async(run_list()), ([], 'end'))

        async def run_gen():
            gen = (0 async for i, j in badpairs())
            a = gen.asend(None)
            with self.assertRaises(RuntimeError) as cm:
                await a
            self.assertIsInstance(cm.exception.__cause__, StopAsyncIteration)
            self.assertEqual(cm.exception.__cause__.args, (42,))
            return 'end'
        self.assertEqual(run_async(run_gen()), ([], 'end'))


    def test_func_5(self):
        @types.coroutine
        def bar():
            yield 1

        async def foo():
            await bar()

        check = lambda: self.assertRaisesRegex(
            TypeError, "'coroutine' object is not iterable")

        coro = foo()
        with check():
            for el in coro:
                pass
        coro.close()

        # the following should pass without an error
        for el in bar():
            self.assertEqual(el, 1)
        self.assertEqual([el for el in bar()], [1])
        self.assertEqual(tuple(bar()), (1,))
        self.assertEqual(next(iter(bar())), 1)

    def test_func_6(self):
        @types.coroutine
        def bar():
            yield 1
            yield 2

        async def foo():
            await bar()

        f = foo()
        self.assertEqual(f.send(None), 1)
        self.assertEqual(f.send(None), 2)
        with self.assertRaises(StopIteration):
            f.send(None)

    def test_func_8(self):
        @types.coroutine
        def bar():
            return (yield from coro)

        async def foo():
            return 'spam'

        coro = foo()
        self.assertEqual(run_async(bar()), ([], 'spam'))
        coro.close()

    def test_func_14(self):
        @types.coroutine
        def gen():
            yield
        async def coro():
            try:
                await gen()
            except GeneratorExit:
                await gen()
        c = coro()
        c.send(None)
        with self.assertRaisesRegex(RuntimeError,
                                    "coroutine ignored GeneratorExit"):
            c.close()

    def test_func_16(self):
        # See http://bugs.python.org/issue25887 for details

        @types.coroutine
        def nop():
            yield
        async def send():
            await nop()
            return 'spam'
        async def read(coro):
            await nop()
            return await coro

        spammer = send()

        reader = read(spammer)
        reader.send(None)
        reader.send(None)
        with self.assertRaisesRegex(Exception, 'ham'):
            reader.throw(Exception('ham'))

        reader = read(spammer)
        reader.send(None)
        with self.assertRaisesRegex(RuntimeError,
                                    'cannot reuse already awaited coroutine'):
            reader.send(None)

        with self.assertRaisesRegex(RuntimeError,
                                    'cannot reuse already awaited coroutine'):
            reader.throw(Exception('wat'))

    def test_func_19(self):
        CHK = 0

        @types.coroutine
        def foo():
            nonlocal CHK
            yield
            try:
                yield
            except GeneratorExit:
                CHK += 1

        async def coroutine():
            await foo()

        coro = coroutine()

        coro.send(None)
        coro.send(None)

        self.assertEqual(CHK, 0)
        coro.close()
        self.assertEqual(CHK, 1)

        for _ in range(3):
            # Closing a coroutine shouldn't raise any exception even if it's
            # already closed/exhausted (similar to generators)
            coro.close()
            self.assertEqual(CHK, 1)

    def test_await_15(self):
        @types.coroutine
        def nop():
            yield

        async def coroutine():
            await nop()

        async def waiter(coro):
            await coro

        coro = coroutine()
        coro.send(None)

        with self.assertRaisesRegex(RuntimeError,
                                    "coroutine is being awaited already"):
            waiter(coro).send(None)


    def test_async_with_suppression_exception_state(self):
        class Suppress:
            async def __aenter__(self): pass
            async def __aexit__(self, *args): return True
        async def empty():
            async with Suppress(): raise ValueError('suppressed')
            with self.assertRaisesRegex(RuntimeError, 'No active exception'): raise
        self.assertEqual(run_async(empty()), ([], None))
        async def enclosing():
            error = KeyError('outer')
            try: raise error
            except KeyError:
                async with Suppress(): raise ValueError('suppressed')
                try: raise
                except KeyError as caught: self.assertIs(caught, error)
        self.assertEqual(run_async(enclosing()), ([], None))

    def test_async_with_truth_failure_context(self):
        error = ValueError('body')
        class BadTruth:
            def __bool__(self): raise TypeError('truth')
        class Manager:
            async def __aenter__(self): pass
            async def __aexit__(self, *args): return BadTruth()
        async def f():
            async with Manager(): raise error
        with self.assertRaisesRegex(TypeError, 'truth') as cm: run_async(f())
        self.assertIs(cm.exception.__context__, error)

    def test_async_with_missing_exit_lookup_order(self):
        seen = []
        class Enter:
            def __get__(self, obj, owner):
                seen.append('enter lookup')
                return lambda: None
        class Manager:
            __aenter__ = Enter()
        async def f():
            async with Manager(): pass
        with self.assertRaisesRegex(TypeError, '__aexit__'): run_async(f())
        self.assertEqual(seen, [])

    def test_async_iteration_protocol_and_exception_state(self):
        class Iterator:
            def __aiter__(self): return self
            async def __anext__(self): raise StopAsyncIteration
        async def f():
            async for item in Iterator(): pass
            with self.assertRaises(RuntimeError): raise
            error = ValueError('original')
            try: raise error
            except ValueError:
                async for item in Iterator(): pass
                with self.assertRaises(ValueError) as cm: raise
                self.assertIs(cm.exception, error)
        self.assertEqual(run_async(f()), ([], None))
        class BadIterator:
            def __aiter__(self): return self
            def __anext__(self): return ()
        async def invalid(value):
            async for item in value: pass
        for value, message in [((), '__aiter__'), (BadIterator(), '__anext__')]:
            with self.assertRaisesRegex(TypeError, message): run_async(invalid(value))
        class NoNext:
            def __aiter__(self): return self
        with self.assertRaisesRegex(TypeError, 'does not implement __anext__'):
            run_async(invalid(NoNext()))
        class BadValue:
            def __iter__(self): raise StopAsyncIteration('assignment')
        class OneValue:
            def __aiter__(self): return self
            async def __anext__(self): return BadValue()
        async def assignment():
            async for x, y in OneValue(): pass
        with self.assertRaisesRegex(StopAsyncIteration, 'assignment'):
            run_async(assignment())

    def test_with_10(self):
        CNT = 0

        class CM:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *e):
                1/0

        async def foo():
            nonlocal CNT
            async with CM():
                async with CM():
                    raise RuntimeError

        try:
            run_async(foo())
        except ZeroDivisionError as exc:
            self.assertTrue(exc.__context__ is not None)
            self.assertTrue(isinstance(exc.__context__, ZeroDivisionError))
            self.assertTrue(isinstance(exc.__context__.__context__,
                                       RuntimeError))
        else:
            self.fail('exception from __aexit__ did not propagate')

    def test_with_7(self):
        class CM:
            async def __aenter__(self):
                return self

            def __aexit__(self, *e):
                return 444

        # Exit with exception
        async def foo():
            async with CM():
                1/0

        try:
            run_async(foo())
        except TypeError as exc:
            self.assertRegex(
                exc.args[0],
                "'async with' received an object from __aexit__ "
                "that does not implement __await__: int")
            self.assertTrue(exc.__context__ is not None)
            self.assertTrue(isinstance(exc.__context__, ZeroDivisionError))
        else:
            self.fail('invalid asynchronous context manager did not fail')


    # Skulpt's teaching harness normally records failures instead of raising.
    # Upstream test_with_5 deliberately asserts inside assertRaises.
    def appendResult(self, result, actual, expected, feedback):
        if not result:
            raise AssertionError(feedback)
        super().appendResult(result, actual, expected, feedback)


    def test_with_13(self):
        CNT = 0

        class CM:
            async def __aenter__(self):
                1/0

            async def __aexit__(self, *e):
                return True

        async def foo():
            nonlocal CNT
            CNT += 1
            async with CM():
                CNT += 1000
            CNT += 10000

        with self.assertRaises(ZeroDivisionError):
            run_async(foo())
        self.assertEqual(CNT, 1)

    def test_with_12(self):
        CNT = 0

        class CM:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *e):
                return True

        async def foo():
            nonlocal CNT
            async with CM() as cm:
                self.assertIs(cm.__class__, CM)
                raise RuntimeError

        run_async(foo())

    def test_with_11(self):
        CNT = 0

        class CM:
            async def __aenter__(self):
                raise NotImplementedError

            async def __aexit__(self, *e):
                1/0

        async def foo():
            nonlocal CNT
            async with CM():
                raise RuntimeError

        try:
            run_async(foo())
        except NotImplementedError as exc:
            self.assertTrue(exc.__context__ is None)
        else:
            self.fail('exception from __aenter__ did not propagate')

    def test_with_9(self):
        CNT = 0

        class CM:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *e):
                1/0

        async def foo():
            nonlocal CNT
            async with CM():
                CNT += 1

        with self.assertRaises(ZeroDivisionError):
            run_async(foo())

        self.assertEqual(CNT, 1)

    def test_with_8(self):
        CNT = 0

        class CM:
            async def __aenter__(self):
                return self

            def __aexit__(self, *e):
                return 456

        # Normal exit
        async def foo():
            nonlocal CNT
            async with CM():
                CNT += 1
        with self.assertRaisesRegex(
                TypeError,
                "'async with' received an object from __aexit__ "
                "that does not implement __await__: int"):
            run_async(foo())
        self.assertEqual(CNT, 1)

        # Exit with 'break'
        async def foo():
            nonlocal CNT
            for i in range(2):
                async with CM():
                    CNT += 1
                    break
        with self.assertRaisesRegex(
                TypeError,
                "'async with' received an object from __aexit__ "
                "that does not implement __await__: int"):
            run_async(foo())
        self.assertEqual(CNT, 2)

        # Exit with 'continue'
        async def foo():
            nonlocal CNT
            for i in range(2):
                async with CM():
                    CNT += 1
                    continue
        with self.assertRaisesRegex(
                TypeError,
                "'async with' received an object from __aexit__ "
                "that does not implement __await__: int"):
            run_async(foo())
        self.assertEqual(CNT, 3)

        # Exit with 'return'
        async def foo():
            nonlocal CNT
            async with CM():
                CNT += 1
                return
        with self.assertRaisesRegex(
                TypeError,
                "'async with' received an object from __aexit__ "
                "that does not implement __await__: int"):
            run_async(foo())
        self.assertEqual(CNT, 4)


    def test_with_6(self):
        class CM:
            def __aenter__(self):
                return 123

            def __aexit__(self, *e):
                return 456

        async def foo():
            async with CM():
                pass

        with self.assertRaisesRegex(
                TypeError,
                "'async with' received an object from __aenter__ "
                "that does not implement __await__: int"):
            # it's important that __aexit__ wasn't called
            run_async(foo())

    def test_with_5(self):
        # While this test doesn't make a lot of sense,
        # it's a regression test for an early bug with opcodes
        # generation

        class CM:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                pass

        async def func():
            async with CM():
                self.assertEqual((1, ), 1)

        with self.assertRaises(AssertionError):
            run_async(func())

    def test_with_4(self):
        class CM:
            pass

        body_executed = None
        async def foo():
            nonlocal body_executed
            body_executed = False
            async with CM():
                body_executed = True

        with self.assertRaisesRegex(TypeError, 'asynchronous context manager'):
            run_async(foo())
        self.assertIs(body_executed, False)

    def test_with_3(self):
        class CM:
            def __aexit__(self):
                pass

        body_executed = None
        async def foo():
            nonlocal body_executed
            body_executed = False
            async with CM():
                body_executed = True

        with self.assertRaisesRegex(TypeError, 'asynchronous context manager'):
            run_async(foo())
        self.assertIs(body_executed, False)

    def test_with_2(self):
        class CM:
            def __aenter__(self):
                pass

        body_executed = None
        async def foo():
            nonlocal body_executed
            body_executed = False
            async with CM():
                body_executed = True

        with self.assertRaisesRegex(TypeError, 'asynchronous context manager.*__aexit__'):
            run_async(foo())
        self.assertIs(body_executed, False)

    def test_with_1(self):
        class Manager:
            def __init__(self, name):
                self.name = name

            async def __aenter__(self):
                await AsyncYieldFrom(['enter-1-' + self.name,
                                      'enter-2-' + self.name])
                return self

            async def __aexit__(self, *args):
                await AsyncYieldFrom(['exit-1-' + self.name,
                                      'exit-2-' + self.name])

                if self.name == 'B':
                    return True


        async def foo():
            async with Manager("A") as a, Manager("B") as b:
                await AsyncYieldFrom([('managers', a.name, b.name)])
                1/0

        f = foo()
        result, _ = run_async(f)

        self.assertEqual(
            result, ['enter-1-A', 'enter-2-A', 'enter-1-B', 'enter-2-B',
                     ('managers', 'A', 'B'),
                     'exit-1-B', 'exit-2-B', 'exit-1-A', 'exit-2-A']
        )

        async def foo():
            async with Manager("A") as a, Manager("C") as c:
                await AsyncYieldFrom([('managers', a.name, c.name)])
                1/0

        with self.assertRaises(ZeroDivisionError):
            run_async(foo())

    def test_for_stop_iteration(self):
        class Done(Exception): pass

        class AIter(StopIteration):
            i = 0
            def __aiter__(self):
                return self
            async def __anext__(self):
                if self.i:
                    raise StopAsyncIteration
                self.i += 1
                return self.value

        result = []
        async def foo():
            async for i in AIter(42):
                result.append(i)
            raise Done

        with self.assertRaises(Done):
            foo().send(None)
        self.assertEqual(result, [42])

    def test_for_tuple(self):
        class Done(Exception): pass

        class AIter(tuple):
            i = 0
            def __aiter__(self):
                return self
            async def __anext__(self):
                if self.i >= len(self):
                    raise StopAsyncIteration
                self.i += 1
                return self[self.i - 1]

        result = []
        async def foo():
            async for i in AIter([42]):
                result.append(i)
            raise Done

        with self.assertRaises(Done):
            foo().send(None)
        self.assertEqual(result, [42])

    def test_for_11(self):
        class F:
            def __aiter__(self):
                return self
            def __anext__(self):
                return self
            def __await__(self):
                1 / 0

        async def main():
            async for _ in F():
                pass

        with self.assertRaisesRegex(TypeError,
                                    'an invalid object from __anext__') as c:
            main().send(None)

        err = c.exception
        self.assertIsInstance(err.__cause__, ZeroDivisionError)

    def test_for_7(self):
        CNT = 0
        class AI:
            def __aiter__(self):
                1/0
        async def foo():
            nonlocal CNT
            async for i in AI():
                CNT += 1
            CNT += 10
        with self.assertRaises(ZeroDivisionError):
            run_async(foo())
        self.assertEqual(CNT, 0)

    def test_for_1(self):
        aiter_calls = 0

        class AsyncIter:
            def __init__(self):
                self.i = 0

            def __aiter__(self):
                nonlocal aiter_calls
                aiter_calls += 1
                return self

            async def __anext__(self):
                self.i += 1

                if not (self.i % 10):
                    await AsyncYield(self.i * 10)

                if self.i > 100:
                    raise StopAsyncIteration

                return self.i, self.i


        buffer = []
        async def test1():
            async for i1, i2 in AsyncIter():
                buffer.append(i1 + i2)

        yielded, _ = run_async(test1())
        # Make sure that __aiter__ was called only once
        self.assertEqual(aiter_calls, 1)
        self.assertEqual(yielded, [i * 100 for i in range(1, 11)])
        self.assertEqual(buffer, [i*2 for i in range(1, 101)])


        buffer = []
        async def test2():
            nonlocal buffer
            async for i in AsyncIter():
                buffer.append(i[0])
                if i[0] == 20:
                    break
            else:
                buffer.append('what?')
            buffer.append('end')

        yielded, _ = run_async(test2())
        # Make sure that __aiter__ was called only once
        self.assertEqual(aiter_calls, 2)
        self.assertEqual(yielded, [100, 200])
        self.assertEqual(buffer, [i for i in range(1, 21)] + ['end'])


        buffer = []
        async def test3():
            nonlocal buffer
            async for i in AsyncIter():
                if i[0] > 20:
                    continue
                buffer.append(i[0])
            else:
                buffer.append('what?')
            buffer.append('end')

        yielded, _ = run_async(test3())
        # Make sure that __aiter__ was called only once
        self.assertEqual(aiter_calls, 3)
        self.assertEqual(yielded, [i * 100 for i in range(1, 11)])
        self.assertEqual(buffer, [i for i in range(1, 21)] +
                                 ['what?', 'end'])

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
