"""Skulpt runner regressions for skip reporting.

CPython's test_unittest.test_skipping covers related teardown cases
through TestResult. These tests check the summary Skulpt's CI reads.
"""

import sys
import unittest


class TestSkipping(unittest.TestCase):
    def run_case(self, case):
        output = []

        class Output:
            def write(self, text):
                output.append(text)

        stdout = sys.stdout
        sys.stdout = Output()
        try:
            case().main()
        finally:
            sys.stdout = stdout
        return ''.join(output)

    def test_body_skip_runs_teardown(self):
        events = []

        class Case(unittest.TestCase):
            def test_skip(self):
                self.skipTest("skip from the test")

            def tearDown(self):
                events.append("teardown")

        output = self.run_case(Case)
        self.assertEqual(events, ["teardown"])
        self.assertIn("passed: 0 failed: 0 skipped: 1", output)

    def test_skip_preserves_assertion_failure(self):
        for skip_in_teardown in (False, True):
            class Case(unittest.TestCase):
                def test_failure(self):
                    self.fail("intentional failure")
                    if not skip_in_teardown:
                        self.skipTest("skip from the test")

                def tearDown(self):
                    if skip_in_teardown:
                        self.skipTest("skip from teardown")

            output = self.run_case(Case)
            self.assertIn("passed: 0 failed: 1 skipped: 0", output)


# Selected from CPython Lib/test/test_unittest/test_case.py at 18ef0f0cb52.
# Uses its LoggingTestCase and supported LoggingResult callbacks from support.py.
class Test:
    class LoggingTestCase(unittest.TestCase):
            """A test case which logs its calls."""

            def __init__(self, events):
                super(Test.LoggingTestCase, self).__init__('test')
                self.events = events

            def setUp(self):
                self.events.append('setUp')

            def test(self):
                self.events.append('test')

            def tearDown(self):
                self.events.append('tearDown')


class LoggingResult(unittest.TestResult):

    def __init__(self, log):
        self._events = log
        super().__init__()

    def startTest(self, test):
        self._events.append('startTest')
        super().startTest(test)

    def startTestRun(self):
        self._events.append('startTestRun')
        super().startTestRun()

    def stopTest(self, test):
        self._events.append('stopTest')
        super().stopTest(test)

    def stopTestRun(self):
        self._events.append('stopTestRun')
        super().stopTestRun()

    def addFailure(self, *args):
        self._events.append('addFailure')
        super().addFailure(*args)

    def addSuccess(self, *args):
        self._events.append('addSuccess')
        super().addSuccess(*args)

    def addError(self, *args):
        self._events.append('addError')
        super().addError(*args)

    def addSkip(self, *args):
        self._events.append('addSkip')
        super().addSkip(*args)


