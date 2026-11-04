# Selected CPython 3.14 unittest tests at 18ef0f0cb5278fa6583b753ffaaef7f46e416ab9.
# Test bodies and assertions are unchanged. Only TestLongMessage.setUp uses
# the existing no-argument constructor; method-name execution remains unsupported.
# GC/refcount, warnings/logging and collection-diff assertions are outside this port.
import datetime
import re
import unittest
from itertools import product



# test_assertions.py: Test_Assertions
class AssertionTests(unittest.TestCase):

    def test_AlmostEqual(self):
        self.assertAlmostEqual(1.00000001, 1.0)
        self.assertNotAlmostEqual(1.0000001, 1.0)
        self.assertRaises(self.failureException,
                          self.assertAlmostEqual, 1.0000001, 1.0)
        self.assertRaises(self.failureException,
                          self.assertNotAlmostEqual, 1.00000001, 1.0)

        self.assertAlmostEqual(1.1, 1.0, places=0)
        self.assertRaises(self.failureException,
                          self.assertAlmostEqual, 1.1, 1.0, places=1)

        self.assertAlmostEqual(0, .1+.1j, places=0)
        self.assertNotAlmostEqual(0, .1+.1j, places=1)
        self.assertRaises(self.failureException,
                          self.assertAlmostEqual, 0, .1+.1j, places=1)
        self.assertRaises(self.failureException,
                          self.assertNotAlmostEqual, 0, .1+.1j, places=0)

        self.assertAlmostEqual(float('inf'), float('inf'))
        self.assertRaises(self.failureException, self.assertNotAlmostEqual,
                          float('inf'), float('inf'))

    def test_AmostEqualWithDelta(self):
        self.assertAlmostEqual(1.1, 1.0, delta=0.5)
        self.assertAlmostEqual(1.0, 1.1, delta=0.5)
        self.assertNotAlmostEqual(1.1, 1.0, delta=0.05)
        self.assertNotAlmostEqual(1.0, 1.1, delta=0.05)

        self.assertAlmostEqual(1.0, 1.0, delta=0.5)
        self.assertRaises(self.failureException, self.assertNotAlmostEqual,
                          1.0, 1.0, delta=0.5)

        self.assertRaises(self.failureException, self.assertAlmostEqual,
                          1.1, 1.0, delta=0.05)
        self.assertRaises(self.failureException, self.assertNotAlmostEqual,
                          1.1, 1.0, delta=0.5)

        self.assertRaises(TypeError, self.assertAlmostEqual,
                          1.1, 1.0, places=2, delta=2)
        self.assertRaises(TypeError, self.assertNotAlmostEqual,
                          1.1, 1.0, places=2, delta=2)

        first = datetime.datetime.now()
        second = first + datetime.timedelta(seconds=10)
        self.assertAlmostEqual(first, second,
                               delta=datetime.timedelta(seconds=20))
        self.assertNotAlmostEqual(first, second,
                                  delta=datetime.timedelta(seconds=5))

    def test_assertRaises(self):
        def _raise(e):
            raise e
        self.assertRaises(KeyError, _raise, KeyError)
        self.assertRaises(KeyError, _raise, KeyError("key"))
        try:
            self.assertRaises(KeyError, lambda: None)
        except self.failureException as e:
            self.assertIn("KeyError not raised", str(e))
        else:
            self.fail("assertRaises() didn't fail")
        try:
            self.assertRaises(KeyError, _raise, ValueError)
        except ValueError:
            pass
        else:
            self.fail("assertRaises() didn't let exception pass through")
        with self.assertRaises(KeyError) as cm:
            try:
                raise KeyError
            except Exception as e:
                exc = e
                raise
        self.assertIs(cm.exception, exc)

        with self.assertRaises(KeyError):
            raise KeyError("key")
        try:
            with self.assertRaises(KeyError):
                pass
        except self.failureException as e:
            self.assertIn("KeyError not raised", str(e))
        else:
            self.fail("assertRaises() didn't fail")
        try:
            with self.assertRaises(KeyError):
                raise ValueError
        except ValueError:
            pass
        else:
            self.fail("assertRaises() didn't let exception pass through")

    def testAssertNotRegex(self):
        self.assertNotRegex('Ala ma kota', r'r+')
        try:
            self.assertNotRegex('Ala ma kota', r'k.t', 'Message')
        except self.failureException as e:
            self.assertIn('Message', e.args[0])
        else:
            self.fail('assertNotRegex should have failed.')


