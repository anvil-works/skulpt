# Selected unchanged CPython 3.14 methods and helpers at 18ef0f0cb5278fa6583b753ffaaef7f46e416ab9.
import sys
import types
import unittest

class ExceptionTracebackTests(unittest.TestCase):
    def testWithTraceback(self):
        try:
            raise IndexError(4)
        except Exception as e:
            tb = e.__traceback__

        e = BaseException().with_traceback(tb)
        self.assertIsInstance(e, BaseException)
        self.assertEqual(e.__traceback__, tb)

        e = IndexError(5).with_traceback(tb)
        self.assertIsInstance(e, IndexError)
        self.assertEqual(e.__traceback__, tb)

        class MyException(Exception):
            pass

        e = MyException().with_traceback(tb)
        self.assertIsInstance(e, MyException)
        self.assertEqual(e.__traceback__, tb)


    def testInvalidTraceback(self):
        try:
            Exception().__traceback__ = 5
        except TypeError as e:
            self.assertIn("__traceback__ must be a traceback", str(e))
        else:
            self.fail("No exception raised")


    def test_invalid_setattr(self):
        TE = TypeError
        exc = Exception()
        msg = "'int' object is not iterable"
        self.assertRaisesRegex(TE, msg, setattr, exc, 'args', 1)
        msg = "__traceback__ must be a traceback or None"
        self.assertRaisesRegex(TE, msg, setattr, exc, '__traceback__', 1)
        msg = "exception cause must be None or derive from BaseException"
        self.assertRaisesRegex(TE, msg, setattr, exc, '__cause__', 1)
        msg = "exception context must be None or derive from BaseException"
        self.assertRaisesRegex(TE, msg, setattr, exc, '__context__', 1)


    def test_invalid_delattr(self):
        TE = TypeError
        try:
            raise IndexError(4)
        except Exception as e:
            exc = e

        msg = "may not be deleted"
        self.assertRaisesRegex(TE, msg, delattr, exc, 'args')
        self.assertRaisesRegex(TE, msg, delattr, exc, '__traceback__')
        self.assertRaisesRegex(TE, msg, delattr, exc, '__cause__')
        self.assertRaisesRegex(TE, msg, delattr, exc, '__context__')


    def testNoneClearsTracebackAttr(self):
        try:
            raise IndexError(4)
        except Exception as e:
            tb = e.__traceback__

        e = Exception()
        e.__traceback__ = tb
        e.__traceback__ = None
        self.assertEqual(e.__traceback__, None)


class TracebackTypesTests(unittest.TestCase):
    def test_traceback_and_frame_types(self):
        try:
            raise OSError
        except OSError as e:
            exc = e
        self.assertIsInstance(exc.__traceback__, types.TracebackType)
        self.assertIsInstance(exc.__traceback__.tb_frame, types.FrameType)


def create_simple_eg():
    excs = []
    try:
        try:
            raise MemoryError("context and cause for ValueError(1)")
        except MemoryError as e:
            raise ValueError(1) from e
    except ValueError as e:
        excs.append(e)

    try:
        try:
            raise OSError("context for TypeError")
        except OSError as e:
            raise TypeError(int)
    except TypeError as e:
        excs.append(e)

    try:
        try:
            raise ImportError("context for ValueError(2)")
        except ImportError as e:
            raise ValueError(2)
    except ValueError as e:
        excs.append(e)

    try:
        raise ExceptionGroup('simple eg', excs)
    except ExceptionGroup as e:
        return e


def create_nested_eg():
    excs = []
    try:
        try:
            raise TypeError(bytes)
        except TypeError as e:
            raise ExceptionGroup("nested", [e])
    except ExceptionGroup as e:
        excs.append(e)

    try:
        try:
            raise MemoryError('out of memory')
        except MemoryError as e:
            raise ValueError(1) from e
    except ValueError as e:
        excs.append(e)

    try:
        raise ExceptionGroup("root", excs)
    except ExceptionGroup as eg:
        return eg