class TestCaseRun(unittest.TestCase):

    def test_run_call_order__error_in_setUp(self):
        events = []
        result = LoggingResult(events)

        class Foo(Test.LoggingTestCase):
            def setUp(self):
                super(Foo, self).setUp()
                raise RuntimeError('raised by Foo.setUp')

        Foo(events).run(result)
        expected = ['startTest', 'setUp', 'addError', 'stopTest']
        self.assertEqual(events, expected)

    def test_run_call_order__failure_in_test(self):
        events = []
        result = LoggingResult(events)

        class Foo(Test.LoggingTestCase):
            def test(self):
                super(Foo, self).test()
                self.fail('raised by Foo.test')

        expected = ['startTest', 'setUp', 'test',
                    'addFailure', 'tearDown', 'stopTest']
        Foo(events).run(result)
        self.assertEqual(events, expected)

    def test_run_call_order__error_in_tearDown(self):
        events = []
        result = LoggingResult(events)

        class Foo(Test.LoggingTestCase):
            def tearDown(self):
                super(Foo, self).tearDown()
                raise RuntimeError('raised by Foo.tearDown')

        Foo(events).run(result)
        expected = ['startTest', 'setUp', 'test', 'tearDown', 'addError',
                    'stopTest']
        self.assertEqual(events, expected)

    def test_failureException__default(self):
        class Foo(unittest.TestCase):
            def test(self):
                pass

        self.assertIs(Foo('test').failureException, AssertionError)

    def test_failureException__subclassing__implicit_raise(self):
        events = []
        result = LoggingResult(events)

        class Foo(unittest.TestCase):
            def test(self):
                self.fail("foo")

            failureException = RuntimeError

        self.assertIs(Foo('test').failureException, RuntimeError)


        Foo('test').run(result)
        expected = ['startTest', 'addFailure', 'stopTest']
        self.assertEqual(events, expected)

    def test_run__returns_given_result(self):

        class Foo(unittest.TestCase):
            def test(self):
                pass

        result = unittest.TestResult()

        retval = Foo('test').run(result)
        self.assertIs(retval, result)

    def test_call__invoking_an_instance_delegates_to_run(self):
        resultIn = unittest.TestResult()
        resultOut = unittest.TestResult()

        class Foo(unittest.TestCase):
            def test(self):
                pass

            def run(self, result):
                self.assertIs(result, resultIn)
                return resultOut

        retval = Foo('test')(resultIn)

        self.assertIs(retval, resultOut)

    # From CPython Lib/test/test_unittest/test_skipping.py at 18ef0f0cb52.
    def test_skipping(self):
        class Foo(unittest.TestCase):
            def defaultTestResult(self):
                return LoggingResult(events)
            def test_skip_me(self):
                self.skipTest("skip")
        events = []
        result = LoggingResult(events)
        test = Foo("test_skip_me")
        self.assertIs(test.run(result), result)
        self.assertEqual(events, ['startTest', 'addSkip', 'stopTest'])
        self.assertEqual(result.skipped, [(test, "skip")])

        events = []
        result = test.run()
        self.assertEqual(events, ['startTestRun', 'startTest', 'addSkip',
                                  'stopTest', 'stopTestRun'])
        self.assertEqual(result.skipped, [(test, "skip")])
        self.assertEqual(result.testsRun, 1)

        # Try letting setUp skip the test now.
        class Foo(unittest.TestCase):
            def defaultTestResult(self):
                return LoggingResult(events)
            def setUp(self):
                self.skipTest("testing")
            def test_nothing(self): pass
        events = []
        result = LoggingResult(events)
        test = Foo("test_nothing")
        self.assertIs(test.run(result), result)
        self.assertEqual(events, ['startTest', 'addSkip', 'stopTest'])
        self.assertEqual(result.skipped, [(test, "testing")])
        self.assertEqual(result.testsRun, 1)

        events = []
        result = test.run()
        self.assertEqual(events, ['startTestRun', 'startTest', 'addSkip',
                                  'stopTest', 'stopTestRun'])
        self.assertEqual(result.skipped, [(test, "testing")])
        self.assertEqual(result.testsRun, 1)

    def test_raising_assertions(self):
        # Run the CPython test_assertions.py body through the single-test API.
        class Assertions(unittest.TestCase):
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

        result = Assertions("test_assertRaises").run()
        self.assertEqual(result.failures, [])
        self.assertEqual(result.errors, [])


# From CPython Lib/test/test_unittest/test_runner.py at 18ef0f0cb52.
class CustomError(Exception):
    pass


class TestCM:
    def __init__(self, ordering, enter_result=None):
        self.ordering = ordering
        self.enter_result = enter_result

    def __enter__(self):
        self.ordering.append('enter')
        return self.enter_result

    def __exit__(self, *exc_info):
        self.ordering.append('exit')


