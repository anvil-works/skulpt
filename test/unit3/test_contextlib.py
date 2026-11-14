# CPython 3.14 Lib/test/test_contextlib.py at 18ef0f0cb52.
# Complete selected test bodies unchanged. Docstring decorators are omitted;
# assertion/subTest and implementation-detail helpers are adapted.
# Slots, traceback formatting and weakref/GC tests await those runtime features.
import unittest
from contextlib import *
from test_type_parameters import SubTest

class Support:
    def check_impl_detail(self, **kwargs): return True
support = Support()

class ContextAssertions(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def assertIsSubclass(self, cls, base): self.assertTrue(issubclass(cls, base))
    def assertNotIsSubclass(self, cls, base): self.assertFalse(issubclass(cls, base))

class TestAbstractContextManager(ContextAssertions):

    def test_enter(self):
        class DefaultEnter(AbstractContextManager):
            def __exit__(self, *args):
                super().__exit__(*args)

        manager = DefaultEnter()
        self.assertIs(manager.__enter__(), manager)


    def test_exit_is_abstract(self):
        class MissingExit(AbstractContextManager):
            pass

        with self.assertRaises(TypeError):
            MissingExit()

    def test_structural_subclassing(self):
        class ManagerFromScratch:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_value, traceback):
                return None

        self.assertIsSubclass(ManagerFromScratch, AbstractContextManager)

        class DefaultEnter(AbstractContextManager):
            def __exit__(self, *args):
                super().__exit__(*args)

        self.assertIsSubclass(DefaultEnter, AbstractContextManager)

        class NoEnter(ManagerFromScratch):
            __enter__ = None

        self.assertNotIsSubclass(NoEnter, AbstractContextManager)

        class NoExit(ManagerFromScratch):
            __exit__ = None

        self.assertNotIsSubclass(NoExit, AbstractContextManager)


