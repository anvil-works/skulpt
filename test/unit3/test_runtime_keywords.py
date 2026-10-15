import unittest


class KeywordUnpackingTests(unittest.TestCase):
    def test_exact_dict_order_key_checks_and_duplicate_arguments(self):
        calls = []
        def capture(**kwargs):
            calls.append(1)
            return list(kwargs.items())
        source = {"last": 1, "__proto__": 2, "constructor": 3, "0": 4, "first": 5}
        del source["constructor"]
        source["constructor"] = 6
        expected = [("last", 1), ("__proto__", 2), ("0", 4), ("first", 5), ("constructor", 6)]
        self.assertEqual(capture(**source), expected)
        self.assertEqual(list(source.items()), expected)
        class String(str):
            pass
        self.assertEqual(capture(**{String("value"): 7}), [("value", 7)])
        with self.assertRaises(TypeError):
            capture(**{"valid": 1, 2: "invalid"})
        self.assertEqual(len(calls), 2)
        def named(first):
            return first
        with self.assertRaises(TypeError):
            named(first=1, **{"first": 2})

    def test_mapping_and_dict_subclass_paths(self):
        def capture(**kwargs):
            return list(kwargs.items())
        seen = []
        class Mapping:
            def keys(self):
                seen.append("keys")
                return ["second", "first"]
            def __getitem__(self, key):
                seen.append(key)
                return {"first": 1, "second": 2}[key]
        self.assertEqual(capture(**Mapping()), [("second", 2), ("first", 1)])
        self.assertEqual(seen, ["keys", "second", "first"])
        class Dict(dict):
            def items(self):
                raise AssertionError("items override should not be called")
        self.assertEqual(capture(**Dict(second=2, first=1)), [("second", 2), ("first", 1)])
        self.assertEqual(capture(**{}), [])


if __name__ == "__main__":
    unittest.main()
