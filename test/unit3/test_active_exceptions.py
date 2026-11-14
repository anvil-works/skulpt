# Selected unchanged methods from CPython 3.14 Lib/test/test_exceptions.py
# at 18ef0f0cb5278fa6583b753ffaaef7f46e416ab9.
import sys
import unittest

class ActiveExceptionTests(unittest.TestCase):
    def test_exception_cleanup_names(self):
        # Make sure the local variable bound to the exception instance by
        # an "except" statement is only visible inside the except block.
        try:
            raise Exception()
        except Exception as e:
            self.assertIsInstance(e, Exception)
        self.assertNotIn('e', locals())
        with self.assertRaises(UnboundLocalError):
            e


    def test_exception_cleanup_names2(self):
        # Make sure the cleanup doesn't break if the variable is explicitly deleted.
        try:
            raise Exception()
        except Exception as e:
            self.assertIsInstance(e, Exception)
            del e
        self.assertNotIn('e', locals())
        with self.assertRaises(UnboundLocalError):
            e


    def test_exception_target_in_nested_scope(self):
        # issue 4617: This used to raise a SyntaxError
        # "can not delete variable 'e' referenced in nested scope"
        def print_error():
            e
        try:
            something
        except Exception as e:
            print_error()


    def test_raise_does_not_create_context_chain_cycle(self):
        class A(Exception):
            pass
        class B(Exception):
            pass
        class C(Exception):
            pass

        # Create a context chain:
        # C -> B -> A
        # Then raise A in context of C.
        try:
            try:
                raise A
            except A as a_:
                a = a_
                try:
                    raise B
                except B as b_:
                    b = b_
                    try:
                        raise C
                    except C as c_:
                        c = c_
                        self.assertIsInstance(a, A)
                        self.assertIsInstance(b, B)
                        self.assertIsInstance(c, C)
                        self.assertIsNone(a.__context__)
                        self.assertIs(b.__context__, a)
                        self.assertIs(c.__context__, b)
                        raise a
        except A as e:
            exc = e

        # Expect A -> C -> B, without cycle
        self.assertIs(exc, a)
        self.assertIs(a.__context__, c)
        self.assertIs(c.__context__, b)
        self.assertIsNone(b.__context__)


    def test_no_hang_on_context_chain_cycle1(self):
        # See issue 25782. Cycle in context chain.

        def cycle():
            try:
                raise ValueError(1)
            except ValueError as ex:
                ex.__context__ = ex
                raise TypeError(2)

        try:
            cycle()
        except Exception as e:
            exc = e

        self.assertIsInstance(exc, TypeError)
        self.assertIsInstance(exc.__context__, ValueError)
        self.assertIs(exc.__context__.__context__, exc.__context__)


    def test_no_hang_on_context_chain_cycle2(self):
        # See issue 25782. Cycle at head of context chain.

        class A(Exception):
            pass
        class B(Exception):
            pass
        class C(Exception):
            pass

        # Context cycle:
        # +-----------+
        # V           |
        # C --> B --> A
        with self.assertRaises(C) as cm:
            try:
                raise A()
            except A as _a:
                a = _a
                try:
                    raise B()
                except B as _b:
                    b = _b
                    try:
                        raise C()
                    except C as _c:
                        c = _c
                        a.__context__ = c
                        raise c

        self.assertIs(cm.exception, c)
        # Verify the expected context chain cycle
        self.assertIs(c.__context__, b)
        self.assertIs(b.__context__, a)
        self.assertIs(a.__context__, c)


    def test_no_hang_on_context_chain_cycle3(self):
        # See issue 25782. Longer context chain with cycle.

        class A(Exception):
            pass
        class B(Exception):
            pass
        class C(Exception):
            pass
        class D(Exception):
            pass
        class E(Exception):
            pass

        # Context cycle:
        #             +-----------+
        #             V           |
        # E --> D --> C --> B --> A
        with self.assertRaises(E) as cm:
            try:
                raise A()
            except A as _a:
                a = _a
                try:
                    raise B()
                except B as _b:
                    b = _b
                    try:
                        raise C()
                    except C as _c:
                        c = _c
                        a.__context__ = c
                        try:
                            raise D()
                        except D as _d:
                            d = _d
                            e = E()
                            raise e

        self.assertIs(cm.exception, e)
        # Verify the expected context chain cycle
        self.assertIs(e.__context__, d)
        self.assertIs(d.__context__, c)
        self.assertIs(c.__context__, b)
        self.assertIs(b.__context__, a)
        self.assertIs(a.__context__, c)


    def test_context_of_exception_in_try_and_finally(self):
        try:
            try:
                te = TypeError(1)
                raise te
            finally:
                ve = ValueError(2)
                raise ve
        except Exception as e:
            exc = e

        self.assertIs(exc, ve)
        self.assertIs(exc.__context__, te)


    def test_context_of_exception_in_except_and_finally(self):
        try:
            try:
                te = TypeError(1)
                raise te
            except:
                ve = ValueError(2)
                raise ve
            finally:
                oe = OSError(3)
                raise oe
        except Exception as e:
            exc = e

        self.assertIs(exc, oe)
        self.assertIs(exc.__context__, ve)
        self.assertIs(exc.__context__.__context__, te)


    def test_context_of_exception_in_else_and_finally(self):
        try:
            try:
                pass
            except:
                pass
            else:
                ve = ValueError(1)
                raise ve
            finally:
                oe = OSError(2)
                raise oe
        except Exception as e:
            exc = e

        self.assertIs(exc, oe)
        self.assertIs(exc.__context__, ve)


    def test_yield_in_nested_try_excepts(self):
        #Issue #25612
        class MainError(Exception):
            pass

        class SubError(Exception):
            pass

        def main():
            try:
                raise MainError()
            except MainError:
                try:
                    yield
                except SubError:
                    pass
                raise

        coro = main()
        coro.send(None)
        with self.assertRaises(MainError):
            coro.throw(SubError())


    def test_generator_doesnt_retain_old_exc2(self):
        #Issue 28884#msg282532
        def g():
            try:
                raise ValueError
            except ValueError:
                yield 1
            self.assertIsNone(sys.exception())
            yield 2

        gen = g()

        try:
            raise IndexError
        except IndexError:
            self.assertEqual(next(gen), 1)
        self.assertEqual(next(gen), 2)


    def test_raise_in_generator(self):
        #Issue 25612#msg304117
        def g():
            yield 1
            raise
            yield 2

        with self.assertRaises(ZeroDivisionError):
            i = g()
            try:
                1/0
            except:
                next(i)
                next(i)


    def test_keyerror_context(self):
        # Make sure that _PyErr_SetKeyError() chains exceptions
        try:
            err1 = None
            err2 = None
            try:
                d = {}
                try:
                    raise ValueError("bug")
                except Exception as exc:
                    err1 = exc
                    d[1]
            except Exception as exc:
                err2 = exc

            self.assertIsInstance(err1, ValueError)
            self.assertIsInstance(err2, KeyError)
            self.assertEqual(err2.__context__, err1)
        finally:
            # Break any potential reference cycle
            exc1 = None
            exc2 = None


    def test_generator_leaking(self):
        # Test that generator exception state doesn't leak into the calling
        # frame
        def yield_raise():
            try:
                raise KeyError("caught")
            except KeyError:
                yield sys.exception()
                yield sys.exception()
            yield sys.exception()
        g = yield_raise()
        self.assertIsInstance(next(g), KeyError)
        self.assertIsNone(sys.exception())
        self.assertIsInstance(next(g), KeyError)
        self.assertIsNone(sys.exception())
        self.assertIsNone(next(g))

        # Same test, but inside an exception handler
        try:
            raise TypeError("foo")
        except TypeError:
            g = yield_raise()
            self.assertIsInstance(next(g), KeyError)
            self.assertIsInstance(sys.exception(), TypeError)
            self.assertIsInstance(next(g), KeyError)
            self.assertIsInstance(sys.exception(), TypeError)
            self.assertIsInstance(next(g), TypeError)
            del g
            self.assertIsInstance(sys.exception(), TypeError)


    def test_generator_leaking2(self):
        # See issue 12475.
        def g():
            yield
        try:
            raise RuntimeError
        except RuntimeError:
            it = g()
            next(it)
        try:
            next(it)
        except StopIteration:
            pass
        self.assertIsNone(sys.exception())


    def test_generator_leaking3(self):
        # See issue #23353.  When gen.throw() is called, the caller's
        # exception state should be save and restored.
        def g():
            try:
                yield
            except ZeroDivisionError:
                yield sys.exception()
        it = g()
        next(it)
        try:
            1/0
        except ZeroDivisionError as e:
            self.assertIs(sys.exception(), e)
            gen_exc = it.throw(e)
            self.assertIs(sys.exception(), e)
            self.assertIs(gen_exc, e)
        self.assertIsNone(sys.exception())


    def test_generator_leaking4(self):
        # See issue #23353.  When an exception is raised by a generator,
        # the caller's exception state should still be restored.
        def g():
            try:
                1/0
            except ZeroDivisionError:
                yield sys.exception()
                raise
        it = g()
        try:
            raise TypeError
        except TypeError:
            # The caller's exception state (TypeError) is temporarily
            # saved in the generator.
            tp = type(next(it))
        self.assertIs(tp, ZeroDivisionError)
        try:
            next(it)
            # We can't check it immediately, but while next() returns
            # with an exception, it shouldn't have restored the old
            # exception state (TypeError).
        except ZeroDivisionError as e:
            self.assertIs(sys.exception(), e)
        # We used to find TypeError here.
        self.assertIsNone(sys.exception())


    def test_generator_doesnt_retain_old_exc(self):
        def g():
            self.assertIsInstance(sys.exception(), RuntimeError)
            yield
            self.assertIsNone(sys.exception())
        it = g()
        try:
            raise RuntimeError
        except RuntimeError:
            next(it)
        self.assertRaises(StopIteration, next, it)


