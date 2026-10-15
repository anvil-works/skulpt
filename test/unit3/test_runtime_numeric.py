import math
import unittest


class NumericDispatchTests(unittest.TestCase):
    def test_builtin_results_and_integer_promotion(self):
        for left, right in [(3, 2), (3.0, 2.0), (3, 2.0), (3.0, 2)]:
            expected_type = int if type(left) is int and type(right) is int else float
            for result, expected in [(left + right, 5), (left - right, 1),
                                     (left * right, 6)]:
                self.assertEqual(result, expected)
                self.assertIs(type(result), expected_type)
        for value in [3, 3.0]:
            for result, expected in [(value + 2, 5), (value - 2, 1),
                                     (value * 2, 6)]:
                self.assertEqual(result, expected)
                self.assertIs(type(result), type(value))
            for result, expected in [(value + 2.0, 5.0), (value - 2.0, 1.0),
                                     (value * 2.0, 6.0)]:
                self.assertEqual(result, expected)
                self.assertIs(type(result), float)
        self.assertEqual(9007199254740991 + 1, 9007199254740992)
        self.assertEqual(-9007199254740991 - 2, -9007199254740993)
        self.assertEqual(1000000007 * 1000000007, 1000000014000000049)
        self.assertEqual(-9007199254740991 * 3, -27021597764222973)
        self.assertEqual((1 << 100) + 3, 1267650600228229401496703205379)
        self.assertEqual(True + 2, 3)

    def test_subclasses_and_reflected_operators(self):
        class Int(int):
            def __add__(self, other):
                return "int add"
            def __rsub__(self, other):
                return "int reflected subtract"
        class Float(float):
            def __radd__(self, other):
                return "float reflected add"
            def __mul__(self, other):
                return "float multiply"
        self.assertEqual(Int(3) + 2, "int add")
        self.assertEqual(Int(3) + 2.0, "int add")
        self.assertEqual(3 - Int(2), "int reflected subtract")
        self.assertEqual(3 + Float(2), "float reflected add")
        self.assertEqual(3.0 + Float(2), "float reflected add")
        self.assertEqual(Float(3) * 2.0, "float multiply")

        class Reflected:
            def __radd__(self, other):
                return "custom reflected add"
        self.assertEqual(3 + Reflected(), "custom reflected add")
        self.assertEqual(3.0 + Reflected(), "custom reflected add")

    def test_signed_zero_and_nonfinite_floats(self):
        self.assertEqual(math.copysign(1, -0.0 * 3), -1)
        self.assertEqual(math.copysign(1, 0 * -3.0), -1)
        self.assertEqual(math.copysign(1, -0.0 - 0.0), -1)
        self.assertTrue(math.isnan(float("inf") - float("inf")))
        self.assertEqual(1e308 * 2.0, float("inf"))
        self.assertRaises(OverflowError, lambda: (10 ** 400) + 1.0)

    def test_literal_square_preserves_numeric_types_and_errors(self):
        def square(value):
            return value ** 2
        for value in [0, 3, -3, 9007199254740991, 1 << 100, True, 3.5, -3.5, 1e154,
                      1.0000000000000002, 0.9999999999999999, 3.141592653589793,
                      2.2250738585072014e-154, 2.2250738585072014e-162]:
            expected = pow(value, 2)
            result = square(value)
            self.assertEqual(result, expected)
            self.assertIs(type(result), type(expected))
        for value in [0.0, -0.0, 1e-200, -1e-200]:
            self.assertEqual(square(value), 0.0)
            self.assertEqual(math.copysign(1, square(value)), 1)
        self.assertEqual(square(float("inf")), float("inf"))
        self.assertEqual(square(-float("inf")), float("inf"))
        self.assertTrue(math.isnan(square(float("nan"))))
        self.assertRaises(OverflowError, square, 1e308)
        self.assertRaises(OverflowError, square, -1e308)
        self.assertEqual(square(complex(1, 2)), complex(-3, 4))

    def test_literal_square_preserves_custom_power_and_single_evaluation(self):
        def square(value):
            return value ** 2
        class Int(int):
            def __pow__(self, other):
                return ("int power", other)
        class Float(float):
            def __pow__(self, other):
                return ("float power", other)
        self.assertEqual(square(Int(3)), ("int power", 2))
        self.assertEqual(square(Float(3)), ("float power", 2))
        seen = []
        def operand():
            seen.append(1)
            return 1e308
        with self.assertRaises(OverflowError):
            operand() ** 2
        self.assertEqual(seen, [1])

    def test_generic_operations_remain_available(self):
        self.assertEqual("a" + "b", "ab")
        self.assertEqual([1] * 3, [1, 1, 1])
        self.assertEqual(3 * "ab", "ababab")
        self.assertRaises(TypeError, lambda: 1 + "a")
        self.assertRaises(TypeError, lambda: 1.0 - [])




class IntegerIndexTests(unittest.TestCase):
    def test_type_changes_at_the_same_indexing_site(self):
        def first(value):
            return value[0]
        class List(list):
            def __getitem__(self, index):
                return "subclass"
        class Mapping:
            def __getitem__(self, index):
                return ("custom", index)
        self.assertEqual(first([11]), 11)
        self.assertEqual(first(List([11])), "subclass")
        self.assertEqual(first(Mapping()), ("custom", 0))
        self.assertEqual(first({0: "dict"}), "dict")
        self.assertEqual(first((12,)), 12)
        self.assertEqual(first([13]), 13)
        self.assertRaises(IndexError, first, [])

    def test_bounds_and_other_index_forms(self):
        def second(value):
            return value[1]
        self.assertEqual(second([11, 12]), 12)
        self.assertRaises(IndexError, second, [11])
        self.assertEqual([11, 12][-1], 12)
        self.assertEqual([11, 12][0:1], [11])
        self.assertRaises(IndexError, lambda: [11][10 ** 100])
        values = [11]
        self.assertRaises(TypeError, lambda: values[0.0])
        class Index:
            def __index__(self):
                return 0
        self.assertEqual([11][Index()], 11)


if __name__ == "__main__":
    unittest.main()