# test_case.py: Test_TestCase
class RaisesTests(unittest.TestCase):

    def testAssertRaisesCallable(self):
        class ExceptionMock(Exception):
            pass
        def Stub():
            raise ExceptionMock('We expect')
        self.assertRaises(ExceptionMock, Stub)
        # A tuple of exception classes is accepted
        self.assertRaises((ValueError, ExceptionMock), Stub)
        # *args and **kwargs also work
        self.assertRaises(ValueError, int, '19', base=8)
        # Failure when no exception is raised
        with self.assertRaises(self.failureException):
            self.assertRaises(ExceptionMock, lambda: 0)
        # Failure when the function is None
        with self.assertRaises(TypeError):
            self.assertRaises(ExceptionMock, None)
        # Failure when another exception is raised
        with self.assertRaises(ExceptionMock):
            self.assertRaises(ValueError, Stub)

    def testAssertRaisesContext(self):
        class ExceptionMock(Exception):
            pass
        def Stub():
            raise ExceptionMock('We expect')
        with self.assertRaises(ExceptionMock):
            Stub()
        # A tuple of exception classes is accepted
        with self.assertRaises((ValueError, ExceptionMock)) as cm:
            Stub()
        # The context manager exposes caught exception
        self.assertIsInstance(cm.exception, ExceptionMock)
        self.assertEqual(cm.exception.args[0], 'We expect')
        # *args and **kwargs also work
        with self.assertRaises(ValueError):
            int('19', base=8)
        # Failure when no exception is raised
        with self.assertRaises(self.failureException):
            with self.assertRaises(ExceptionMock):
                pass
        # Custom message
        with self.assertRaisesRegex(self.failureException, 'foobar'):
            with self.assertRaises(ExceptionMock, msg='foobar'):
                pass
        # Invalid keyword argument
        with self.assertRaisesRegex(TypeError, 'foobar'):
            with self.assertRaises(ExceptionMock, foobar=42):
                pass
        # Failure when another exception is raised
        with self.assertRaises(ExceptionMock):
            self.assertRaises(ValueError, Stub)

    def testAssertRaisesNoExceptionType(self):
        with self.assertRaises(TypeError):
            self.assertRaises()
        with self.assertRaises(TypeError):
            self.assertRaises(1)
        with self.assertRaises(TypeError):
            self.assertRaises(object)
        with self.assertRaises(TypeError):
            self.assertRaises((ValueError, 1))
        with self.assertRaises(TypeError):
            self.assertRaises((ValueError, object))

    def testAssertRaisesRegex(self):
        class ExceptionMock(Exception):
            pass

        def Stub():
            raise ExceptionMock('We expect')

        self.assertRaisesRegex(ExceptionMock, re.compile('expect$'), Stub)
        self.assertRaisesRegex(ExceptionMock, 'expect$', Stub)
        with self.assertRaises(TypeError):
            self.assertRaisesRegex(ExceptionMock, 'expect$', None)

    def testAssertNotRaisesRegex(self):
        self.assertRaisesRegex(
                self.failureException, '^Exception not raised by <lambda>$',
                self.assertRaisesRegex, Exception, re.compile('x'),
                lambda: None)
        self.assertRaisesRegex(
                self.failureException, '^Exception not raised by <lambda>$',
                self.assertRaisesRegex, Exception, 'x',
                lambda: None)
        # Custom message
        with self.assertRaisesRegex(self.failureException, 'foobar'):
            with self.assertRaisesRegex(Exception, 'expect', msg='foobar'):
                pass
        # Invalid keyword argument
        with self.assertRaisesRegex(TypeError, 'foobar'):
            with self.assertRaisesRegex(Exception, 'expect', foobar=42):
                pass

    def testAssertRaisesRegexInvalidRegex(self):
        # Issue 20145.
        class MyExc(Exception):
            pass
        self.assertRaises(TypeError, self.assertRaisesRegex, MyExc, lambda: True)

    def testAssertRaisesRegexMismatch(self):
        def Stub():
            raise Exception('Unexpected')

        self.assertRaisesRegex(
                self.failureException,
                r'"\^Expected\$" does not match "Unexpected"',
                self.assertRaisesRegex, Exception, '^Expected$',
                Stub)
        self.assertRaisesRegex(
                self.failureException,
                r'"\^Expected\$" does not match "Unexpected"',
                self.assertRaisesRegex, Exception,
                re.compile('^Expected$'), Stub)

    def testAssertRaisesExcValue(self):
        class ExceptionMock(Exception):
            pass

        def Stub(foo):
            raise ExceptionMock(foo)
        v = "particular value"

        ctx = self.assertRaises(ExceptionMock)
        with ctx:
            Stub(v)
        e = ctx.exception
        self.assertIsInstance(e, ExceptionMock)
        self.assertEqual(e.args[0], v)

    def testAssertRaisesRegexNoExceptionType(self):
        with self.assertRaises(TypeError):
            self.assertRaisesRegex()
        with self.assertRaises(TypeError):
            self.assertRaisesRegex(ValueError)
        with self.assertRaises(TypeError):
            self.assertRaisesRegex(1, 'expect')
        with self.assertRaises(TypeError):
            self.assertRaisesRegex(object, 'expect')
        with self.assertRaises(TypeError):
            self.assertRaisesRegex((ValueError, 1), 'expect')
        with self.assertRaises(TypeError):
            self.assertRaisesRegex((ValueError, object), 'expect')


