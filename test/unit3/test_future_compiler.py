# CPython-checked future compilation regressions; 3.14 at 18ef0f0cb52.
import __future__
import unittest

class FutureCompilerTest(unittest.TestCase):
    def test_runtime_imports_and_mandatory_source_flags(self):
        for feature in __future__.all_feature_names:
            if feature in ('barry_as_FLUFL', 'annotations'): continue
            ns = {}
            code = compile('"doc"\nfrom __future__ import ' + feature + ' as value\ndef f(): pass', 'future.py', 'exec')
            exec(code, ns)
            self.assertIs(ns['value'], getattr(__future__, feature))
            self.assertEqual(code.co_flags & 0x1fe0000, 0)
            self.assertEqual(ns['f'].__code__.co_flags & 0x1fe0000, 0)

    def test_inheritance_compile_exec_eval_and_dont_inherit(self):
        ns = {}
        flags = __future__.division.compiler_flag | __future__.print_function.compiler_flag
        source = """
def f():
    implicit = compile('pass', 'nested.py', 'exec').co_flags
    explicit = compile('pass', 'nested.py', 'exec', dont_inherit=True).co_flags
    local = {}
    exec('def nested(): pass', {}, local)
    evaluated = eval('lambda: None').__code__.co_flags
    return implicit, explicit, local['nested'].__code__.co_flags, evaluated
class C:
    flags = compile('pass', 'class.py', 'exec').co_flags

def gen():
    yield compile('pass', 'generator.py', 'exec').co_flags
    yield compile('pass', 'generator.py', 'exec').co_flags
"""
        co = compile(source, 'parent.py', 'exec', flags, dont_inherit=True)
        exec(co, ns)
        implicit, explicit, executed, evaluated = ns['f']()
        for result in (implicit, executed, evaluated, ns['C'].flags):
            self.assertEqual(result & 0x1fe0000, flags)
        self.assertEqual(explicit & 0x1fe0000, 0)
        gen = ns['gen']()
        self.assertEqual(next(gen) & 0x1fe0000, flags)
        self.assertEqual(compile('pass', 'outside.py', 'exec').co_flags & 0x1fe0000, 0)
        self.assertEqual(next(gen) & 0x1fe0000, flags)
        with self.assertRaises(StopIteration): next(gen)

    def test_nested_bit_is_not_inherited(self):
        ns = {}
        exec(compile("result = compile('pass', 'nested.py', 'exec').co_flags", 'parent.py', 'exec', flags=0x10), ns)
        self.assertEqual(ns['result'] & 0x10, 0)

    def test_invalid_future_placement_and_names(self):
        for source in [
            'pass; from __future__ import division',
            'from __future__ import division; import sys; from __future__ import division',
            '\'doc\'\n\'extra\'\nfrom __future__ import division',
            'if False:\n from __future__ import division',
            'def f():\n from __future__ import division',
            'class C:\n from __future__ import division',
            'from __future__ import braces',
            'from __future__ import unknown',
            'from __future__ import *',
        ]:
            with self.assertRaises(SyntaxError): compile(source, 'future.py', 'exec')

if __name__ == '__main__': unittest.main()
