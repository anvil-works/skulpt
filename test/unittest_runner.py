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

# Regex assertions must keep working in both language modes. Python 2 does
# not expose the bytes name used by CPython 3's string-type check.
case = unittest.TestCase()
case.assertRegex('abc', 'b')
case.assertNotRegex('abc', 'z')
with case.assertRaises(AssertionError):
    case.assertRegex('abc', 'z')
with case.assertRaises(AssertionError):
    case.assertNotRegex('abc', 'b')


events = []
class StaticSetup(unittest.TestCase):
    @staticmethod
    def setUp():
        events.append('setUp')
        raise ValueError('static setup failure')
    def test_body(self):
        events.append('unreachable')
case = StaticSetup()
case.main()
assert events == ['setUp']
assert case.numPassed == 0 and case.numFailed == 1

events = []
class StaticBody(unittest.TestCase):
    @staticmethod
    def test_body():
        events.append('static body')
case = StaticBody()
case.main()
assert events == ['static body']
assert case.numPassed == 1 and case.numFailed == 0

# Exercise the real GUI runner with an in-memory document. No browser is needed.
import sys
class Element:
    def __init__(self):
        self.children = []
        self.innerHTML = ''
    def appendChild(self, child):
        self.children.append(child)
    def setAttribute(self, name, value):
        pass
    def setCSS(self, name, value):
        pass

document = type(sys)('document')
container = Element()
document.currentDiv = lambda: 'test'
document.getElementById = lambda name: container if name == 'test' else None
document.createElement = lambda name: Element()
sys.modules['document'] = document
from unittest.gui import TestCaseGui

events = []
class GuiCase(TestCaseGui):
    def test_body(self):
        self.assertEqual(1, 1)
        self.assertEqual(1, 2)
        self.fail('explicit failure')
        events.append('continued after assertions')
        raise ValueError('GUI body failure')
    def tearDown(self):
        events.append('tearDown')
        raise ValueError('GUI teardown failure')
case = GuiCase()
case.main()
assert events == ['continued after assertions', 'tearDown']
assert case.numPassed == 1 and case.numFailed == 4
notes = [row.children[-1].innerHTML for row in case.resTable.children[1:]]
assert notes[0] == ''
assert '1 != 2' in notes[1]
assert 'explicit failure' in notes[2]
assert 'GUI body failure' in notes[3]
assert 'GUI teardown failure' in notes[4]

# attrgetter has no __name__; formatting its diagnostic must not stop the call.
import operator
unittest.TestCase().assertRaises(AttributeError, operator.attrgetter('missing'), object())

print('Unittest runner checks passed')