# test_assertions.py: TestLongMessage
class MessageTests(unittest.TestCase):

    def setUp(self):
        class TestableTestFalse(unittest.TestCase):
            longMessage = False
            failureException = self.failureException

            def testTest(self):
                pass

        class TestableTestTrue(unittest.TestCase):
            longMessage = True
            failureException = self.failureException

            def testTest(self):
                pass

        self.testableTrue = TestableTestTrue()
        self.testableFalse = TestableTestFalse()

    def assertMessages(self, methodName, args, errors):
        """
        Check that methodName(*args) raises the correct error messages.
        errors should be a list of 4 regex that match the error when:
          1) longMessage = False and no msg passed;
          2) longMessage = False and msg passed;
          3) longMessage = True and no msg passed;
          4) longMessage = True and msg passed;
        """
        def getMethod(i):
            useTestableFalse  = i < 2
            if useTestableFalse:
                test = self.testableFalse
            else:
                test = self.testableTrue
            return getattr(test, methodName)

        for i, expected_regex in enumerate(errors):
            testMethod = getMethod(i)
            kwargs = {}
            withMsg = i % 2
            if withMsg:
                kwargs = {"msg": "oops"}

            with self.assertRaisesRegex(self.failureException,
                                        expected_regex=expected_regex):
                testMethod(*args, **kwargs)

    def assertMessagesCM(self, methodName, args, func, errors):
        """
        Check that the correct error messages are raised while executing:
          with method(*args):
              func()
        *errors* should be a list of 4 regex that match the error when:
          1) longMessage = False and no msg passed;
          2) longMessage = False and msg passed;
          3) longMessage = True and no msg passed;
          4) longMessage = True and msg passed;
        """
        p = product((self.testableFalse, self.testableTrue),
                    ({}, {"msg": "oops"}))
        for (cls, kwargs), err in zip(p, errors):
            method = getattr(cls, methodName)
            with self.assertRaisesRegex(cls.failureException, err):
                with method(*args, **kwargs) as cm:
                    func()

    def testDefault(self):
        self.assertTrue(unittest.TestCase.longMessage)

    def test_formatMsg(self):
        self.assertEqual(self.testableFalse._formatMessage(None, "foo"), "foo")
        self.assertEqual(self.testableFalse._formatMessage("foo", "bar"), "foo")

        self.assertEqual(self.testableTrue._formatMessage(None, "foo"), "foo")
        self.assertEqual(self.testableTrue._formatMessage("foo", "bar"), "bar : foo")

        # This blows up if _formatMessage uses string concatenation
        self.testableTrue._formatMessage(object(), 'foo')

    def test_formatMessage_unicode_error(self):
        one = ''.join(chr(i) for i in range(255))
        # this used to cause a UnicodeDecodeError constructing msg
        self.testableTrue._formatMessage(one, '\uFFFD')

    def testAssertTrue(self):
        self.assertMessages('assertTrue', (False,),
                            ["^False is not true$", "^oops$", "^False is not true$",
                             "^False is not true : oops$"])

    def testAssertFalse(self):
        self.assertMessages('assertFalse', (True,),
                            ["^True is not false$", "^oops$", "^True is not false$",
                             "^True is not false : oops$"])

    def testNotEqual(self):
        self.assertMessages('assertNotEqual', (1, 1),
                            ["^1 == 1$", "^oops$", "^1 == 1$",
                             "^1 == 1 : oops$"])

    def testAlmostEqual(self):
        self.assertMessages(
            'assertAlmostEqual', (1, 2),
            [r"^1 != 2 within 7 places \(1 difference\)$", "^oops$",
             r"^1 != 2 within 7 places \(1 difference\)$",
             r"^1 != 2 within 7 places \(1 difference\) : oops$"])

    def testNotAlmostEqual(self):
        self.assertMessages('assertNotAlmostEqual', (1, 1),
                            ["^1 == 1 within 7 places$", "^oops$",
                             "^1 == 1 within 7 places$", "^1 == 1 within 7 places : oops$"])

    def testAssertIn(self):
        self.assertMessages('assertIn', (None, []),
                            [r'^None not found in \[\]$', "^oops$",
                             r'^None not found in \[\]$',
                             r'^None not found in \[\] : oops$'])

    def testAssertNotIn(self):
        self.assertMessages('assertNotIn', (None, [None]),
                            [r'^None unexpectedly found in \[None\]$', "^oops$",
                             r'^None unexpectedly found in \[None\]$',
                             r'^None unexpectedly found in \[None\] : oops$'])

    def testAssertLess(self):
        self.assertMessages('assertLess', (2, 1),
                            ["^2 not less than 1$", "^oops$",
                             "^2 not less than 1$", "^2 not less than 1 : oops$"])

    def testAssertLessEqual(self):
        self.assertMessages('assertLessEqual', (2, 1),
                            ["^2 not less than or equal to 1$", "^oops$",
                             "^2 not less than or equal to 1$",
                             "^2 not less than or equal to 1 : oops$"])

    def testAssertGreater(self):
        self.assertMessages('assertGreater', (1, 2),
                            ["^1 not greater than 2$", "^oops$",
                             "^1 not greater than 2$",
                             "^1 not greater than 2 : oops$"])

    def testAssertGreaterEqual(self):
        self.assertMessages('assertGreaterEqual', (1, 2),
                            ["^1 not greater than or equal to 2$", "^oops$",
                             "^1 not greater than or equal to 2$",
                             "^1 not greater than or equal to 2 : oops$"])

    def testAssertIsNone(self):
        self.assertMessages('assertIsNone', ('not None',),
                            ["^'not None' is not None$", "^oops$",
                             "^'not None' is not None$",
                             "^'not None' is not None : oops$"])

    def testAssertIsNotNone(self):
        self.assertMessages('assertIsNotNone', (None,),
                            ["^unexpectedly None$", "^oops$",
                             "^unexpectedly None$",
                             "^unexpectedly None : oops$"])

    def testAssertIs(self):
        self.assertMessages('assertIs', (None, 'foo'),
                            ["^None is not 'foo'$", "^oops$",
                             "^None is not 'foo'$",
                             "^None is not 'foo' : oops$"])

    def testAssertIsNot(self):
        self.assertMessages('assertIsNot', (None, None),
                            ["^unexpectedly identical: None$", "^oops$",
                             "^unexpectedly identical: None$",
                             "^unexpectedly identical: None : oops$"])

    def testAssertRegex(self):
        self.assertMessages('assertRegex', ('foo', 'bar'),
                            ["^Regex didn't match:",
                             "^oops$",
                             "^Regex didn't match:",
                             "^Regex didn't match: (.*) : oops$"])

    def testAssertNotRegex(self):
        self.assertMessages('assertNotRegex', ('foo', 'foo'),
                            ["^Regex matched:",
                             "^oops$",
                             "^Regex matched:",
                             "^Regex matched: (.*) : oops$"])

    def testAssertRaises(self):
        self.assertMessagesCM('assertRaises', (TypeError,), lambda: None,
                              ['^TypeError not raised$', '^oops$',
                               '^TypeError not raised$',
                               '^TypeError not raised : oops$'])

    def testAssertRaisesRegex(self):
        # test error not raised
        self.assertMessagesCM('assertRaisesRegex', (TypeError, 'unused regex'),
                              lambda: None,
                              ['^TypeError not raised$', '^oops$',
                               '^TypeError not raised$',
                               '^TypeError not raised : oops$'])
        # test error raised but with wrong message
        def raise_wrong_message():
            raise TypeError('foo')
        self.assertMessagesCM('assertRaisesRegex', (TypeError, 'regex'),
                              raise_wrong_message,
                              ['^"regex" does not match "foo"$', '^oops$',
                               '^"regex" does not match "foo"$',
                               '^"regex" does not match "foo" : oops$'])


