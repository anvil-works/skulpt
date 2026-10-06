# CPython 3.14 Lib/test/test_contextlib_async.py at 18ef0f0cb52.
# Complete selected bodies and no-yield coroutine harness are unchanged.
# Slots and traceback formatting await their runtime features.
import functools
from contextlib import (asynccontextmanager, AbstractAsyncContextManager,
                        nullcontext, aclosing, contextmanager)
from test_contextlib import ContextAssertions, support

def _run_async_fn(async_fn, /, *args, **kwargs):
    coro = async_fn(*args, **kwargs)
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    else:
        raise AssertionError("coroutine did not complete")
    finally:
        coro.close()


def _async_test(async_fn):
    """Decorator to turn an async function into a synchronous function"""
    @functools.wraps(async_fn)
    def wrapper(*args, **kwargs):
        return _run_async_fn(async_fn, *args, **kwargs)

    return wrapper


class TestAbstractAsyncContextManager(ContextAssertions):

    @_async_test
    async def test_enter(self):
        class DefaultEnter(AbstractAsyncContextManager):
            async def __aexit__(self, *args):
                await super().__aexit__(*args)

        manager = DefaultEnter()
        self.assertIs(await manager.__aenter__(), manager)

        async with manager as context:
            self.assertIs(manager, context)


    @_async_test
    async def test_async_gen_propagates_generator_exit(self):
        # A regression test for https://bugs.python.org/issue33786.

        @asynccontextmanager
        async def ctx():
            yield

        async def gen():
            async with ctx():
                yield 11

        g = gen()
        async for val in g:
            self.assertEqual(val, 11)
            break
        await g.aclose()

    def test_exit_is_abstract(self):
        class MissingAexit(AbstractAsyncContextManager):
            pass

        with self.assertRaises(TypeError):
            MissingAexit()

    def test_structural_subclassing(self):
        class ManagerFromScratch:
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc_value, traceback):
                return None

        self.assertIsSubclass(ManagerFromScratch, AbstractAsyncContextManager)

        class DefaultEnter(AbstractAsyncContextManager):
            async def __aexit__(self, *args):
                await super().__aexit__(*args)

        self.assertIsSubclass(DefaultEnter, AbstractAsyncContextManager)

        class NoneAenter(ManagerFromScratch):
            __aenter__ = None

        self.assertNotIsSubclass(NoneAenter, AbstractAsyncContextManager)

        class NoneAexit(ManagerFromScratch):
            __aexit__ = None

        self.assertNotIsSubclass(NoneAexit, AbstractAsyncContextManager)