class GroupTracebackTests(unittest.TestCase):
    def test_basics_ExceptionGroup_fields(self):
        eg = create_simple_eg()

        # check msg
        self.assertEqual(eg.message, 'simple eg')
        self.assertEqual(eg.args[0], 'simple eg')

        # check cause and context
        self.assertIsInstance(eg.exceptions[0], ValueError)
        self.assertIsInstance(eg.exceptions[0].__cause__, MemoryError)
        self.assertIsInstance(eg.exceptions[0].__context__, MemoryError)
        self.assertIsInstance(eg.exceptions[1], TypeError)
        self.assertIsNone(eg.exceptions[1].__cause__)
        self.assertIsInstance(eg.exceptions[1].__context__, OSError)
        self.assertIsInstance(eg.exceptions[2], ValueError)
        self.assertIsNone(eg.exceptions[2].__cause__)
        self.assertIsInstance(eg.exceptions[2].__context__, ImportError)

        # check tracebacks
        line0 = create_simple_eg.__code__.co_firstlineno
        tb_linenos = [line0 + 27,
                      [line0 + 6, line0 + 14, line0 + 22]]
        self.assertEqual(eg.__traceback__.tb_lineno, tb_linenos[0])
        self.assertIsNone(eg.__traceback__.tb_next)
        for i in range(3):
            tb = eg.exceptions[i].__traceback__
            self.assertIsNone(tb.tb_next)
            self.assertEqual(tb.tb_lineno, tb_linenos[1][i])


    def test_nested_exception_group_tracebacks(self):
        eg = create_nested_eg()

        line0 = create_nested_eg.__code__.co_firstlineno
        for (tb, expected) in [
            (eg.__traceback__, line0 + 19),
            (eg.exceptions[0].__traceback__, line0 + 6),
            (eg.exceptions[1].__traceback__, line0 + 14),
            (eg.exceptions[0].exceptions[0].__traceback__, line0 + 4),
        ]:
            self.assertEqual(tb.tb_lineno, expected)
            self.assertIsNone(tb.tb_next)


class SysExceptionInfoTests(unittest.TestCase):
    def test_exc_info_no_exception(self):
        self.assertEqual(sys.exc_info(), (None, None, None))


    def test_sys_exception_no_exception(self):
        self.assertEqual(sys.exception(), None)


    def test_exc_info_with_exception_instance(self):
        def f():
            raise ValueError(42)

        try:
            f()
        except Exception as e_:
            e = e_
            exc_info = sys.exc_info()

        self.assertIsInstance(e, ValueError)
        self.assertIs(exc_info[0], ValueError)
        self.assertIs(exc_info[1], e)
        self.assertIs(exc_info[2], e.__traceback__)


    def test_exc_info_with_exception_type(self):
        def f():
            raise ValueError

        try:
            f()
        except Exception as e_:
            e = e_
            exc_info = sys.exc_info()

        self.assertIsInstance(e, ValueError)
        self.assertIs(exc_info[0], ValueError)
        self.assertIs(exc_info[1], e)
        self.assertIs(exc_info[2], e.__traceback__)


    def test_sys_exception_with_exception_instance(self):
        def f():
            raise ValueError(42)

        try:
            f()
        except Exception as e_:
            e = e_
            exc = sys.exception()

        self.assertIsInstance(e, ValueError)
        self.assertIs(exc, e)


    def test_sys_exception_with_exception_type(self):
        def f():
            raise ValueError

        try:
            f()
        except Exception as e_:
            e = e_
            exc = sys.exception()

        self.assertIsInstance(e, ValueError)
        self.assertIs(exc, e)