class AssertionFailureTests(unittest.TestCase):
    def test_failures_raise(self):
        # Use an independent observer: broken assertRaises must not hide a
        # second broken assertion and allow the framework to certify itself.
        case = unittest.TestCase()
        failures = [
            ('fail', ('stop',)),
            ('assertEqual', (1, 2)),
            ('assertNotEqual', (1, 1)),
            ('assertTrue', (False,)),
            ('assertFalse', (True,)),
            ('assertIs', (None, 1)),
            ('assertIsNot', (None, None)),
            ('assertIsNone', (1,)),
            ('assertIsNotNone', (None,)),
            ('assertIn', (1, [])),
            ('assertNotIn', (1, [1])),
            ('assertLess', (2, 1)),
            ('assertLessEqual', (2, 1)),
            ('assertGreater', (1, 2)),
            ('assertGreaterEqual', (1, 2)),
            ('assertIsInstance', (1, str)),
            ('assertNotIsInstance', (1, int)),
            ('assertRegex', ('abc', 'xyz')),
            ('assertNotRegex', ('abc', 'abc')),
            ('assertAlmostEqual', (1, 2)),
            ('assertNotAlmostEqual', (1, 1)),
        ]
        for name, args in failures:
            try:
                getattr(case, name)(*args)
            except AssertionError:
                pass
            else:
                raise AssertionError(name + ' did not raise')

    def test_custom_failure_exception(self):
        class Failure(Exception):
            pass
        class Case(unittest.TestCase):
            failureException = Failure
        try:
            Case().assertEqual(1, 2, msg='custom failure')
        except Failure as error:
            assert 'custom failure' in str(error)
        else:
            raise AssertionError('failureException was ignored')

    def test_captured_exception_has_no_traceback(self):
        with self.assertRaises(ValueError) as context:
            raise ValueError('expected')
        assert context.exception.__traceback__ is None


if __name__ == '__main__':
    unittest.main()