class ActiveExceptionRegression(unittest.TestCase):
    def test_runtime_wrappers_keep_their_original_cause(self):
        def g():
            raise StopIteration('end')
            yield
        outer = ValueError('caller')
        try:
            raise outer
        except ValueError:
            try:
                next(g())
            except RuntimeError as error:
                self.assertIsInstance(error.__cause__, StopIteration)
                self.assertIs(error.__context__, error.__cause__)
                self.assertTrue(error.__suppress_context__)
                self.assertIs(error.__cause__.__context__, outer)

    def test_propagation_does_not_replace_generator_context(self):
        caught = ValueError('caught')
        def g():
            try:
                raise caught
            except ValueError:
                yield
                raise
        it = g()
        next(it)
        try:
            raise TypeError('caller')
        except TypeError:
            try:
                next(it)
            except ValueError as error:
                self.assertIsNone(error.__context__)


    def test_handler_control_flow_and_frame_inheritance(self):
        def reraiser():
            raise
        outer = ValueError('outer')
        try:
            raise outer
        except ValueError:
            for mode in ('break', 'continue', 'return', 'raise'):
                def inner():
                    for i in range(2):
                        try:
                            raise KeyError('inner')
                        except KeyError as target:
                            if mode == 'break': break
                            if mode == 'continue': continue
                            if mode == 'return': return
                            raise TypeError('replacement')
                            self.fail('unreachable handler statement')
                    self.assertNotIn('target', locals())
                if mode == 'raise':
                    with self.assertRaises(TypeError): inner()
                else:
                    inner()
                self.assertIs(sys.exception(), outer)
                try:
                    reraiser()
                except ValueError as caught:
                    self.assertIs(caught, outer)
                class C:
                    try:
                        raise KeyError('class')
                    except KeyError as target:
                        pass
                self.assertFalse(hasattr(C, 'target'))
                self.assertIs(sys.exception(), outer)
        self.assertIsNone(sys.exception())
        with self.assertRaises(RuntimeError): reraiser()

    def test_finally_replaces_pending_control_flow(self):
        def f():
            try:
                return 1
            finally:
                raise ValueError('replacement')
        with self.assertRaises(ValueError): f()
        def g():
            try:
                raise KeyError('pending')
            finally:
                return 2
        self.assertEqual(g(), 2)
        def h():
            try:
                return 3
            finally:
                try:
                    raise KeyError('handled')
                except KeyError:
                    pass
        self.assertEqual(h(), 3)

    def test_raise_from_keeps_context_and_suppression(self):
        outer = ValueError('outer')
        try:
            raise outer
        except ValueError:
            try:
                raise TypeError('inner') from None
            except TypeError as inner:
                self.assertIs(inner.__context__, outer)
                self.assertIsNone(inner.__cause__)
                self.assertTrue(inner.__suppress_context__)
        self.assertIsNone(sys.exception())

