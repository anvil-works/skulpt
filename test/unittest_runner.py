# Lifecycle expectations follow CPython 3.14 Lib/unittest/case.py: TestCase.run
# and test_unittest/test_case.py's setup/body/teardown call-order tests.
import unittest


events = []
class BodyFailure(unittest.TestCase):
    def setUp(self):
        events.append('setUp')
    def test_body(self):
        events.append('body')
        self.fail('body failure')
        events.append('unreachable')
    def tearDown(self):
        events.append('tearDown')
        raise ValueError('teardown failure')
case = BodyFailure()
case.main()
assert events == ['setUp', 'body', 'tearDown']
assert case.numPassed == 0 and case.numFailed == 1
assert case.assertFailed == 2


events = []
class SetupFailure(unittest.TestCase):
    def setUp(self):
        events.append('setUp')
        self.assertTrue(False)
    def test_body(self):
        events.append('body')
    def tearDown(self):
        events.append('tearDown')
case = SetupFailure()
case.main()
assert events == ['setUp']
assert case.numPassed == 0 and case.numFailed == 1


# Each test starts with fresh assertion counters, including assertions in setup.
events = []
class FollowingTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(True)
    def test_first(self):
        raise ValueError('first fails')
    def test_second(self):
        events.append('second')
case = FollowingTest()
case.main()
assert events == ['second']
assert case.numPassed == 1 and case.numFailed == 1
assert case.assertPassed == 1 and case.assertFailed == 0


# The GUI's existing appendResult hook still receives passing and failing
# assertions and can display a failure without stopping the following checks.
results = []
class Reporter(unittest.TestCase):
    def appendResult(self, res, actual, expected, feedback):
        results.append((res, actual, expected, feedback))
case = Reporter()
case.assertEqual(1, 1)
case.assertEqual(1, 2, msg='reported')
with case.assertRaises(ValueError):
    pass
assert len(results) == 3
assert results[0][:3] == (True, 1, 1)
assert results[1] == (False, 1, 2, '1 != 2 : reported')
assert results[2][0] is False

print('Unittest runner checks passed')