class AsyncContextManagerTestCase(ContextAssertions):

    @_async_test
    async def test_contextmanager_plain(self):
        state = []
        @asynccontextmanager
        async def woohoo():
            state.append(1)
            yield 42
            state.append(999)
        async with woohoo() as x:
            self.assertEqual(state, [1])
            self.assertEqual(x, 42)
            state.append(x)
        self.assertEqual(state, [1, 42, 999])

    @_async_test
    async def test_contextmanager_finally(self):
        state = []
        @asynccontextmanager
        async def woohoo():
            state.append(1)
            try:
                yield 42
            finally:
                state.append(999)
        with self.assertRaises(ZeroDivisionError):
            async with woohoo() as x:
                self.assertEqual(state, [1])
                self.assertEqual(x, 42)
                state.append(x)
                raise ZeroDivisionError()
        self.assertEqual(state, [1, 42, 999])


    @_async_test
    async def test_contextmanager_no_reraise(self):
        @asynccontextmanager
        async def whee():
            yield
        ctx = whee()
        await ctx.__aenter__()
        # Calling __aexit__ should not result in an exception
        self.assertFalse(await ctx.__aexit__(TypeError, TypeError("foo"), None))

    @_async_test
    async def test_contextmanager_trap_yield_after_throw(self):
        @asynccontextmanager
        async def whoo():
            try:
                yield
            except:
                yield
        ctx = whoo()
        await ctx.__aenter__()
        with self.assertRaises(RuntimeError):
            await ctx.__aexit__(TypeError, TypeError('foo'), None)
        if support.check_impl_detail(cpython=True):
            # The "gen" attribute is an implementation detail.
            self.assertFalse(ctx.gen.ag_suspended)

    @_async_test
    async def test_contextmanager_trap_no_yield(self):
        @asynccontextmanager
        async def whoo():
            if False:
                yield
        ctx = whoo()
        with self.assertRaises(RuntimeError):
            await ctx.__aenter__()

    @_async_test
    async def test_contextmanager_trap_second_yield(self):
        @asynccontextmanager
        async def whoo():
            yield
            yield
        ctx = whoo()
        await ctx.__aenter__()
        with self.assertRaises(RuntimeError):
            await ctx.__aexit__(None, None, None)
        if support.check_impl_detail(cpython=True):
            # The "gen" attribute is an implementation detail.
            self.assertFalse(ctx.gen.ag_suspended)

    @_async_test
    async def test_contextmanager_non_normalised(self):
        @asynccontextmanager
        async def whoo():
            try:
                yield
            except RuntimeError:
                raise SyntaxError

        ctx = whoo()
        await ctx.__aenter__()
        with self.assertRaises(SyntaxError):
            await ctx.__aexit__(RuntimeError, None, None)

    @_async_test
    async def test_contextmanager_except(self):
        state = []
        @asynccontextmanager
        async def woohoo():
            state.append(1)
            try:
                yield 42
            except ZeroDivisionError as e:
                state.append(e.args[0])
                self.assertEqual(state, [1, 42, 999])
        async with woohoo() as x:
            self.assertEqual(state, [1])
            self.assertEqual(x, 42)
            state.append(x)
            raise ZeroDivisionError(999)
        self.assertEqual(state, [1, 42, 999])

    @_async_test
    async def test_contextmanager_except_stopiter(self):
        @asynccontextmanager
        async def woohoo():
            yield

        class StopIterationSubclass(StopIteration):
            pass

        class StopAsyncIterationSubclass(StopAsyncIteration):
            pass

        for stop_exc in (
            StopIteration('spam'),
            StopAsyncIteration('ham'),
            StopIterationSubclass('spam'),
            StopAsyncIterationSubclass('spam')
        ):
            with self.subTest(type=type(stop_exc)):
                try:
                    async with woohoo():
                        raise stop_exc
                except Exception as ex:
                    self.assertIs(ex, stop_exc)
                else:
                    self.fail(f'{stop_exc} was suppressed')

    @_async_test
    async def test_contextmanager_wrap_runtimeerror(self):
        @asynccontextmanager
        async def woohoo():
            try:
                yield
            except Exception as exc:
                raise RuntimeError(f'caught {exc}') from exc

        with self.assertRaises(RuntimeError):
            async with woohoo():
                1 / 0

        # If the context manager wrapped StopAsyncIteration in a RuntimeError,
        # we also unwrap it, because we can't tell whether the wrapping was
        # done by the generator machinery or by the generator itself.
        with self.assertRaises(StopAsyncIteration):
            async with woohoo():
                raise StopAsyncIteration

    def _create_contextmanager_attribs(self):
        def attribs(**kw):
            def decorate(func):
                for k,v in kw.items():
                    setattr(func,k,v)
                return func
            return decorate
        @asynccontextmanager
        @attribs(foo='bar')
        async def baz(spam):
            """Whee!"""
            yield
        return baz

    def test_contextmanager_attribs(self):
        baz = self._create_contextmanager_attribs()
        self.assertEqual(baz.__name__,'baz')
        self.assertEqual(baz.foo, 'bar')

    def test_contextmanager_doc_attrib(self):
        baz = self._create_contextmanager_attribs()
        self.assertEqual(baz.__doc__, "Whee!")

    @_async_test
    async def test_instance_docstring_given_cm_docstring(self):
        baz = self._create_contextmanager_attribs()(None)
        self.assertEqual(baz.__doc__, "Whee!")
        async with baz:
            pass  # suppress warning

    @_async_test
    async def test_keywords(self):
        # Ensure no keyword arguments are inhibited
        @asynccontextmanager
        async def woohoo(self, func, args, kwds):
            yield (self, func, args, kwds)
        async with woohoo(self=11, func=22, args=33, kwds=44) as target:
            self.assertEqual(target, (11, 22, 33, 44))

    @_async_test
    async def test_recursive(self):
        depth = 0
        ncols = 0

        @asynccontextmanager
        async def woohoo():
            nonlocal ncols
            ncols += 1

            nonlocal depth
            before = depth
            depth += 1
            yield
            depth -= 1
            self.assertEqual(depth, before)

        @woohoo()
        async def recursive():
            if depth < 10:
                await recursive()

        await recursive()

        self.assertEqual(ncols, 10)
        self.assertEqual(depth, 0)

    @_async_test
    async def test_decorator(self):
        entered = False

        @asynccontextmanager
        async def context():
            nonlocal entered
            entered = True
            yield
            entered = False

        @context()
        async def test():
            self.assertTrue(entered)

        self.assertFalse(entered)
        await test()
        self.assertFalse(entered)

    @_async_test
    async def test_decorator_with_exception(self):
        entered = False

        @asynccontextmanager
        async def context():
            nonlocal entered
            try:
                entered = True
                yield
            finally:
                entered = False

        @context()
        async def test():
            self.assertTrue(entered)
            raise NameError('foo')

        self.assertFalse(entered)
        with self.assertRaisesRegex(NameError, 'foo'):
            await test()
        self.assertFalse(entered)

    @_async_test
    async def test_decorating_method(self):

        @asynccontextmanager
        async def context():
            yield


        class Test(object):

            @context()
            async def method(self, a, b, c=None):
                self.a = a
                self.b = b
                self.c = c

        # these tests are for argument passing when used as a decorator
        test = Test()
        await test.method(1, 2)
        self.assertEqual(test.a, 1)
        self.assertEqual(test.b, 2)
        self.assertEqual(test.c, None)

        test = Test()
        await test.method('a', 'b', 'c')
        self.assertEqual(test.a, 'a')
        self.assertEqual(test.b, 'b')
        self.assertEqual(test.c, 'c')

        test = Test()
        await test.method(a=1, b=2)
        self.assertEqual(test.a, 1)
        self.assertEqual(test.b, 2)