class TestCleanUp(unittest.TestCase):

    def testCleanUp(self):
        class TestableTest(unittest.TestCase):
            def testNothing(self):
                pass

        test = TestableTest('testNothing')
        self.assertEqual(test._cleanups, [])

        cleanups = []

        def cleanup1(*args, **kwargs):
            cleanups.append((1, args, kwargs))

        def cleanup2(*args, **kwargs):
            cleanups.append((2, args, kwargs))

        test.addCleanup(cleanup1, 1, 2, 3, four='hello', five='goodbye')
        test.addCleanup(cleanup2)

        self.assertEqual(test._cleanups,
                         [(cleanup1, (1, 2, 3), dict(four='hello', five='goodbye')),
                          (cleanup2, (), {})])

        self.assertTrue(test.doCleanups())
        self.assertEqual(cleanups, [(2, (), {}), (1, (1, 2, 3), dict(four='hello', five='goodbye'))])

    def testCleanupInRun(self):
        blowUp = False
        ordering = []

        class TestableTest(unittest.TestCase):
            def setUp(self):
                ordering.append('setUp')
                test.addCleanup(cleanup2)
                if blowUp:
                    raise CustomError('foo')

            def testNothing(self):
                ordering.append('test')
                test.addCleanup(cleanup3)

            def tearDown(self):
                ordering.append('tearDown')

        test = TestableTest('testNothing')

        def cleanup1():
            ordering.append('cleanup1')
        def cleanup2():
            ordering.append('cleanup2')
        def cleanup3():
            ordering.append('cleanup3')
        test.addCleanup(cleanup1)

        def success(some_test):
            self.assertEqual(some_test, test)
            ordering.append('success')

        result = unittest.TestResult()
        result.addSuccess = success

        test.run(result)
        self.assertEqual(ordering, ['setUp', 'test', 'tearDown', 'cleanup3',
                                    'cleanup2', 'cleanup1', 'success'])

        blowUp = True
        ordering = []
        test = TestableTest('testNothing')
        test.addCleanup(cleanup1)
        test.run(result)
        self.assertEqual(ordering, ['setUp', 'cleanup2', 'cleanup1'])

    def test_enterContext(self):
        class TestableTest(unittest.TestCase):
            def testNothing(self):
                pass

        test = TestableTest('testNothing')
        cleanups = []

        test.addCleanup(cleanups.append, 'cleanup1')
        cm = TestCM(cleanups, 42)
        self.assertEqual(test.enterContext(cm), 42)
        test.addCleanup(cleanups.append, 'cleanup2')

        self.assertTrue(test.doCleanups())
        self.assertEqual(cleanups, ['enter', 'cleanup2', 'exit', 'cleanup1'])


class List(list):
    pass


