# CPython 3.14 Lib/test/test_builtin.py at 18ef0f0cb52.
# Five complete zip methods and iter_error helper are unchanged.
import unittest

class ZipStrict(unittest.TestCase):
    def iter_error(self, iterable, error):
        """Collect `iterable` into a list, catching an expected `error`."""
        items = []
        with self.assertRaises(error):
            for item in iterable:
                items.append(item)
        return items


    def test_zip_bad_iterable(self):
        exception = TypeError()

        class BadIterable:
            def __iter__(self):
                raise exception

        with self.assertRaises(TypeError) as cm:
            zip(BadIterable())

        self.assertIs(cm.exception, exception)


    def test_zip_strict(self):
        self.assertEqual(tuple(zip((1, 2, 3), 'abc', strict=True)),
                         ((1, 'a'), (2, 'b'), (3, 'c')))
        self.assertRaises(ValueError, tuple,
                          zip((1, 2, 3, 4), 'abc', strict=True))
        self.assertRaises(ValueError, tuple,
                          zip((1, 2), 'abc', strict=True))
        self.assertRaises(ValueError, tuple,
                          zip((1, 2), (1, 2), 'abc', strict=True))


    def test_zip_strict_iterators(self):
        x = iter(range(5))
        y = [0]
        z = iter(range(5))
        self.assertRaises(ValueError, list,
                          (zip(x, y, z, strict=True)))
        self.assertEqual(next(x), 2)
        self.assertEqual(next(z), 1)


    def test_zip_strict_error_handling(self):

        class Error(Exception):
            pass

        class Iter:
            def __init__(self, size):
                self.size = size
            def __iter__(self):
                return self
            def __next__(self):
                self.size -= 1
                if self.size < 0:
                    raise Error
                return self.size

        l1 = self.iter_error(zip("AB", Iter(1), strict=True), Error)
        self.assertEqual(l1, [("A", 0)])
        l2 = self.iter_error(zip("AB", Iter(2), "A", strict=True), ValueError)
        self.assertEqual(l2, [("A", 1, "A")])
        l3 = self.iter_error(zip("AB", Iter(2), "ABC", strict=True), Error)
        self.assertEqual(l3, [("A", 1, "A"), ("B", 0, "B")])
        l4 = self.iter_error(zip("AB", Iter(3), strict=True), ValueError)
        self.assertEqual(l4, [("A", 2), ("B", 1)])
        l5 = self.iter_error(zip(Iter(1), "AB", strict=True), Error)
        self.assertEqual(l5, [(0, "A")])
        l6 = self.iter_error(zip(Iter(2), "A", strict=True), ValueError)
        self.assertEqual(l6, [(1, "A")])
        l7 = self.iter_error(zip(Iter(2), "ABC", strict=True), Error)
        self.assertEqual(l7, [(1, "A"), (0, "B")])
        l8 = self.iter_error(zip(Iter(3), "AB", strict=True), ValueError)
        self.assertEqual(l8, [(2, "A"), (1, "B")])


    def test_zip_strict_error_handling_stopiteration(self):

        class Iter:
            def __init__(self, size):
                self.size = size
            def __iter__(self):
                return self
            def __next__(self):
                self.size -= 1
                if self.size < 0:
                    raise StopIteration
                return self.size

        l1 = self.iter_error(zip("AB", Iter(1), strict=True), ValueError)
        self.assertEqual(l1, [("A", 0)])
        l2 = self.iter_error(zip("AB", Iter(2), "A", strict=True), ValueError)
        self.assertEqual(l2, [("A", 1, "A")])
        l3 = self.iter_error(zip("AB", Iter(2), "ABC", strict=True), ValueError)
        self.assertEqual(l3, [("A", 1, "A"), ("B", 0, "B")])
        l4 = self.iter_error(zip("AB", Iter(3), strict=True), ValueError)
        self.assertEqual(l4, [("A", 2), ("B", 1)])
        l5 = self.iter_error(zip(Iter(1), "AB", strict=True), ValueError)
        self.assertEqual(l5, [(0, "A")])
        l6 = self.iter_error(zip(Iter(2), "A", strict=True), ValueError)
        self.assertEqual(l6, [(1, "A")])
        l7 = self.iter_error(zip(Iter(2), "ABC", strict=True), ValueError)
        self.assertEqual(l7, [(1, "A"), (0, "B")])
        l8 = self.iter_error(zip(Iter(3), "AB", strict=True), ValueError)
        self.assertEqual(l8, [(2, "A"), (1, "B")])


if __name__ == '__main__': unittest.main()
