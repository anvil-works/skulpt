# Python-2.0 license. Complete CPython 3.14 test_global pattern methods.
import unittest
# Fixture adapter: Skulpt has no types.SimpleNamespace; this test only needs
# its keyword-initialized attributes, not its repr or comparison protocols.
class SimpleNamespace:
    def __init__(self, **kwargs): self.__dict__.update(kwargs)

class PatternGlobalsTests(unittest.TestCase):
    def test_match(self):
        global name_match
        value = object()
        match value:
            case name_match:
                pass
        self.assertIs(globals()["name_match"], value)
        del name_match


    def test_match_as(self):
        global name_match_as
        value = object()
        match value:
            case _ as name_match_as:
                pass
        self.assertIs(globals()["name_match_as"], value)
        del name_match_as


    def test_match_seq(self):
        global name_match_seq
        value = object()
        match (None, value):
            case (_, name_match_seq):
                pass
        self.assertIs(globals()["name_match_seq"], value)
        del name_match_seq


    def test_match_map(self):
        global name_match_map
        value = object()
        match {"key": value}:
            case {"key": name_match_map}:
                pass
        self.assertIs(globals()["name_match_map"], value)
        del name_match_map


    def test_match_attr(self):
        global name_match_attr
        value = object()
        match SimpleNamespace(key=value):
            case SimpleNamespace(key=name_match_attr):
                pass
        self.assertIs(globals()["name_match_attr"], value)
        del name_match_attr


class PatternScopesTests(unittest.TestCase):
    # CPython-checked regression: captures use ordinary cell/nonlocal binding,
    # and the subject survives yields in guards across case boundaries.
    def test_closure_and_generator_guard(self):
        captured = None
        def bind(subject):
            nonlocal captured
            match subject:
                case {'value': captured}:
                    return lambda: captured
        value = object()
        closure = bind({'value': value})
        self.assertIs(closure(), value)
        self.assertIs(captured, value)
        def cases(subject):
            match subject:
                case None: return
                case [a, b] if (yield a): return b
                case [a, b]: return a + b
        gen = cases([2, 3])
        self.assertEqual(next(gen), 2)
        with self.assertRaises(StopIteration) as caught:
            gen.send(False)
        self.assertEqual(caught.exception.value, 5)
        gen = cases([2, 3])
        self.assertEqual(next(gen), 2)
        with self.assertRaises(StopIteration) as caught:
            gen.send(True)
        self.assertEqual(caught.exception.value, 3)

if __name__ == '__main__':
    unittest.main()
