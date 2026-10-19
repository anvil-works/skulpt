# Assertion behaviour follows CPython 3.14 Lib/unittest/case.py at 18ef0f0cb52.
# This module retains Skulpt's lightweight runner and unittest.gui result hook.
import re


def _safe_repr(obj):
    try:
        return repr(obj)
    except Exception:
        return object.__repr__(obj)


class _AssertRaisesContext(object):
    def __init__(self, expected, test_case, expected_regex=None):
        self.expected = expected
        self.test_case = test_case
        self.exception = None
        self.expected_regex = re.compile(expected_regex) if expected_regex is not None else None
        self.msg = None
        self.obj_name = None

    def _is_subtype(self, expected, basetype):
        if isinstance(expected, tuple):
            return all(self._is_subtype(e, basetype) for e in expected)
        return isinstance(expected, type) and issubclass(expected, basetype)

    def handle(self, name, args, kwargs):
        if not self._is_subtype(self.expected, BaseException):
            raise TypeError('%s() arg 1 must be an exception type or tuple of exception types' % name)
        if not args:
            self.msg = kwargs.pop('msg', None)
            if kwargs:
                raise TypeError('%r is an invalid keyword argument for this function' % next(iter(kwargs)))
            return self
        callable_obj = args[0]
        try:
            self.obj_name = callable_obj.__name__
        except AttributeError:
            self.obj_name = str(callable_obj)
        with self:
            callable_obj(*args[1:], **kwargs)

    def __enter__(self):
        return self

    def _raiseFailure(self, message):
        message = self.test_case._formatMessage(self.msg, message)
        self.test_case.appendResult(False, None, self.expected, message)

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            try:
                name = self.expected.__name__
            except AttributeError:
                name = str(self.expected)
            message = '%s not raised' % name
            if self.obj_name:
                message += ' by %s' % self.obj_name
            self._raiseFailure(message)
            return True
        if not issubclass(exc_type, self.expected):
            return False
        # Native traceback objects are available; traceback.clear_frames is not.
        self.exception = exc_value.with_traceback(None)
        if self.expected_regex is not None and not self.expected_regex.search(str(exc_value)):
            self._raiseFailure('"%s" does not match "%s"' % (self.expected_regex.pattern, exc_value))
            return True
        self.test_case.appendResult(True, exc_type, self.expected, self.msg)
        return True