class ContextManagerTestCase(ContextAssertions):

    def test_contextmanager_plain(self):
        state = []
        @contextmanager
        def woohoo():
            state.append(1)
            yield 42
            state.append(999)
        with woohoo() as x:
            self.assertEqual(state, [1])
            self.assertEqual(x, 42)
            state.append(x)
        self.assertEqual(state, [1, 42, 999])

    def test_contextmanager_finally(self):
        state = []
        @contextmanager
        def woohoo():
            state.append(1)
            try:
                yield 42
            finally:
                state.append(999)
        with self.assertRaises(ZeroDivisionError):
            with woohoo() as x:
                self.assertEqual(state, [1])
                self.assertEqual(x, 42)
                state.append(x)
                raise ZeroDivisionError()
        self.assertEqual(state, [1, 42, 999])


    def test_contextmanager_no_reraise(self):
        @contextmanager
        def whee():
            yield
        ctx = whee()
        ctx.__enter__()
        # Calling __exit__ should not result in an exception
        self.assertFalse(ctx.__exit__(TypeError, TypeError("foo"), None))

    def test_contextmanager_trap_yield_after_throw(self):
        @contextmanager
        def whoo():
            try:
                yield
            except:
                yield
        ctx = whoo()
        ctx.__enter__()
        with self.assertRaises(RuntimeError):
            ctx.__exit__(TypeError, TypeError("foo"), None)
        if support.check_impl_detail(cpython=True):
            # The "gen" attribute is an implementation detail.
            self.assertFalse(ctx.gen.gi_suspended)

    def test_contextmanager_trap_no_yield(self):
        @contextmanager
        def whoo():
            if False:
                yield
        ctx = whoo()
        with self.assertRaises(RuntimeError):
            ctx.__enter__()

    def test_contextmanager_trap_second_yield(self):
        @contextmanager
        def whoo():
            yield
            yield
        ctx = whoo()
        ctx.__enter__()
        with self.assertRaises(RuntimeError):
            ctx.__exit__(None, None, None)
        if support.check_impl_detail(cpython=True):
            # The "gen" attribute is an implementation detail.
            self.assertFalse(ctx.gen.gi_suspended)

    def test_contextmanager_non_normalised(self):
        @contextmanager
        def whoo():
            try:
                yield
            except RuntimeError:
                raise SyntaxError

        ctx = whoo()
        ctx.__enter__()
        with self.assertRaises(SyntaxError):
            ctx.__exit__(RuntimeError, None, None)

    def test_contextmanager_except(self):
        state = []
        @contextmanager
        def woohoo():
            state.append(1)
            try:
                yield 42
            except ZeroDivisionError as e:
                state.append(e.args[0])
                self.assertEqual(state, [1, 42, 999])
        with woohoo() as x:
            self.assertEqual(state, [1])
            self.assertEqual(x, 42)
            state.append(x)
            raise ZeroDivisionError(999)
        self.assertEqual(state, [1, 42, 999])

    def test_contextmanager_except_stopiter(self):
        @contextmanager
        def woohoo():
            yield

        class StopIterationSubclass(StopIteration):
            pass

        for stop_exc in (StopIteration('spam'), StopIterationSubclass('spam')):
            with self.subTest(type=type(stop_exc)):
                try:
                    with woohoo():
                        raise stop_exc
                except Exception as ex:
                    self.assertIs(ex, stop_exc)
                else:
                    self.fail(f'{stop_exc} was suppressed')

    def test_contextmanager_except_pep479(self):
        code = """\
from __future__ import generator_stop
from contextlib import contextmanager
@contextmanager
def woohoo():
    yield
"""
        locals = {}
        exec(code, locals, locals)
        woohoo = locals['woohoo']

        stop_exc = StopIteration('spam')
        try:
            with woohoo():
                raise stop_exc
        except Exception as ex:
            self.assertIs(ex, stop_exc)
        else:
            self.fail('StopIteration was suppressed')

    def test_contextmanager_do_not_unchain_non_stopiteration_exceptions(self):
        @contextmanager
        def test_issue29692():
            try:
                yield
            except Exception as exc:
                raise RuntimeError('issue29692:Chained') from exc
        try:
            with test_issue29692():
                raise ZeroDivisionError
        except Exception as ex:
            self.assertIs(type(ex), RuntimeError)
            self.assertEqual(ex.args[0], 'issue29692:Chained')
            self.assertIsInstance(ex.__cause__, ZeroDivisionError)

        try:
            with test_issue29692():
                raise StopIteration('issue29692:Unchained')
        except Exception as ex:
            self.assertIs(type(ex), StopIteration)
            self.assertEqual(ex.args[0], 'issue29692:Unchained')
            self.assertIsNone(ex.__cause__)

    def test_contextmanager_wrap_runtimeerror(self):
        @contextmanager
        def woohoo():
            try:
                yield
            except Exception as exc:
                raise RuntimeError(f'caught {exc}') from exc

        with self.assertRaises(RuntimeError):
            with woohoo():
                1 / 0

        # If the context manager wrapped StopIteration in a RuntimeError,
        # we also unwrap it, because we can't tell whether the wrapping was
        # done by the generator machinery or by the generator itself.
        with self.assertRaises(StopIteration):
            with woohoo():
                raise StopIteration

    def test_contextmanager_trap_second_yield_closes(self):
        state = []

        @contextmanager
        def woohoo():
            try:
                yield
                yield
            finally:
                state.append('cleanup')

        ctx = woohoo()
        ctx.__enter__()
        with self.assertRaises(RuntimeError):
            ctx.__exit__(None, None, None)
        self.assertEqual(state, ['cleanup'])


    def _create_contextmanager_attribs(self):
        def attribs(**kw):
            def decorate(func):
                for k,v in kw.items():
                    setattr(func,k,v)
                return func
            return decorate
        @contextmanager
        @attribs(foo='bar')
        def baz(spam):
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

    def test_instance_docstring_given_cm_docstring(self):
        baz = self._create_contextmanager_attribs()(None)
        self.assertEqual(baz.__doc__, "Whee!")

    def test_keywords(self):
        # Ensure no keyword arguments are inhibited
        @contextmanager
        def woohoo(self, func, args, kwds):
            yield (self, func, args, kwds)
        with woohoo(self=11, func=22, args=33, kwds=44) as target:
            self.assertEqual(target, (11, 22, 33, 44))


    def test_param_errors(self):
        @contextmanager
        def woohoo(a, *, b):
            yield

        with self.assertRaises(TypeError):
            woohoo()
        with self.assertRaises(TypeError):
            woohoo(3, 5)
        with self.assertRaises(TypeError):
            woohoo(b=3)

    def test_recursive(self):
        depth = 0
        ncols = 0
        @contextmanager
        def woohoo():
            nonlocal ncols
            ncols += 1
            nonlocal depth
            before = depth
            depth += 1
            yield
            depth -= 1
            self.assertEqual(depth, before)

        @woohoo()
        def recursive():
            if depth < 10:
                recursive()

        recursive()
        self.assertEqual(ncols, 10)
        self.assertEqual(depth, 0)