class TestAssertionHelpers(unittest.TestCase):
    def test_cpython_assertions(self):
        # From CPython test_case.py at 18ef0f0cb52. Run the assertions in raising mode.
        # assertCountEqual utility-internal cases require the separate unittest.util module.
        class Assertions(unittest.TestCase):
            def testAssertHasAttr(self):
                a = List()
                a.x = 1
                self.assertHasAttr(a, 'x')
                with self.assertRaises(self.failureException) as cm:
                    self.assertHasAttr(a, 'y')
                self.assertEqual(str(cm.exception),
                        "'List' object has no attribute 'y'")
                with self.assertRaises(self.failureException) as cm:
                    self.assertHasAttr(List, 'spam')
                self.assertEqual(str(cm.exception),
                        "type object 'List' has no attribute 'spam'")
                with self.assertRaises(self.failureException) as cm:
                    self.assertHasAttr(sys, 'nonexistent')
                self.assertEqual(str(cm.exception),
                        "module 'sys' has no attribute 'nonexistent'")

                with self.assertRaises(self.failureException) as cm:
                    self.assertHasAttr(a, 'y', 'ababahalamaha')
                self.assertIn('ababahalamaha', str(cm.exception))
                with self.assertRaises(self.failureException) as cm:
                    self.assertHasAttr(a, 'y', msg='ababahalamaha')
                self.assertIn('ababahalamaha', str(cm.exception))

            def testAssertNotHasAttr(self):
                a = List()
                a.x = 1
                self.assertNotHasAttr(a, 'y')
                with self.assertRaises(self.failureException) as cm:
                    self.assertNotHasAttr(a, 'x')
                self.assertEqual(str(cm.exception),
                        "'List' object has unexpected attribute 'x'")
                with self.assertRaises(self.failureException) as cm:
                    self.assertNotHasAttr(List, 'append')
                self.assertEqual(str(cm.exception),
                        "type object 'List' has unexpected attribute 'append'")
                with self.assertRaises(self.failureException) as cm:
                    self.assertNotHasAttr(sys, 'modules')
                self.assertEqual(str(cm.exception),
                        "module 'sys' has unexpected attribute 'modules'")

                with self.assertRaises(self.failureException) as cm:
                    self.assertNotHasAttr(a, 'x', 'ababahalamaha')
                self.assertIn('ababahalamaha', str(cm.exception))
                with self.assertRaises(self.failureException) as cm:
                    self.assertNotHasAttr(a, 'x', msg='ababahalamaha')
                self.assertIn('ababahalamaha', str(cm.exception))

            def testAssertCountEqual(self):
                a = object()
                self.assertCountEqual([1, 2, 3], [3, 2, 1])
                self.assertCountEqual(['foo', 'bar', 'baz'], ['bar', 'baz', 'foo'])
                self.assertCountEqual([a, a, 2, 2, 3], (a, 2, 3, a, 2))
                self.assertCountEqual([1, "2", "a", "a"], ["a", "2", True, "a"])
                self.assertRaises(self.failureException, self.assertCountEqual,
                                  [1, 2] + [3] * 100, [1] * 100 + [2, 3])
                self.assertRaises(self.failureException, self.assertCountEqual,
                                  [1, "2", "a", "a"], ["a", "2", True, 1])
                self.assertRaises(self.failureException, self.assertCountEqual,
                                  [10], [10, 11])
                self.assertRaises(self.failureException, self.assertCountEqual,
                                  [10, 11], [10])
                self.assertRaises(self.failureException, self.assertCountEqual,
                                  [10, 11, 10], [10, 11])

                # Test that sequences of unhashable objects can be tested for sameness:
                self.assertCountEqual([[1, 2], [3, 4], 0], [False, [3, 4], [1, 2]])
                # Test that iterator of unhashable objects can be tested for sameness:
                self.assertCountEqual(iter([1, 2, [], 3, 4]),
                                      iter([1, 2, [], 3, 4]))

                # hashable types, but not orderable
                self.assertRaises(self.failureException, self.assertCountEqual,
                                  [], [divmod, 'x', 1, 5j, 2j, frozenset()])
                # comparing dicts
                self.assertCountEqual([{'a': 1}, {'b': 2}], [{'b': 2}, {'a': 1}])
                # comparing heterogeneous non-hashable sequences
                self.assertCountEqual([1, 'x', divmod, []], [divmod, [], 'x', 1])
                self.assertRaises(self.failureException, self.assertCountEqual,
                                  [], [divmod, [], 'x', 1, 5j, 2j, set()])
                self.assertRaises(self.failureException, self.assertCountEqual,
                                  [[1]], [[2]])

                # Same elements, but not same sequence length
                self.assertRaises(self.failureException, self.assertCountEqual,
                                  [1, 1, 2], [2, 1])
                self.assertRaises(self.failureException, self.assertCountEqual,
                                  [1, 1, "2", "a", "a"], ["2", "2", True, "a"])
                self.assertRaises(self.failureException, self.assertCountEqual,
                                  [1, {'b': 2}, None, True], [{'b': 2}, True, None])

                # Same elements which don't reliably compare, in
                # different order, see issue 10242
                a = [{2,4}, {1,2}]
                b = a[::-1]
                self.assertCountEqual(a, b)

        for name in ("testAssertHasAttr", "testAssertNotHasAttr", "testAssertCountEqual"):
            result = Assertions(name).run()
            self.assertEqual(result.failures, [])
            self.assertEqual(result.errors, [])


if __name__ == '__main__':
    unittest.main()
