# Selected complete CPython 3.14 rich comparison tests and fixtures.
import unittest, operator

class Number:

    def __init__(self, x):
        self.x = x

    def __lt__(self, other):
        return self.x < other

    def __le__(self, other):
        return self.x <= other

    def __eq__(self, other):
        return self.x == other

    def __ne__(self, other):
        return self.x != other

    def __gt__(self, other):
        return self.x > other

    def __ge__(self, other):
        return self.x >= other

    def __repr__(self):
        return "Number(%r)" % (self.x, )


class Vector:

    def __init__(self, data):
        self.data = data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, i):
        return self.data[i]

    def __setitem__(self, i, v):
        self.data[i] = v

    __hash__ = None # Vectors cannot be hashed

    def __bool__(self):
        raise TypeError("Vectors cannot be used in Boolean contexts")

    def __repr__(self):
        return "Vector(%r)" % (self.data, )

    def __lt__(self, other):
        return Vector([a < b for a, b in zip(self.data, self.__cast(other))])

    def __le__(self, other):
        return Vector([a <= b for a, b in zip(self.data, self.__cast(other))])

    def __eq__(self, other):
        return Vector([a == b for a, b in zip(self.data, self.__cast(other))])

    def __ne__(self, other):
        return Vector([a != b for a, b in zip(self.data, self.__cast(other))])

    def __gt__(self, other):
        return Vector([a > b for a, b in zip(self.data, self.__cast(other))])

    def __ge__(self, other):
        return Vector([a >= b for a, b in zip(self.data, self.__cast(other))])

    def __cast(self, other):
        if isinstance(other, Vector):
            other = other.data
        if len(self.data) != len(other):
            raise ValueError("Cannot compare vectors of different length")
        return other


opmap = {
    "lt": (lambda a,b: a< b, operator.lt, operator.__lt__),
    "le": (lambda a,b: a<=b, operator.le, operator.__le__),
    "eq": (lambda a,b: a==b, operator.eq, operator.__eq__),
    "ne": (lambda a,b: a!=b, operator.ne, operator.__ne__),
    "gt": (lambda a,b: a> b, operator.gt, operator.__gt__),
    "ge": (lambda a,b: a>=b, operator.ge, operator.__ge__)
}


class VectorTest(unittest.TestCase):

    def checkfail(self, error, opname, *args):
        for op in opmap[opname]:
            self.assertRaises(error, op, *args)

    def checkequal(self, opname, a, b, expres):
        for op in opmap[opname]:
            realres = op(a, b)
            # can't use assertEqual(realres, expres) here
            self.assertEqual(len(realres), len(expres))
            for i in range(len(realres)):
                # results are bool, so we can use "is" here
                self.assertTrue(realres[i] is expres[i])

    def test_mixed(self):
        # check that comparisons involving Vector objects
        # which return rich results (i.e. Vectors with itemwise
        # comparison results) work
        a = Vector(range(2))
        b = Vector(range(3))
        # all comparisons should fail for different length
        for opname in opmap:
            self.checkfail(ValueError, opname, a, b)

        a = list(range(5))
        b = 5 * [2]
        # try mixed arguments (but not (a, b) as that won't return a bool vector)
        args = [(a, Vector(b)), (Vector(a), b), (Vector(a), Vector(b))]
        for (a, b) in args:
            self.checkequal("lt", a, b, [True,  True,  False, False, False])
            self.checkequal("le", a, b, [True,  True,  True,  False, False])
            self.checkequal("eq", a, b, [False, False, True,  False, False])
            self.checkequal("ne", a, b, [True,  True,  False, True,  True ])
            self.checkequal("gt", a, b, [False, False, False, True,  True ])
            self.checkequal("ge", a, b, [False, False, True,  True,  True ])

            for ops in opmap.values():
                for op in ops:
                    # calls __bool__, which should fail
                    self.assertRaises(TypeError, bool, op(a, b))


class NumberTest(unittest.TestCase):

    def test_basic(self):
        # Check that comparisons involving Number objects
        # give the same results give as comparing the
        # corresponding ints
        for a in range(3):
            for b in range(3):
                for typea in (int, Number):
                    for typeb in (int, Number):
                        if typea==typeb==int:
                            continue # the combination int, int is useless
                        ta = typea(a)
                        tb = typeb(b)
                        for ops in opmap.values():
                            for op in ops:
                                realoutcome = op(a, b)
                                testoutcome = op(ta, tb)
                                self.assertEqual(realoutcome, testoutcome)

    def checkvalue(self, opname, a, b, expres):
        for typea in (int, Number):
            for typeb in (int, Number):
                ta = typea(a)
                tb = typeb(b)
                for op in opmap[opname]:
                    realres = op(ta, tb)
                    realres = getattr(realres, "x", realres)
                    self.assertTrue(realres is expres)

    def test_values(self):
        # check all operators and all comparison results
        self.checkvalue("lt", 0, 0, False)
        self.checkvalue("le", 0, 0, True )
        self.checkvalue("eq", 0, 0, True )
        self.checkvalue("ne", 0, 0, False)
        self.checkvalue("gt", 0, 0, False)
        self.checkvalue("ge", 0, 0, True )

        self.checkvalue("lt", 0, 1, True )
        self.checkvalue("le", 0, 1, True )
        self.checkvalue("eq", 0, 1, False)
        self.checkvalue("ne", 0, 1, True )
        self.checkvalue("gt", 0, 1, False)
        self.checkvalue("ge", 0, 1, False)

        self.checkvalue("lt", 1, 0, False)
        self.checkvalue("le", 1, 0, False)
        self.checkvalue("eq", 1, 0, False)
        self.checkvalue("ne", 1, 0, True )
        self.checkvalue("gt", 1, 0, True )
        self.checkvalue("ge", 1, 0, True )


class MiscTest(unittest.TestCase):
    def test_misbehavin(self):
        class Misb:
            def __lt__(self_, other): return 0
            def __gt__(self_, other): return 0
            def __eq__(self_, other): return 0
            def __le__(self_, other): self.fail("This shouldn't happen")
            def __ge__(self_, other): self.fail("This shouldn't happen")
            def __ne__(self_, other): self.fail("This shouldn't happen")
        a = Misb()
        b = Misb()
        self.assertEqual(a<b, 0)
        self.assertEqual(a==b, 0)
        self.assertEqual(a>b, 0)


    def test_not(self):
        # Check that exceptions in __bool__ are properly
        # propagated by the not operator
        import operator
        class Exc(Exception):
            pass
        class Bad:
            def __bool__(self):
                raise Exc

        def do(bad):
            not bad

        for func in (do, operator.not_):
            self.assertRaises(Exc, func, Bad())


# Complete CPython test_grammar comparison method, including the short-circuit chain.
class GrammarComparisonTest(unittest.TestCase):
    def test_comparison(self):
        ### comparison: expr (comp_op expr)*
        ### comp_op: '<'|'>'|'=='|'>='|'<='|'!='|'in'|'not' 'in'|'is'|'is' 'not'
        if 1: pass
        x = (1 == 1)
        if 1 == 1: pass
        if 1 != 1: pass
        if 1 < 1: pass
        if 1 > 1: pass
        if 1 <= 1: pass
        if 1 >= 1: pass
        if x is x: pass
        if x is not x: pass
        if 1 in (): pass
        if 1 not in (): pass
        if 1 < 1 > 1 == 1 >= 1 <= 1 != 1 in 1 not in x is x is not x: pass

if __name__ == '__main__': unittest.main()