class ClosingTestCase(ContextAssertions):

    def test_instance_docs(self):
        # Issue 19330: ensure context manager instances have good docstrings
        cm_docstring = closing.__doc__
        obj = closing(None)
        self.assertEqual(obj.__doc__, cm_docstring)

    def test_closing(self):
        state = []
        class C:
            def close(self):
                state.append(1)
        x = C()
        self.assertEqual(state, [])
        with closing(x) as y:
            self.assertEqual(x, y)
        self.assertEqual(state, [1])

    def test_closing_error(self):
        state = []
        class C:
            def close(self):
                state.append(1)
        x = C()
        self.assertEqual(state, [])
        with self.assertRaises(ZeroDivisionError):
            with closing(x) as y:
                self.assertEqual(x, y)
                1 / 0
        self.assertEqual(state, [1])


class NullcontextTestCase(ContextAssertions):
    def test_nullcontext(self):
        class C:
            pass
        c = C()
        with nullcontext(c) as c_in:
            self.assertIs(c_in, c)


class mycontext(ContextDecorator):
    """Example decoration-compatible context manager for testing"""
    started = False
    exc = None
    catch = False

    def __enter__(self):
        self.started = True
        return self

    def __exit__(self, *exc):
        self.exc = exc
        return self.catch


class TestContextDecorator(ContextAssertions):

    def test_instance_docs(self):
        # Issue 19330: ensure context manager instances have good docstrings
        cm_docstring = mycontext.__doc__
        obj = mycontext()
        self.assertEqual(obj.__doc__, cm_docstring)

    def test_contextdecorator(self):
        context = mycontext()
        with context as result:
            self.assertIs(result, context)
            self.assertTrue(context.started)

        self.assertEqual(context.exc, (None, None, None))


    def test_contextdecorator_with_exception(self):
        context = mycontext()

        with self.assertRaisesRegex(NameError, 'foo'):
            with context:
                raise NameError('foo')
        self.assertIsNotNone(context.exc)
        self.assertIs(context.exc[0], NameError)

        context = mycontext()
        context.catch = True
        with context:
            raise NameError('foo')
        self.assertIsNotNone(context.exc)
        self.assertIs(context.exc[0], NameError)


    def test_decorator(self):
        context = mycontext()

        @context
        def test():
            self.assertIsNone(context.exc)
            self.assertTrue(context.started)
        test()
        self.assertEqual(context.exc, (None, None, None))


    def test_decorator_with_exception(self):
        context = mycontext()

        @context
        def test():
            self.assertIsNone(context.exc)
            self.assertTrue(context.started)
            raise NameError('foo')

        with self.assertRaisesRegex(NameError, 'foo'):
            test()
        self.assertIsNotNone(context.exc)
        self.assertIs(context.exc[0], NameError)


    def test_decorating_method(self):
        context = mycontext()

        class Test(object):

            @context
            def method(self, a, b, c=None):
                self.a = a
                self.b = b
                self.c = c

        # these tests are for argument passing when used as a decorator
        test = Test()
        test.method(1, 2)
        self.assertEqual(test.a, 1)
        self.assertEqual(test.b, 2)
        self.assertEqual(test.c, None)

        test = Test()
        test.method('a', 'b', 'c')
        self.assertEqual(test.a, 'a')
        self.assertEqual(test.b, 'b')
        self.assertEqual(test.c, 'c')

        test = Test()
        test.method(a=1, b=2)
        self.assertEqual(test.a, 1)
        self.assertEqual(test.b, 2)


    def test_typo_enter(self):
        class mycontext(ContextDecorator):
            def __unter__(self):
                pass
            def __exit__(self, *exc):
                pass

        with self.assertRaisesRegex(TypeError, 'the context manager'):
            with mycontext():
                pass


    def test_typo_exit(self):
        class mycontext(ContextDecorator):
            def __enter__(self):
                pass
            def __uxit__(self, *exc):
                pass

        with self.assertRaisesRegex(TypeError, 'the context manager.*__exit__'):
            with mycontext():
                pass


    def test_contextdecorator_as_mixin(self):
        class somecontext(object):
            started = False
            exc = None

            def __enter__(self):
                self.started = True
                return self

            def __exit__(self, *exc):
                self.exc = exc

        class mycontext(somecontext, ContextDecorator):
            pass

        context = mycontext()
        @context
        def test():
            self.assertIsNone(context.exc)
            self.assertTrue(context.started)
        test()
        self.assertEqual(context.exc, (None, None, None))


    def test_contextmanager_as_decorator(self):
        @contextmanager
        def woohoo(y):
            state.append(y)
            yield
            state.append(999)

        state = []
        @woohoo(1)
        def test(x):
            self.assertEqual(state, [1])
            state.append(x)
        test('something')
        self.assertEqual(state, [1, 'something', 999])

        # Issue #11647: Ensure the decorated function is 'reusable'
        state = []
        test('something else')
        self.assertEqual(state, [1, 'something else', 999])


