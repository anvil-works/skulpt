# Selected CPython3.14 Lib/test/test_code.py at18ef0f0cb52.
import types
import unittest

class CodeTest(unittest.TestCase):
    def test_qualname(self):
        self.assertEqual(
            CodeTest.test_qualname.__code__.co_qualname,
            CodeTest.test_qualname.__qualname__
        )

    # Functions and expected fields from CPython test_code's opening doctest.
    # Bytecode/names/constants output belongs to later metadata coverage.
    def test_doctest_local_and_closure_metadata(self):
        namespace = {}
        exec("def f(x):\n def g(y):\n  return x + y\n return g\ndef h(x, y):\n a = x + y\n b = x - y\n c = a * b\n return c", namespace)
        f = namespace['f']
        g = f(4)
        h = namespace['h']
        self.assertEqual(f.__code__.co_varnames, ('x', 'g'))
        self.assertEqual(f.__code__.co_cellvars, ('x',))
        self.assertEqual(f.__code__.co_freevars, ())
        self.assertEqual(f.__code__.co_nlocals, 2)
        self.assertEqual(f.__code__.co_flags, 3)
        self.assertEqual(g.__code__.co_varnames, ('y',))
        self.assertEqual(g.__code__.co_cellvars, ())
        self.assertEqual(g.__code__.co_freevars, ('x',))
        self.assertEqual(g.__code__.co_nlocals, 1)
        self.assertEqual(g.__code__.co_flags, 19)
        self.assertEqual(h.__code__.co_varnames, ('x', 'y', 'a', 'b', 'c'))
        self.assertEqual(h.__code__.co_nlocals, 5)
        self.assertEqual(g(3), 7)

    def test_compiled_code_identity_and_execution(self):
        class Filename(str):
            pass
        filename = Filename('source.py')
        code = compile('def f(): return 42', filename, 'exec')
        self.assertIsInstance(code, types.CodeType)
        self.assertEqual(code.co_name, '<module>')
        self.assertEqual(code.co_qualname, '<module>')
        self.assertEqual(code.co_firstlineno, 1)
        self.assertEqual(code.co_flags, 0)
        first = {}
        second = {}
        exec(code, first)
        exec(code, second)
        self.assertIs(first['f'].__code__, first['f'].__code__)
        self.assertIs(first['f'].__code__, second['f'].__code__)
        self.assertIs(first['f'].__code__.co_filename, filename)
        self.assertEqual(first['f'].__code__.co_firstlineno, 1)
        self.assertEqual(first['f'](), 42)
        self.assertEqual(eval(first['f'].__code__, {}), 42)
        self.assertEqual(eval(compile('6 * 7', filename, 'eval')), 42)
        self.assertIsNone(exec(first['f'].__code__, {}))

    def test_executable_source_line_boundaries(self):
        namespace = {}
        exec(compile("def f():\r return 42\rvalue = '\u2028\u2029'", '<lines>', 'exec'), namespace)
        self.assertEqual(namespace['f'](), 42)
        self.assertEqual(namespace['value'], '\u2028\u2029')

    def test_decorated_lines_and_method_flags(self):
        namespace = {}
        exec('def decorator(f): return f\n@decorator\n@decorator\ndef f(): pass\nclass C:\n def method(self): return __class__', namespace)
        self.assertEqual(namespace['f'].__code__.co_firstlineno, 2)
        self.assertEqual(namespace['C'].method.__code__.co_flags, 0x8000003)
        self.assertEqual(namespace['C'].method.__code__.co_freevars, ('__class__',))
        self.assertIs(namespace['C']().method(), namespace['C'])

    def test_local_order_across_comprehensions_and_dead_suites(self):
        namespace = {}
        exec('def f():\n before=1\n result=[x for x in [1]]\n after=3\n return result\ndef dead():\n if False: x=1\n while False: y=2\n z=3\n return z', namespace)
        self.assertEqual(namespace['f'].__code__.co_varnames, ('before', 'x', 'result', 'after'))
        self.assertEqual(namespace['dead'].__code__.co_varnames, ('x', 'y', 'z'))
        self.assertEqual(namespace['dead'](), 3)
        code = compile('result = [x for x in [1]]', '<module>', 'exec')
        self.assertEqual(code.co_varnames, ('x',))
        self.assertEqual(code.co_nlocals, 1)
        for source in ['if False: break', 'if True: pass\nelse: continue', 'while False: pass\nelse: return']:
            self.assertRaises(SyntaxError, compile, source, '<dead>', 'exec')

    def test_generator_and_comprehension_metadata(self):
        namespace = {}
        exec('def f(a, /, b, *args, c, **kwargs):\n "doc"\n local = 1\n yield a\ndef h(): return [lambda: x for x in [1]]', namespace)
        code = namespace['f'].__code__
        self.assertEqual(code.co_argcount, 2)
        self.assertEqual(code.co_posonlyargcount, 1)
        self.assertEqual(code.co_kwonlyargcount, 1)
        self.assertEqual(code.co_varnames, ('a', 'b', 'c', 'args', 'kwargs', 'local'))
        self.assertEqual(code.co_flags, 0x400002f)
        code = namespace['h'].__code__
        self.assertEqual(code.co_varnames, ('x',))
        self.assertEqual(code.co_cellvars, ('x',))
        self.assertEqual(namespace['h']()[0].__code__.co_freevars, ('x',))
        with self.assertRaises(AttributeError):
            code.co_name = 'different'
        self.assertEqual(namespace['h'].__code__.co_name, 'h')

if __name__ == '__main__':
    unittest.main()