class TestCase(object):
    failureException = AssertionError
    longMessage = True

    def __init__(self):
        self.numPassed = 0
        self.numFailed = 0
        self.assertPassed = 0
        self.assertFailed = 0
        self.verbosity = 1
        self.tlist = []
        testNames = {}
        for name in dir(self):
            if name[:4] == 'test' and name not in testNames:
                self.tlist.append(getattr(self,name))
                testNames[name]=True

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def cleanName(self,funcName):
        return funcName.__func__.__name__

    def _runTestPart(self, func):
        # Record each failing phase separately, so a teardown error does not
        # hide the original failure and setup errors prevent the test body.
        try:
            func()
        except Exception as error:
            self.assertFailed += 1
            print('Test threw exception in %s (%s)' % (self.cleanName(func), error))
            return False
        return True

    def main(self):
        for func in self.tlist:
            if self.verbosity > 1:
                print('Running %s' % self.cleanName(func))
            self.assertPassed = 0
            self.assertFailed = 0
            if self._runTestPart(self.setUp):
                self._runTestPart(func)
                self._runTestPart(self.tearDown)
            if self.assertFailed:
                self.numFailed += 1
            else:
                self.numPassed += 1
        self.showSummary()

    def _formatMessage(self, msg, standardMsg):
        """Honour the longMessage attribute when generating failure messages.
        If longMessage is False this means:
        * Use only an explicit message if it is provided
        * Otherwise use the standard message for the assert

        If longMessage is True:
        * Use the standard message
        * If an explicit message is provided, plus ' : ' and the explicit message
        """
        if not self.longMessage:
            return msg or standardMsg
        if msg is None:
            return standardMsg
        try:
            # don't switch to '{}' formatting in Python 2.X
            # it changes the way unicode input is handled
            return '%s : %s' % (standardMsg, msg)
        except UnicodeDecodeError:
            return  '%s : %s' % (_safe_repr(standardMsg), _safe_repr(msg))

    def assertEqual(self, first, second, msg=None):
        res = bool(first == second)
        if not res:
            msg = self._formatMessage(msg, '%s != %s' % (_safe_repr(first), _safe_repr(second)))
        self.appendResult(res, first, second, msg)

    def assertNotEqual(self, first, second, msg=None):
        res = bool(first != second)
        if not res:
            msg = self._formatMessage(msg, '%s == %s' % (_safe_repr(first), _safe_repr(second)))
        self.appendResult(res, first, second, msg)

    def assertTrue(self, expr, msg=None):
        res = bool(expr)
        if not res:
            msg = self._formatMessage(msg, '%s is not true' % _safe_repr(expr))
        self.appendResult(res, expr, True, msg)

    def assertFalse(self, expr, msg=None):
        res = not expr
        if not res:
            msg = self._formatMessage(msg, '%s is not false' % _safe_repr(expr))
        self.appendResult(res, expr, False, msg)

    def assertIs(self, expr1, expr2, msg=None):
        res = expr1 is expr2
        if not res:
            msg = self._formatMessage(msg, '%s is not %s' % (_safe_repr(expr1), _safe_repr(expr2)))
        self.appendResult(res, expr1, expr2, msg)

    def assertIsNot(self, expr1, expr2, msg=None):
        res = expr1 is not expr2
        if not res:
            msg = self._formatMessage(msg, 'unexpectedly identical: %s' % _safe_repr(expr1))
        self.appendResult(res, expr1, expr2, msg)

    def assertIsNone(self, obj, msg=None):
        res = obj is None
        if not res:
            msg = self._formatMessage(msg, '%s is not None' % _safe_repr(obj))
        self.appendResult(res, obj, None, msg)

    def assertIsNotNone(self, obj, msg=None):
        res = obj is not None
        if not res:
            msg = self._formatMessage(msg, 'unexpectedly None')
        self.appendResult(res, obj, None, msg)

    def assertIn(self, member, container, msg=None):
        res = member in container
        if not res:
            msg = self._formatMessage(msg, '%s not found in %s' % (_safe_repr(member), _safe_repr(container)))
        self.appendResult(res, member, container, msg)

    def assertNotIn(self, member, container, msg=None):
        res = member not in container
        if not res:
            msg = self._formatMessage(msg, '%s unexpectedly found in %s' % (_safe_repr(member), _safe_repr(container)))
        self.appendResult(res, member, container, msg)

    def assertGreater(self, a, b, msg=None):
        res = bool(a > b)
        if not res:
            msg = self._formatMessage(msg, '%s not greater than %s' % (_safe_repr(a), _safe_repr(b)))
        self.appendResult(res, a, b, msg)

    def assertGreaterEqual(self, a, b, msg=None):
        res = bool(a >= b)
        if not res:
            msg = self._formatMessage(msg, '%s not greater than or equal to %s' % (_safe_repr(a), _safe_repr(b)))
        self.appendResult(res, a, b, msg)

    def assertLess(self, a, b, msg=None):
        res = bool(a < b)
        if not res:
            msg = self._formatMessage(msg, '%s not less than %s' % (_safe_repr(a), _safe_repr(b)))
        self.appendResult(res, a, b, msg)

    def assertLessEqual(self, a, b, msg=None):
        res = bool(a <= b)
        if not res:
            msg = self._formatMessage(msg, '%s not less than or equal to %s' % (_safe_repr(a), _safe_repr(b)))
        self.appendResult(res, a, b, msg)

    def assertIsInstance(self, obj, cls, msg=None):
        """Same as self.assertTrue(isinstance(obj, cls)), with a nicer
        default message."""
        if not isinstance(obj, cls):
            if isinstance(cls, tuple):
                standardMsg = '%s is not an instance of any of %r' % (_safe_repr(obj), cls)
            else:
                standardMsg = '%s is not an instance of %r' % (_safe_repr(obj), cls)
            return self.appendResult(False, obj, cls, self._formatMessage(msg, standardMsg))
        self.appendResult(True, obj, cls, msg)

    def assertNotIsInstance(self, obj, cls, msg=None):
        """Included for symmetry with assertIsInstance."""
        if isinstance(obj, cls):
            if isinstance(cls, tuple):
                for x in cls:
                    if isinstance(obj, x):
                        cls = x
                        break
            standardMsg = '%s is an instance of %r' % (_safe_repr(obj), cls)
            return self.appendResult(False, obj, cls, self._formatMessage(msg, standardMsg))
        self.appendResult(True, obj, cls, msg)

    def assertRegex(self, text, expected_regex, msg=None):
        """Fail the test unless the text matches the regular expression."""
        if isinstance(expected_regex, (str, bytes)):
            assert expected_regex, "expected_regex must not be empty."
            expected_regex = re.compile(expected_regex)
        if not expected_regex.search(text):
            standardMsg = "Regex didn't match: %r not found in %r" % (
                expected_regex.pattern, text)
            # _formatMessage ensures the longMessage option is respected
            msg = self._formatMessage(msg, standardMsg)
            return self.appendResult(False, text, expected_regex, msg)
        self.appendResult(True, text, expected_regex, msg)

    def assertNotRegex(self, text, unexpected_regex, msg=None):
        """Fail the test if the text matches the regular expression."""
        if isinstance(unexpected_regex, (str, bytes)):
            unexpected_regex = re.compile(unexpected_regex)
        match = unexpected_regex.search(text)
        if match:
            standardMsg = 'Regex matched: %r matches %r in %r' % (
                text[match.start() : match.end()],
                unexpected_regex.pattern,
                text)
            # _formatMessage ensures the longMessage option is respected
            msg = self._formatMessage(msg, standardMsg)
            return self.appendResult(False, text, unexpected_regex, msg)
        self.appendResult(True, text, unexpected_regex, msg)

    def assertAlmostEqual(self, first, second, places=None, msg=None,
                          delta=None):
        """Fail if the two objects are unequal as determined by their
           difference rounded to the given number of decimal places
           (default 7) and comparing to zero, or by comparing that the
           difference between the two objects is more than the given
           delta.

           Note that decimal places (from zero) are usually not the same
           as significant digits (measured from the most significant digit).

           If the two objects compare equal then they will automatically
           compare almost equal.
        """
        if first == second:
            # shortcut
            self.appendResult(True, first, second, msg)
            return
        if delta is not None and places is not None:
            raise TypeError("specify delta or places not both")

        diff = abs(first - second)
        if delta is not None:
            if diff <= delta:
                self.appendResult(True, first, second, msg)
                return

            standardMsg = '%s != %s within %s delta (%s difference)' % (
                _safe_repr(first),
                _safe_repr(second),
                _safe_repr(delta),
                _safe_repr(diff))
        else:
            if places is None:
                places = 7

            if round(diff, places) == 0:
                self.appendResult(True, first, second, msg)
                return

            standardMsg = '%s != %s within %r places (%s difference)' % (
                _safe_repr(first),
                _safe_repr(second),
                places,
                _safe_repr(diff))
        msg = self._formatMessage(msg, standardMsg)
        return self.appendResult(False, first, second, msg)

    def assertNotAlmostEqual(self, first, second, places=None, msg=None,
                             delta=None):
        """Fail if the two objects are equal as determined by their
           difference rounded to the given number of decimal places
           (default 7) and comparing to zero, or by comparing that the
           difference between the two objects is less than the given delta.

           Note that decimal places (from zero) are usually not the same
           as significant digits (measured from the most significant digit).

           Objects that are equal automatically fail.
        """
        if delta is not None and places is not None:
            raise TypeError("specify delta or places not both")
        diff = abs(first - second)
        if delta is not None:
            if not (first == second) and diff > delta:
                self.appendResult(True, first, second, msg)
                return
            standardMsg = '%s == %s within %s delta (%s difference)' % (
                _safe_repr(first),
                _safe_repr(second),
                _safe_repr(delta),
                _safe_repr(diff))
        else:
            if places is None:
                places = 7
            if not (first == second) and round(diff, places) != 0:
                self.appendResult(True, first, second, msg)
                return
            standardMsg = '%s == %s within %r places' % (_safe_repr(first),
                                                         _safe_repr(second),
                                                         places)

        msg = self._formatMessage(msg, standardMsg)
        return self.appendResult(False, first, second, msg)

    def appendResult(self, res, actual, expected, feedback):
        # unittest.gui overrides this hook to display every assertion.
        if res:
            self.assertPassed += 1
        else:
            self.fail(feedback)

    def assertRaises(self, expected_exception, *args, **kwargs):
        return _AssertRaisesContext(expected_exception, self).handle('assertRaises', args, kwargs)

    def assertRaisesRegex(self, expected_exception, expected_regex, *args, **kwargs):
        context = _AssertRaisesContext(expected_exception, self, expected_regex)
        return context.handle('assertRaisesRegex', args, kwargs)

    def fail(self, msg=None):
        raise self.failureException(msg)

    def showSummary(self):
        # don't divde by zero
        # pct = self.numPassed / (self.numPassed+self.numFailed) * 100
        print("Ran %d tests, passed: %d failed: %d\n" % (self.numPassed+self.numFailed,
                                               self.numPassed, self.numFailed))



def main(verbosity=1, module="__main__"):
    import sys
    glob = vars(sys.modules[module])
    # Test methods may add module globals; discover names before running them.
    for name in list(glob):
        if type(glob[name]) == type and issubclass(glob[name], TestCase):
            try:
                tc = glob[name]()
                tc.verbosity = verbosity
                tc.main()
            except:
                print("Uncaught Error in: ", name)