class TestSuppress(unittest.TestCase):

    # @support.requires_docstrings
    def test_instance_docs(self):
        # Issue 19330: ensure context manager instances have good docstrings
        cm_docstring = suppress.__doc__
        obj = suppress()
        self.assertEqual(obj.__doc__, cm_docstring)

    def test_no_result_from_enter(self):
        with suppress(ValueError) as enter_result:
            self.assertIsNone(enter_result)

    def test_no_exception(self):
        with suppress(ValueError):
            self.assertEqual(pow(2, 5), 32)

    def test_exact_exception(self):
        with suppress(TypeError):
            len(5)

    def test_exception_hierarchy(self):
        with suppress(LookupError):
            'Hello'[50]

    def test_other_exception(self):
        with self.assertRaises(ZeroDivisionError):
            with suppress(TypeError):
                1/0

    def test_no_args(self):
        with self.assertRaises(ZeroDivisionError):
            with suppress():
                1/0

    def test_multiple_exception_args(self):
        with suppress(ZeroDivisionError, TypeError):
            1/0
        with suppress(ZeroDivisionError, TypeError):
            len(5)

    def test_cm_is_reentrant(self):
        ignore_exceptions = suppress(Exception)
        with ignore_exceptions:
            pass
        with ignore_exceptions:
            len(5)
        with ignore_exceptions:
            with ignore_exceptions: # Check nested usage
                len(5)
            outer_continued = True
            1/0
        self.assertTrue(outer_continued)


class ContextManagerProtocolTests(unittest.TestCase):
    def test_second_yield_cleanup_failure_propagates(self):
        original = StopIteration('body failed')

        @contextmanager
        def manager():
            try:
                yield
            except StopIteration as error:
                try:
                    yield
                finally:
                    raise RuntimeError('cleanup failed') from error

        with self.assertRaises(RuntimeError) as caught:
            with manager():
                raise original
        self.assertEqual(str(caught.exception), 'cleanup failed')
        self.assertIs(caught.exception.__cause__, original)

    # CPython v3.7.9 Lib/test/test_contextlib.py, issue #11647.
    def test_contextmanager_as_decorator(self):
        @contextmanager
        def woohoo(y):
            state.append(y)
            yield
            state.append(999)

        state = []
        @woohoo(1)
        def test(x):
            self.assertEqual(state, [1])
            state.append(x)
        test('something')
        self.assertEqual(state, [1, 'something', 999])

        # Issue #11647: Ensure the decorated function is 'reusable'
        state = []
        test('something else')
        self.assertEqual(state, [1, 'something else', 999])

    def test_decorator_returns_and_metadata(self):
        @contextmanager
        def manager():
            yield
        @manager()
        def answer(value=42):
            """Wrapped documentation."""
            return value
        self.assertEqual(answer(), 42)
        self.assertEqual(answer(value=7), 7)
        self.assertEqual(answer.__name__, "answer")
        self.assertEqual(answer.__doc__, "Wrapped documentation.")

    def test_failed_entry_preserves_error(self):
        error = ValueError("entry")
        @contextmanager
        def manager():
            raise error
            yield
        @manager()
        def answer():
            self.fail("body must not run")
        with self.assertRaises(ValueError) as caught:
            answer()
        self.assertIs(caught.exception, error)

    def test_decorated_exception_suppression_and_exit_failure(self):
        @contextmanager
        def suppress_value_error():
            try:
                yield
            except ValueError:
                pass
        @suppress_value_error()
        def fail():
            raise ValueError
        self.assertIsNone(fail())
        error = RuntimeError("exit")
        @contextmanager
        def bad_exit():
            yield
            raise error
        @bad_exit()
        def answer():
            return 42
        with self.assertRaises(RuntimeError) as caught:
            answer()
        self.assertIs(caught.exception, error)

    def test_closing_keyword_argument(self):
        events = []
        class Resource:
            def close(self):
                events.append("closed")
        resource = Resource()
        with closing(thing=resource) as entered:
            self.assertIs(entered, resource)
        self.assertEqual(events, ["closed"])



if __name__ == '__main__': unittest.main()
