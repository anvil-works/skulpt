""" Unit test for hash"""
import unittest

class HashTest(unittest.TestCase):
    def test_integers(self):
        self.assertEqual(hash(int()),hash(int()))
        self.assertEqual(hash(332), hash(332))
        self.assertEqual(hash(-47), hash(-47))

    def test_float(self):
        self.assertEqual(hash(float()), hash(float()))
        self.assertEqual(hash(33.2), hash(33.2))
        self.assertEqual(hash(0.05), hash(0.05))
        self.assertEqual(hash(-11.85), hash(-11.85))

    def test_strings(self):
        self.assertEqual(hash(''), hash(''))
        self.assertEqual(hash('hello'), hash('hello'))

    def test_tuples(self):
        self.assertEqual(hash(()), hash(()))
        self.assertEqual(hash((1,2,3)), hash((1,2,3,)))

    def test_int_and_float(self):
        self.assertEqual(hash(1), hash(1.0))
        self.assertEqual(hash(-5), hash(-5.0))

# Complete selected CPython Lib/test/test_hash.py inheritance tests and fixtures.
_default_hash = object.__hash__

class DefaultHash(object): pass

_FIXED_HASH_VALUE = 42

class FixedHash(object):
    def __hash__(self):
        return _FIXED_HASH_VALUE

class OnlyEquality(object):
    def __eq__(self, other):
        return self is other

class OnlyInequality(object):
    def __ne__(self, other):
        return self is not other

class InheritedHashWithEquality(FixedHash, OnlyEquality): pass

class InheritedHashWithInequality(FixedHash, OnlyInequality): pass

class NoHash(object):
    __hash__ = None

class HashInheritanceTestCase(unittest.TestCase):
    default_expected = [object(),
                        DefaultHash(),
                        OnlyInequality(),
                       ]
    fixed_expected = [FixedHash(),
                      InheritedHashWithEquality(),
                      InheritedHashWithInequality(),
                      ]
    error_expected = [NoHash(),
                      OnlyEquality(),
                      ]
    def test_default_hash(self):
        for obj in self.default_expected:
            self.assertEqual(hash(obj), _default_hash(obj))
    def test_fixed_hash(self):
        for obj in self.fixed_expected:
            self.assertEqual(hash(obj), _FIXED_HASH_VALUE)
    def test_error_hash(self):
        for obj in self.error_expected:
            self.assertRaises(TypeError, hash, obj)

# CPython test_except_star: TestExceptStar_WeirdExceptionGroupSubclass fixture.
class AlwaysEqualEG(ExceptionGroup):
    def __eq__(self, other):
        return True

    def derive(self, excs):
        return type(self)(self.message, excs)

HashInheritanceTestCase.error_expected.append(AlwaysEqualEG("eg", [ValueError(1)]))

if __name__ == '__main__':
    unittest.main()