class TracebackRegression(unittest.TestCase):
    def test_delegated_throw_chains_only_frames_that_resume(self):
        outer_error = KeyError('outer')
        def inner_catches():
            try: yield
            except TypeError as error: yield error.__context__
        def inner_escapes():
            try: raise OSError('inner')
            except OSError: yield
        def outer(inner):
            try: raise outer_error
            except KeyError: yield from inner()
        it = outer(inner_catches)
        next(it)
        self.assertIsNone(it.throw(TypeError('injected')))
        it.close()
        it = outer(inner_escapes)
        next(it)
        try:
            it.throw(TypeError('injected'))
        except TypeError as error:
            self.assertIs(error.__context__, outer_error)

    def test_throw_context_uses_local_handler_not_the_caller(self):
        def plain(): yield
        def protected():
            try: yield
            finally: pass
        def local():
            try: raise KeyError('local')
            except KeyError as error: yield error
        for factory in (plain, protected, local):
            for previous in (None, OSError('previous')):
                it = factory()
                own = next(it)
                injected = TypeError('injected')
                injected.__context__ = previous
                try:
                    raise ValueError('caller')
                except ValueError:
                    try:
                        it.throw(injected)
                    except TypeError as caught:
                        self.assertIs(caught, injected)
                        self.assertIs(caught.__context__, own if factory is local else previous)

    def test_throwing_existing_error_adds_the_injection_location(self):
        saved = ValueError('saved')
        def g():
            try:
                raise saved
            except ValueError:
                yield saved
                yield 2
        it = g()
        error = next(it)
        original = error.__traceback__
        try:
            it.throw(error)
        except ValueError as caught:
            injected = caught.__traceback__.tb_next
            self.assertIs(injected.tb_next, original)
            self.assertIs(injected.tb_frame, original.tb_frame)
            self.assertEqual(injected.tb_lineno, g.__code__.co_firstlineno + 4)

    def test_pending_finally_error_keeps_traceback_across_yield(self):
        def g():
            try:
                raise ValueError('first')
            finally:
                yield 1
        it = g()
        self.assertEqual(next(it), 1)
        try:
            next(it)
        except ValueError as error:
            inner = error.__traceback__.tb_next
            self.assertIsNone(inner.tb_next)
            self.assertIs(inner.tb_frame.f_code, g.__code__)
            self.assertEqual(inner.tb_lineno, g.__code__.co_firstlineno + 2)


    def test_raise_locations_reraise_and_frame_identity(self):
        def f():
            try:
                raise ValueError('first')
            except ValueError as error:
                captured = error.__traceback__
                frame = captured.tb_frame
                self.assertIs(frame.f_code, f.__code__)
                self.assertEqual(captured.tb_lineno, f.__code__.co_firstlineno + 2)
                self.assertIs(sys.exc_info()[2], captured)
                raise
        try:
            f()
        except ValueError as error:
            outer = error.__traceback__
            inner = outer.tb_next
            self.assertIsNone(inner.tb_next)
            self.assertIs(inner.tb_frame.f_code, f.__code__)
            self.assertEqual(inner.tb_lineno, f.__code__.co_firstlineno + 2)
            self.assertIs(inner.tb_frame.f_back, outer.tb_frame)
            saved = outer
            try:
                raise error
            except ValueError as reraised:
                self.assertIs(reraised.__traceback__.tb_next, saved)
        self.assertEqual(sys.exc_info(), (None, None, None))

    def test_mutable_links_constructor_and_group_metadata(self):
        try:
            raise ValueError('frame')
        except ValueError as error:
            tb = error.__traceback__
        made = types.TracebackType(None, tb.tb_frame, 7, 123)
        for value in (-2**31 - 1, 2**31, 2**100):
            with self.assertRaises(OverflowError): types.TracebackType(None, tb.tb_frame, value, 1)
            with self.assertRaises(OverflowError): types.TracebackType(None, tb.tb_frame, 0, value)
        self.assertEqual(made.tb_lasti, 7)
        self.assertEqual(made.tb_lineno, 123)
        self.assertIs(made.tb_frame, tb.tb_frame)
        made.tb_next = tb
        with self.assertRaises(ValueError): tb.tb_next = made
        with self.assertRaises(TypeError): made.tb_next = 1
        with self.assertRaises(TypeError): del made.tb_next
        made.tb_next = None
        self.assertIsNone(made.tb_next)
        with self.assertRaises(AttributeError): made.tb_lineno = 5
        with self.assertRaises(TypeError): types.FrameType()
        group = ExceptionGroup('eg', [ValueError(1), TypeError(2)])
        group.__traceback__ = tb
        match, rest = group.split(ValueError)
        self.assertIs(match.__traceback__, tb)
        self.assertIs(rest.__traceback__, tb)
        try:
            raise match
        except ExceptionGroup as caught:
            self.assertIs(caught.__traceback__.tb_next, tb)
        self.assertIs(group.__traceback__, tb)
        self.assertIs(rest.__traceback__, tb)

    def test_with_traceback_bypasses_override_and_exit_receives_traceback(self):
        class E(Exception):
            @property
            def __traceback__(self): return 'override'
            @__traceback__.setter
            def __traceback__(self, value): raise AssertionError('override')
        error = E()
        self.assertIs(error.with_traceback(None), error)
        events = []
        class Manager:
            def __enter__(self): return self
            def __exit__(self, kind, error, tb):
                events.append(tb)
                assert tb is sys.exc_info()[2]
                assert tb is error.__traceback__
                return True
        with Manager(): raise ValueError('body')
        self.assertIsInstance(events[0], types.TracebackType)

if __name__ == '__main__':
    unittest.main()