# Unchanged CPython Lib/test/test_with.py methods at the same revision.
class ContextManagerExceptionTests(unittest.TestCase):
    # Skulpt unittest.fail records failures; CPython raises AssertionError.
    def fail(self, msg=None):
        raise AssertionError(msg)

    def testRaisedStopIteration2(self):
        # From bug 1462485
        class cm(object):
            def __enter__(self):
                pass
            def __exit__(self, type, value, traceback):
                pass

        def shouldThrow():
            with cm():
                raise StopIteration("from with")

        with self.assertRaisesRegex(StopIteration, 'from with'):
            shouldThrow()


    def testRaisedGeneratorExit2(self):
        # From bug 1462485
        class cm (object):
            def __enter__(self):
                pass
            def __exit__(self, type, value, traceback):
                pass

        def shouldThrow():
            with cm():
                raise GeneratorExit("from with")

        self.assertRaises(GeneratorExit, shouldThrow)


    def testErrorsInBool(self):
        # issue4589: __exit__ return code may raise an exception
        # when looking at its truth value.

        class cm(object):
            def __init__(self, bool_conversion):
                class Bool:
                    def __bool__(self):
                        return bool_conversion()
                self.exit_result = Bool()
            def __enter__(self):
                return 3
            def __exit__(self, a, b, c):
                return self.exit_result

        def trueAsBool():
            with cm(lambda: True):
                self.fail("Should NOT see this")
        trueAsBool()

        def falseAsBool():
            with cm(lambda: False):
                self.fail("Should raise")
        self.assertRaises(AssertionError, falseAsBool)

        def failAsBool():
            with cm(lambda: 1//0):
                self.fail("Should NOT see this")
        self.assertRaises(ZeroDivisionError, failAsBool)


class ContextManagerExceptionRegression(unittest.TestCase):
    def test_exit_state_suppression_and_failure(self):
        outer = ValueError('outer')
        body = KeyError('body')
        class Manager:
            def __enter__(self): return self
            def __exit__(self, typ, error, tb):
                self.assert_state(error)
                if self.fail_exit: raise TypeError('exit')
                return self.suppress
            def assert_state(self, error):
                assert sys.exception() is (outer if error is None else error)
            fail_exit = False
            suppress = True
        try:
            raise outer
        except ValueError:
            with Manager(): raise body
            self.assertIs(sys.exception(), outer)
            manager = Manager()
            manager.suppress = False
            try:
                with manager: raise body
            except KeyError as caught:
                self.assertIs(caught, body)
            self.assertIs(sys.exception(), outer)
            manager.fail_exit = True
            try:
                with manager: raise body
            except TypeError as caught:
                self.assertIs(caught.__context__, body)
            self.assertIs(sys.exception(), outer)
            class BadBool:
                def __bool__(self): raise TypeError('bool')
            manager.fail_exit = False
            manager.suppress = BadBool()
            try:
                with manager: raise body
            except TypeError as caught:
                self.assertIs(caught.__context__, body)
            self.assertIs(sys.exception(), outer)
        self.assertIsNone(sys.exception())

    def test_return_exit_failure_is_called_once(self):
        events = []
        class Manager:
            def __enter__(self): return self
            def __exit__(self, *args):
                events.append(args[0])
                raise ValueError('exit')
        def f():
            with Manager(): return 1
        with self.assertRaises(ValueError): f()
        self.assertEqual(events, [None])
        self.assertIsNone(sys.exception())

if __name__ == '__main__':
    unittest.main()
