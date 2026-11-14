# CPython 3.14 Lib/test/test_compile.py at 18ef0f0cb52.
# Selected method bodies and assertions are unchanged.
import unittest
import textwrap

# Global fixture from CPython test_builtin.py.
A_GLOBAL_VALUE = 123

class TestSpecifics(unittest.TestCase):
    def test_exec_with_general_mapping_for_locals(self):

        class M:
            "Test mapping interface versus possible calls from eval()."
            def __getitem__(self, key):
                if key == 'a':
                    return 12
                raise KeyError
            def __setitem__(self, key, value):
                self.results = (key, value)
            def keys(self):
                return list('xyz')

        m = M()
        g = globals()
        exec('z = a', g, m)
        self.assertEqual(m.results, ('z', 12))
        try:
            exec('z = b', g, m)
        except NameError:
            pass
        else:
            self.fail('Did not detect a KeyError')
        exec('z = dir()', g, m)
        self.assertEqual(m.results, ('z', list('xyz')))
        exec('z = globals()', g, m)
        self.assertEqual(m.results, ('z', g))
        exec('z = locals()', g, m)
        self.assertEqual(m.results, ('z', m))
        self.assertRaises(TypeError, exec, 'z = b', m)

        class A:
            "Non-mapping"
            pass
        m = A()
        self.assertRaises(TypeError, exec, 'z = a', g, m)

        # Verify that dict subclasses work as well
        class D(dict):
            def __getitem__(self, key):
                if key == 'a':
                    return 12
                return dict.__getitem__(self, key)
        d = D()
        exec('z = a', g, d)
        self.assertEqual(d['z'], 12)

    # CPython test_builtin.py methods; assertions unchanged. The UserDict
    # fixture call is omitted because that stdlib class is not implemented.
    def test_eval_kwargs(self):
        data = {"A_GLOBAL_VALUE": 456}
        self.assertEqual(eval("globals()['A_GLOBAL_VALUE']", globals=data), 456)
        self.assertEqual(eval("globals()['A_GLOBAL_VALUE']", locals=data), 123)

    def test_general_eval(self):
        # Tests that general mappings can be used for the locals argument

        class M:
            "Test mapping interface versus possible calls from eval()."
            def __getitem__(self, key):
                if key == 'a':
                    return 12
                raise KeyError
            def keys(self):
                return list('xyz')

        m = M()
        g = globals()
        self.assertEqual(eval('a', g, m), 12)
        self.assertRaises(NameError, eval, 'b', g, m)
        self.assertEqual(eval('dir()', g, m), list('xyz'))
        self.assertEqual(eval('globals()', g, m), g)
        self.assertEqual(eval('locals()', g, m), m)
        self.assertRaises(TypeError, eval, 'a', m)
        class A:
            "Non-mapping"
            pass
        m = A()
        self.assertRaises(TypeError, eval, 'a', g, m)

        # Verify that dict subclasses work as well
        class D(dict):
            def __getitem__(self, key):
                if key == 'a':
                    return 12
                return dict.__getitem__(self, key)
            def keys(self):
                return list('xyz')

        d = D()
        self.assertEqual(eval('a', g, d), 12)
        self.assertRaises(NameError, eval, 'b', g, d)
        self.assertEqual(eval('dir()', g, d), list('xyz'))
        self.assertEqual(eval('globals()', g, d), g)
        self.assertEqual(eval('locals()', g, d), d)

        # Verify locals stores (used by list comps)
        eval('[locals() for i in (2,3)]', g, d)
        # collections.UserDict fixture is unavailable in Skulpt; deferred stdlib coverage.

        class SpreadSheet:
            "Sample application showing nested, calculated lookups."
            _cells = {}
            def __setitem__(self, key, formula):
                self._cells[key] = formula
            def __getitem__(self, key):
                return eval(self._cells[key], globals(), self)

        ss = SpreadSheet()
        ss['a1'] = '5'
        ss['a2'] = 'a1*6'
        ss['a3'] = 'a2*7'
        self.assertEqual(ss['a3'], 210)

        # Verify that dir() catches a non-list returned by eval
        # SF bug #1004669
        class C:
            def __getitem__(self, item):
                raise KeyError(item)
            def keys(self):
                return 1 # used to be 'a' but that's no longer an error
        self.assertRaises(TypeError, eval, 'dir()', globals(), C())

    def test_exec_kwargs(self):
        g = {}
        exec('global z\nz = 1', globals=g)
        if '__builtins__' in g:
            del g['__builtins__']
        self.assertEqual(g, {'z': 1})

        # if we only set locals, the global assignment will not
        # reach this locals dictionary
        g = {}
        exec('global z\nz = 1', locals=g)
        self.assertEqual(g, {})

    # Additional unchanged CPython methods; subTest infrastructure adapted.
    def test_no_ending_newline(self):
        compile("hi", "<test>", "exec")
        compile("hi\r", "<test>", "exec")

    def test_empty(self):
        compile("", "<test>", "exec")

    def test_other_newlines(self):
        compile("\r\n", "<test>", "exec")
        compile("\r", "<test>", "exec")
        compile("hi\r\nstuff\r\ndef f():\n    pass\r", "<test>", "exec")
        compile("this_is\rreally_old_mac\rdef f():\n    pass", "<test>", "exec")

    def test_debug_assignment(self):
        # catch assignments to __debug__
        self.assertRaises(SyntaxError, compile, '__debug__ = 1', '?', 'single')
        import builtins
        prev = builtins.__debug__
        setattr(builtins, '__debug__', 'sure')
        self.assertEqual(__debug__, prev)
        setattr(builtins, '__debug__', prev)

    def test_argument_handling(self):
        # detect duplicate positional and keyword arguments
        self.assertRaises(SyntaxError, eval, 'lambda a,a:0')
        self.assertRaises(SyntaxError, eval, 'lambda a,a=1:0')
        self.assertRaises(SyntaxError, eval, 'lambda a=1,a=1:0')
        self.assertRaises(SyntaxError, exec, 'def f(a, a): pass')
        self.assertRaises(SyntaxError, exec, 'def f(a = 0, a = 1): pass')
        self.assertRaises(SyntaxError, exec, 'def f(a): global a; a = 1')

    def test_syntax_error(self):
        self.assertRaises(SyntaxError, compile, "1+*3", "filename", "exec")

    def test_none_keyword_arg(self):
        self.assertRaises(SyntaxError, compile, "f(None=1)", "<string>", "exec")

    def test_duplicate_global_local(self):
        self.assertRaises(SyntaxError, exec, 'def f(a): global a; a = 1')

    def test_docstring(self):
        src = textwrap.dedent("""
            def with_docstring():
                "docstring"

            def two_strings():
                "docstring"
                "not docstring"

            def with_fstring():
                f"not docstring"

            def with_const_expression():
                "also" + " not docstring"

            def multiple_const_strings():
                "not docstring " * 3
            """)

        for opt in [0, 1, 2]:
            if True:  # Skulpt unittest has no subTest context.
                code = compile(src, "<test>", "exec", optimize=opt)
                ns = {}
                exec(code, ns)

                if opt < 2:
                    self.assertEqual(ns['with_docstring'].__doc__, "docstring")
                    self.assertEqual(ns['two_strings'].__doc__, "docstring")
                else:
                    self.assertIsNone(ns['with_docstring'].__doc__)
                    self.assertIsNone(ns['two_strings'].__doc__)
                self.assertIsNone(ns['with_fstring'].__doc__)
                self.assertIsNone(ns['with_const_expression'].__doc__)
                self.assertIsNone(ns['multiple_const_strings'].__doc__)

    # CPython BuiltinTest.test_compile source optimization cases, same assertions.
    def test_compile_optimization(self):
        codestr = '''def f():
        """doc"""
        debug_enabled = False
        if __debug__:
            debug_enabled = True
        try:
            assert False
        except AssertionError:
            return (True, f.__doc__, debug_enabled, __debug__)
        else:
            return (False, f.__doc__, debug_enabled, __debug__)
        '''
        def f(): """doc"""
        values = [(-1, __debug__, f.__doc__, __debug__, __debug__),
                  (0, True, 'doc', True, True),
                  (1, False, 'doc', False, False),
                  (2, False, None, False, False)]
        for optval, *expected in values:
            if True:  # No subTest support in Skulpt unittest.
            # Preserve upstream source-compilation assertions; AST path deferred.
                codeobjs = []
                codeobjs.append(compile(codestr, "<test>", "exec", optimize=optval))
                # AST-input compilation remains a separate increment.
                for code in codeobjs:
                    ns = {}
                    exec(code, ns)
                    rv = ns['f']()
                    self.assertEqual(rv, tuple(expected))

    # Argument/error cases selected from CPython BuiltinTest.test_compile.
    # Bytes/buffer source and AST cases remain separate increments.
    def test_compile_option_arguments(self):
        compile(source='pass', filename='?', mode='exec')
        compile(dont_inherit=False, filename='tmp', source='0', mode='eval')
        compile('pass', '?', dont_inherit=True, mode='exec')
        self.assertRaises(TypeError, compile)
        self.assertRaises(ValueError, compile, 'print(42)\n', '<string>', 'badmode')
        self.assertRaises(ValueError, compile, 'print(42)\n', '<string>', 'single', 0xff)
        self.assertRaises(TypeError, compile, 'pass', '?', 'exec',
                          mode='eval', source='0', filename='tmp')

    # CPython interactive-mode methods; assertions unchanged.
    def compile_single(self, source):
        compile(source, "<single>", "single")

    def assertInvalidSingle(self, source):
        self.assertRaises(SyntaxError, self.compile_single, source)

    def test_single_statement(self):
        self.compile_single("1 + 2")
        self.compile_single("\n1 + 2")
        self.compile_single("1 + 2\n")
        self.compile_single("1 + 2\n\n")
        self.compile_single("1 + 2\t\t\n")
        self.compile_single("1 + 2\t\t\n        ")
        self.compile_single("1 + 2 # one plus two")
        self.compile_single("1; 2")
        self.compile_single("import sys; sys")
        self.compile_single("def f():\n   pass")
        self.compile_single("while False:\n   pass")
        self.compile_single("if x:\n   f(x)")
        self.compile_single("if x:\n   f(x)\nelse:\n   g(x)")
        self.compile_single("class T:\n   pass")
        self.compile_single("c = '''\na=1\nb=2\nc=3\n'''")

    def test_bad_single_statement(self):
        self.assertInvalidSingle('1\n2')
        self.assertInvalidSingle('def f(): pass')
        self.assertInvalidSingle('a = 13\nb = 187')
        self.assertInvalidSingle('del x\ndel y')
        self.assertInvalidSingle('f()\ng()')
        self.assertInvalidSingle('f()\n# blah\nblah()')
        self.assertInvalidSingle('f()\nxy # blah\nblah()')
        self.assertInvalidSingle('x = 5 # comment\nx = 6\n')
        self.assertInvalidSingle("c = '''\nd=1\n'''\na = 1\n\nb = 2\n")

    def test_docstring_interactive_mode(self):
        srcs = [
            """def with_docstring():
                "docstring"
            """,
            """class with_docstring:
                "docstring"
            """,
        ]

        for opt in [0, 1, 2]:
            for src in srcs:
                if True:  # No subTest context in Skulpt unittest.
                    code = compile(textwrap.dedent(src), "<test>", "single", optimize=opt)
                    ns = {}
                    exec(code, ns)
                    if opt < 2:
                        self.assertEqual(ns['with_docstring'].__doc__, "docstring")
                    else:
                        self.assertIsNone(ns['with_docstring'].__doc__)

if __name__ == "__main__":
    unittest.main()