class AclosingTestCase(ContextAssertions):

    def test_instance_docs(self):
        cm_docstring = aclosing.__doc__
        obj = aclosing(None)
        self.assertEqual(obj.__doc__, cm_docstring)

    @_async_test
    async def test_aclosing(self):
        state = []
        class C:
            async def aclose(self):
                state.append(1)
        x = C()
        self.assertEqual(state, [])
        async with aclosing(x) as y:
            self.assertEqual(x, y)
        self.assertEqual(state, [1])

    @_async_test
    async def test_aclosing_error(self):
        state = []
        class C:
            async def aclose(self):
                state.append(1)
        x = C()
        self.assertEqual(state, [])
        with self.assertRaises(ZeroDivisionError):
            async with aclosing(x) as y:
                self.assertEqual(x, y)
                1 / 0
        self.assertEqual(state, [1])

    @_async_test
    async def test_aclosing_bpo41229(self):
        state = []

        @contextmanager
        def sync_resource():
            try:
                yield
            finally:
                state.append(1)

        async def agenfunc():
            with sync_resource():
                yield -1
                yield -2

        x = agenfunc()
        self.assertEqual(state, [])
        with self.assertRaises(ZeroDivisionError):
            async with aclosing(x) as y:
                self.assertEqual(x, y)
                self.assertEqual(-1, await x.__anext__())
                1 / 0
        self.assertEqual(state, [1])


class TestAsyncNullcontext(ContextAssertions):
    @_async_test
    async def test_async_nullcontext(self):
        class C:
            pass
        c = C()
        async with nullcontext(c) as c_in:
            self.assertIs(c_in, c)


if __name__ == '__main__':
    import unittest
    unittest.main()
