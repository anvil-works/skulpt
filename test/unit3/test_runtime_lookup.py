import unittest


class LookupTests(unittest.TestCase):
    def test_method_lookup_precedes_argument_evaluation(self):
        class Value:
            def method(self, value):
                return "original", value
        obj = Value()
        def replace():
            Value.method = lambda self, value: ("replacement", value)
            return 3
        self.assertEqual(obj.method(replace()), ("original", 3))
        self.assertEqual(obj.method(4), ("replacement", 4))
        method = obj.method
        self.assertIs(method.__self__, obj)
        self.assertIs(method.__func__, Value.method)

    def test_shadowing_descriptors_and_custom_attribute_access(self):
        def invoke(obj):
            return obj.method(3)
        class Value:
            def method(self, value):
                return "method", value
        class Property(Value):
            @property
            def method(self):
                return lambda value: ("property", value)
        class Missing:
            def __getattr__(self, name):
                return lambda value: ("getattr", value)
        class Custom:
            def __getattribute__(self, name):
                return lambda value: ("getattribute", value)
        obj = Value()
        self.assertEqual(invoke(obj), ("method", 3))
        obj.method = lambda value: ("shadow", value)
        self.assertEqual(invoke(obj), ("shadow", 3))
        del obj.method
        self.assertEqual(invoke(obj), ("method", 3))
        for obj, label in [(Property(), "property"), (Missing(), "getattr"), (Custom(), "getattribute")]:
            self.assertEqual(invoke(obj), (label, 3))
        obj = Property()
        obj.__dict__["method"] = lambda value: ("shadow", value)
        self.assertEqual(invoke(obj), ("property", 3))
        events = []
        with self.assertRaises(AttributeError):
            Value().missing(events.append(1))
        self.assertEqual(events, [])

    def test_method_call_variants(self):
        class Value:
            def __hidden(self, value):
                return value
            def call_hidden(self):
                return self.__hidden(3)
            @staticmethod
            def static(value):
                return value
            @classmethod
            def klass(cls, value):
                return cls, value
        obj = Value()
        self.assertEqual(obj.call_hidden(), 3)
        self.assertEqual(obj.static(4), 4)
        self.assertEqual(obj.klass(5), (Value, 5))
        self.assertEqual(obj.static(value=6), 6)
        self.assertEqual(obj.static(*[7]), 7)

    def test_globals_remain_dynamic(self):
        global lookup_value
        def read():
            return lookup_value
        lookup_value = 3
        self.assertEqual(read(), 3)
        lookup_value = 4
        self.assertEqual(read(), 4)
        del lookup_value
        with self.assertRaises(NameError):
            read()

    def test_builtin_shadowing_remains_dynamic(self):
        global abs
        def read():
            return abs(-3)
        self.assertEqual(read(), 3)
        abs = lambda value: "shadow"
        self.assertEqual(read(), "shadow")
        del abs
        self.assertEqual(read(), 3)


if __name__ == "__main__":
    unittest.main()
