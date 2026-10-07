# Unchanged CPython 3.14 BuiltinTest methods at 18ef0f0cb52.
import types
import unittest
import sys
from itertools import product
from textwrap import dedent
from types import AsyncGeneratorType, FunctionType

# Numeric compiler/inspect constants are fixtures until these modules are ported.
class ast:
    PyCF_ALLOW_TOP_LEVEL_AWAIT = 0x2000
CO_COROUTINE = 0x80

@types.coroutine
def async_yield(v):
    return (yield v)


def run_yielding_async_fn(async_fn, /, *args, **kwargs):
    coro = async_fn(*args, **kwargs)
    try:
        while True:
            try:
                coro.send(None)
            except StopIteration as e:
                return e.value
    finally:
        coro.close()


# Harness: retain subTest assertions and exceptions without grouped reporting.
class SubTest:
    def __enter__(self): pass
    def __exit__(self, *args): return False

class TopLevelAwaitTest(unittest.TestCase):
    def test_expression_result_and_deferred_module_namespaces(self):
        class Pause:
            def __init__(self, value): self.value = value
            def __await__(self):
                yield 'pause'
                return self.value
        co = compile('await Pause(42)', 'expression.py', 'eval', flags=0x2000)
        for create in [lambda: eval(co, {'Pause': Pause}),
                       lambda: FunctionType(co, {'Pause': Pause})()]:
            c = create()
            self.assertIs(type(c), types.CoroutineType)
            self.assertIs(c.cr_code, co)
            self.assertEqual(c.send(None), 'pause')
            with self.assertRaises(StopIteration) as cm: c.send(None)
            self.assertEqual(cm.exception.value, 42)
        co = compile('answer = await Pause(9); size = len(())', 'module.py', 'exec', flags=0x2000)
        globals_ = {'__builtins__': {'Pause': Pause, 'len': len}}
        locals_ = {}
        c = eval(co, globals_, locals_)
        self.assertEqual(locals_, {})
        globals_['__builtins__'] = {}
        self.assertEqual(c.send(None), 'pause')
        self.assertEqual(locals_, {})
        with self.assertRaises(StopIteration): c.send(None)
        self.assertEqual(locals_, {'answer': 9, 'size': 0})
        self.assertNotIn('answer', globals_)

    def test_interactive_await_display_and_flag_boundary(self):
        seen = []
        old = sys.displayhook
        async def value(): return 7
        try:
            sys.displayhook = seen.append
            co = compile('await value()', 'interactive.py', 'single', flags=0x2000)
            c = eval(co, {'value': value})
            self.assertEqual(seen, [])
            with self.assertRaises(StopIteration): c.send(None)
            self.assertEqual(seen, [7])
        finally: sys.displayhook = old
        for source in ['yield 1', 'return 1', 'def f():\n    await value()',
                       'class C:\n    await value()']:
            with self.assertRaises(SyntaxError): compile(source, 'bad.py', 'exec', flags=0x2000)

    def subTest(self, *args, **kwargs): return SubTest()
    # Skulpt calls unittest's diagnostic argument feedback rather than msg.
    def assertEqual(self, first, second, msg=None):
        return super().assertEqual(first, second, msg)
    def assertNotEqual(self, first, second, msg=None):
        return super().assertNotEqual(first, second, msg)
    def test_compile_top_level_await_no_coro(self):
        """Make sure top level non-await codes get the correct coroutine flags"""
        modes = ('single', 'exec')
        code_samples = [
            '''def f():pass\n''',
            '''[x for x in l]''',
            '''{x for x in l}''',
            '''(x for x in l)''',
            '''{x:x for x in l}''',
        ]
        for mode, code_sample in product(modes, code_samples):
            source = dedent(code_sample)
            co = compile(source,
                            '?',
                            mode,
                            flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)

            self.assertNotEqual(co.co_flags & CO_COROUTINE, CO_COROUTINE,
                                msg=f"source={source} mode={mode}")

    def test_compile_top_level_await(self):
        """Test whether code with top level await can be compiled.

        Make sure it compiles only with the PyCF_ALLOW_TOP_LEVEL_AWAIT flag
        set, and make sure the generated code object has the CO_COROUTINE flag
        set in order to execute it with  `await eval(.....)` instead of exec,
        or via a FunctionType.
        """

        # helper function just to check we can run top=level async-for
        async def arange(n):
            for i in range(n):
                yield i

        class Lock:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc_info):
                pass

        async def sleep(delay, result=None):
            assert delay == 0
            await async_yield(None)
            return result

        modes = ('single', 'exec')
        optimizations = (-1, 0, 1, 2)
        code_samples = [
            '''a = await sleep(0, result=1)''',
            '''async for i in arange(1):
                   a = 1''',
            '''async with Lock() as l:
                   a = 1''',
            '''a = [x async for x in arange(2)][1]''',
            '''a = 1 in {x async for x in arange(2)}''',
            '''a = {x:1 async for x in arange(1)}[0]''',
            '''a = [x async for x in arange(2) async for x in arange(2)][1]''',
            '''a = [x async for x in (x async for x in arange(5))][1]''',
            '''a, = [1 for x in {x async for x in arange(1)}]''',
            '''a = [await sleep(0, x) async for x in arange(2)][1]''',
            '''a = [await sleep(0, 1) for _ in [0]][0]''',
            '''a = {await sleep(0, 1) for _ in [0]}.pop()''',
            '''a = {0: await sleep(0, 1) for _ in [0]}[0]''',
            '''a = (lambda x=[await sleep(0, 1) for _ in [0]]: x)()[0]''',
            # gh-121637: Make sure we correctly handle the case where the
            # async code is optimized away
            '''assert not await sleep(0); a = 1''',
            '''assert [x async for x in arange(1)]; a = 1''',
            '''assert {x async for x in arange(1)}; a = 1''',
            '''assert {x: x async for x in arange(1)}; a = 1''',
            '''
            if (a := 1) and __debug__:
                async with Lock() as l:
                    pass
            ''',
            '''
            if (a := 1) and __debug__:
                async for x in arange(2):
                    pass
            ''',
        ]
        for mode, code_sample, optimize in product(modes, code_samples, optimizations):
            with self.subTest(mode=mode, code_sample=code_sample, optimize=optimize):
                source = dedent(code_sample)
                with self.assertRaises(
                        SyntaxError, msg=f"source={source} mode={mode}"):
                    compile(source, '?', mode, optimize=optimize)

                co = compile(source,
                            '?',
                            mode,
                            flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
                            optimize=optimize)

                self.assertEqual(co.co_flags & CO_COROUTINE, CO_COROUTINE,
                                msg=f"source={source} mode={mode}")

                # test we can create and  advance a function type
                globals_ = {'Lock': Lock, 'a': 0, 'arange': arange, 'sleep': sleep}
                run_yielding_async_fn(FunctionType(co, globals_))
                self.assertEqual(globals_['a'], 1)

                # test we can await-eval,
                globals_ = {'Lock': Lock, 'a': 0, 'arange': arange, 'sleep': sleep}
                run_yielding_async_fn(lambda: eval(co, globals_))
                self.assertEqual(globals_['a'], 1)

    def test_compile_top_level_await_invalid_cases(self):
         # helper function just to check we can run top=level async-for
        async def arange(n):
            for i in range(n):
                yield i

        class Lock:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc_info):
                pass

        modes = ('single', 'exec')
        code_samples = [
            '''def f():  await arange(10)\n''',
            '''def f():  [x async for x in arange(10)]\n''',
            '''def f():  [await x async for x in arange(10)]\n''',
            '''def f():
                   async for i in arange(1):
                       a = 1
            ''',
            '''def f():
                   async with Lock() as l:
                       a = 1
            ''',
            '''class C:
                   [await x for x in y]
            ''',
            '''class C:
                   [x async for x in arange(10)]
            ''',
            '''async def f():
                   class C:
                       [await x for x in y]
            ''',
            '''lambda: [await x for x in y]''',
            '''class C:
                   def f(self, x=[await y for y in z]):
                       pass
            ''',
            '''type T = [await x for x in y]''',
            '''async def f[T=[await x for x in y]]():
                   pass
            ''',
        ]
        for mode, code_sample in product(modes, code_samples):
            source = dedent(code_sample)
            with self.assertRaises(
                    SyntaxError, msg=f"source={source} mode={mode}"):
                compile(source, '?', mode)

            with self.assertRaises(
                    SyntaxError, msg=f"source={source} mode={mode}"):
                co = compile(source,
                         '?',
                         mode,
                         flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)

    def test_compile_async_generator(self):
        """
        With the PyCF_ALLOW_TOP_LEVEL_AWAIT flag added in 3.8, we want to
        make sure AsyncGenerators are still properly not marked with the
        CO_COROUTINE flag.
        """
        code = dedent("""async def ticker():
                for i in range(10):
                    yield i
                    await sleep(0)""")

        co = compile(code, '?', 'exec', flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        glob = {}
        exec(co, glob)
        self.assertEqual(type(glob['ticker']()), AsyncGeneratorType)


if __name__ == '__main__': unittest.main()
