# CPython 3.14 Lib/test/test_compile.py at 18ef0f0cb52.
# Selected method bodies and assertions are unchanged.
import unittest
import textwrap
import types

# Global fixture from CPython test_builtin.py.
A_GLOBAL_VALUE = 123

class FakePath:
    """Simple implementation of the path protocol.
    """
    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return f'<FakePath {self.path!r}>'

    def __fspath__(self):
        if (isinstance(self.path, BaseException) or
            isinstance(self.path, type) and
                issubclass(self.path, BaseException)):
            raise self.path
        else:
            return self.path

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

    # CPython encoding method, unchanged.
    def test_encoding(self):
        code = b'# -*- coding: badencoding -*-\npass\n'
        self.assertRaises(SyntaxError, compile, code, 'tmp', 'exec')
        code = '# -*- coding: badencoding -*-\n"\xc2\xa4"\n'
        compile(code, 'tmp', 'exec')
        self.assertEqual(eval(code), '\xc2\xa4')
        code = '"\xc2\xa4"\n'
        self.assertEqual(eval(code), '\xc2\xa4')
        code = b'"\xc2\xa4"\n'
        self.assertEqual(eval(code), '\xa4')
        code = b'# -*- coding: latin1 -*-\n"\xc2\xa4"\n'
        self.assertEqual(eval(code), '\xc2\xa4')
        code = b'# -*- coding: utf-8 -*-\n"\xc2\xa4"\n'
        self.assertEqual(eval(code), '\xa4')
        code = b'# -*- coding: iso8859-15 -*-\n"\xc2\xa4"\n'
        self.assertEqual(eval(code), '\xc2\u20ac')
        code = '"""\\\n# -*- coding: iso8859-15 -*-\n\xc2\xa4"""\n'
        self.assertEqual(eval(code), '# -*- coding: iso8859-15 -*-\n\xc2\xa4')
        code = b'"""\\\n# -*- coding: iso8859-15 -*-\n\xc2\xa4"""\n'
        self.assertEqual(eval(code), '# -*- coding: iso8859-15 -*-\n\xa4')

    # CPython test_builtin.py custom-builtin methods, unchanged.
    def test_exec_globals(self):
        code = compile("print('Hello World!')", "", "exec")
        # no builtin function
        self.assertRaisesRegex(NameError, "name 'print' is not defined",
                               exec, code, {'__builtins__': {}})
        # __builtins__ must be a mapping type
        self.assertRaises(TypeError,
                          exec, code, {'__builtins__': 123})
    def test_exec_globals_error_on_get(self):
        # custom `globals` or `builtins` can raise errors on item access
        class setonlyerror(Exception):
            pass

        class setonlydict(dict):
            def __getitem__(self, key):
                raise setonlyerror

        # globals' `__getitem__` raises
        code = compile("globalname", "test", "exec")
        self.assertRaises(setonlyerror,
                          exec, code, setonlydict({'globalname': 1}))

        # builtins' `__getitem__` raises
        code = compile("superglobal", "test", "exec")
        self.assertRaises(setonlyerror, exec, code,
                          {'__builtins__': setonlydict({'superglobal': 1})})
    def test_exec_globals_dict_subclass(self):
        class customdict(dict):  # this one should not do anything fancy
            pass

        code = compile("superglobal", "test", "exec")
        # works correctly
        exec(code, {'__builtins__': customdict({'superglobal': 1})})
        # custom builtins dict subclass is missing key
        self.assertRaisesRegex(NameError, "name 'superglobal' is not defined",
                               exec, code, {'__builtins__': customdict()})
    def test_eval_builtins_mapping(self):
        code = compile("superglobal", "test", "eval")
        # works correctly
        ns = {'__builtins__': types.MappingProxyType({'superglobal': 1})}
        self.assertEqual(eval(code, ns), 1)
        # custom builtins mapping is missing key
        ns = {'__builtins__': types.MappingProxyType({})}
        self.assertRaisesRegex(NameError, "name 'superglobal' is not defined",
                               eval, code, ns)
    def test_exec_builtins_mapping_import(self):
        code = compile("import foo.bar", "test", "exec")
        ns = {'__builtins__': types.MappingProxyType({})}
        self.assertRaisesRegex(ImportError, "__import__ not found", exec, code, ns)
        ns = {'__builtins__': types.MappingProxyType({'__import__': lambda *args: args})}
        exec(code, ns)
        self.assertEqual(ns['foo'], ('foo.bar', ns, ns, None, 0))

    # CPython Objects/funcobject.c function builtin capture / frame lifetime.
    def test_captured_builtin_namespace(self):
        original = {'value': 1}
        ns = {'__builtins__': original}
        exec('def f(): return value\ndef g():\n yield value\n yield value', ns)
        ns['__builtins__'] = {'value': 2}
        self.assertEqual(ns['f'](), 1)
        self.assertIs(ns['f'].__builtins__, original)
        with self.assertRaises(AttributeError):
            ns['f'].__builtins__ = {}
        gen = ns['g']()
        self.assertEqual(next(gen), 1)
        original['value'] = 3
        self.assertEqual(next(gen), 3)
        self.assertEqual(ns['f'](), 3)
        exec('def h(): return value', ns)
        self.assertEqual(ns['h'](), 2)

    def test_module_builtin_namespace(self):
        import builtins
        self.assertEqual(eval('len([1, 2])', {'__builtins__': builtins}), 2)
        ns = {'__builtins__': builtins}
        exec('def f(): return len([1, 2])', ns)
        self.assertIs(ns['f'].__builtins__, vars(builtins))
        self.assertEqual(ns['f'](), 2)

    def test_import_hook_namespace_and_arguments(self):
        events = []
        def hook(*args):
            events.append(args)
            return {'answer': 42}
        ns = {'__builtins__': {'__import__': hook}}
        exec('import package', ns)
        self.assertEqual(events[0], ('package', ns, ns, None, 0))
        self.assertEqual(ns['package'], {'answer': 42})

    # Python/ceval.c _PyEval_EnsureBuiltins inherits the caller frame's mapping.
    def test_exec_eval_inherit_caller_builtins(self):
        custom = {'value': 42, 'eval': eval, 'exec': exec}
        ns = {'__builtins__': custom}
        exec('def f(): return eval("value", {})\ndef g():\n d = {}\n exec("result = value", d)\n return d', ns)
        self.assertEqual(ns['f'](), 42)
        result = ns['g']()
        self.assertEqual(result['result'], 42)
        self.assertIs(result['__builtins__'], custom)

    def test_exec_globals_frozen(self):
        class frozendict_error(Exception):
            pass

        class frozendict(dict):
            def __setitem__(self, key, value):
                raise frozendict_error("frozendict is readonly")

        # read-only builtins
        if isinstance(__builtins__, types.ModuleType):
            frozen_builtins = frozendict(__builtins__.__dict__)
        else:
            frozen_builtins = frozendict(__builtins__)
        code = compile("__builtins__['superglobal']=2; print(superglobal)", "test", "exec")
        self.assertRaises(frozendict_error,
                          exec, code, {'__builtins__': frozen_builtins})

        # no __build_class__ function
        code = compile("class A: pass", "", "exec")
        self.assertRaisesRegex(NameError, "__build_class__ not found",
                               exec, code, {'__builtins__': {}})
        # __build_class__ in a custom __builtins__
        exec(code, {'__builtins__': frozen_builtins})
        self.assertRaisesRegex(NameError, "__build_class__ not found",
                               exec, code, {'__builtins__': frozendict()})

        # read-only globals
        namespace = frozendict({})
        code = compile("x=1", "test", "exec")
        self.assertRaises(frozendict_error,
                          exec, code, namespace)


    # CPython codegen_class / builtin___build_class__ ordering and hook dispatch.
    def test_class_builder_hook(self):
        import builtins
        events = []
        def hook(body, name, *bases, **kwargs):
            events.append((body.__name__, name, bases, kwargs))
            with self.assertRaises(TypeError):
                body(1)
            return builtins.__build_class__(body, name, *bases, **kwargs)
        custom = dict(vars(builtins))
        custom['__build_class__'] = hook
        ns = {'__builtins__': custom, '__name__': 'example'}
        exec('class C(object):\n value = 42\n def method(self): return __class__', ns)
        self.assertEqual(events, [('C', 'C', (object,), {})])
        self.assertEqual(ns['C'].value, 42)
        self.assertEqual(ns['C'].__module__, 'example')
        self.assertIs(ns['C']().method(), ns['C'])

    def test_class_builder_lookup_before_bases(self):
        events = []
        ns = {'__builtins__': {}, 'base': lambda: events.append('base')}
        with self.assertRaisesRegex(NameError, '__build_class__ not found'):
            exec('class C(base()): pass', ns)
        self.assertEqual(events, [])

    def test_class_builder_argument_validation(self):
        import builtins
        build = builtins.__build_class__
        self.assertRaises(TypeError, build)
        self.assertRaises(TypeError, build, None, 'C')
        self.assertRaises(TypeError, build, lambda: None, 1)
        self.assertRaises(TypeError, build, len, 'C')
        cls = build(lambda: None, 'C')
        self.assertEqual(cls.__name__, 'C')

    # codegen_class returns the cell without reading __prepare__'s mapping.
    def test_class_cell_return_ignores_namespace_lookup(self):
        class Namespace(dict):
            def __getitem__(self, key):
                if key == '__classcell__':
                    raise ValueError('unexpected class cell lookup')
                return dict.__getitem__(self, key)
        class Meta(type):
            @classmethod
            def __prepare__(cls, name, bases):
                return Namespace()
        class C(metaclass=Meta):
            def method(self):
                return __class__
        self.assertIs(C().method(), C)

    def test_direct_class_body_uses_globals(self):
        import builtins
        seen = []
        def hook(body, name):
            body()
            return object
        custom = dict(vars(builtins))
        custom['__build_class__'] = hook
        ns = {'__builtins__': custom, 'seen': seen}
        exec('class C:\n seen.append(locals() is globals())\n x = 42', ns)
        self.assertEqual(seen, [True])
        self.assertEqual(ns['x'], 42)
        self.assertIs(ns['C'], object)

    def test_live_native_module_builtins(self):
        import sys
        ns = {'__builtins__': sys}
        try:
            sys.compiler_builtin_probe = 1
            exec('def f(): return compiler_builtin_probe', ns)
            self.assertIs(ns['f'].__builtins__, sys.__dict__)
            sys.compiler_builtin_probe = 2
            self.assertEqual(ns['f'](), 2)
            sys.__dict__['compiler_builtin_probe'] = 3
            self.assertEqual(sys.compiler_builtin_probe, 3)
            self.assertEqual(ns['f'](), 3)
            del sys.compiler_builtin_probe
            self.assertRaises(NameError, ns['f'])
        finally:
            sys.__dict__.pop('compiler_builtin_probe', None)

    def test_globals_dict_subclass(self):
        # gh-132386
        class WeirdDict(dict):
            pass

        ns = {}
        exec('def foo(): return a', WeirdDict(), ns)

        self.assertRaises(NameError, ns['foo'])

    # _PyEval_LoadGlobalStackRef's subclass path differs from LOAD_NAME.
    def test_globals_subclass_function_lookup_hooks(self):
        calls = []
        class Namespace(dict):
            def __getitem__(self, key):
                calls.append(key)
                if key == 'value':
                    return 42
                if key == 'error':
                    raise ValueError('lookup failure')
                return dict.__getitem__(self, key)
        namespace = Namespace(value=1)
        locals_map = {}
        exec('result = value\ndef f(): return value\ndef g(): return len([])\ndef h(): return error', namespace, locals_map)
        self.assertEqual(locals_map['result'], 1)
        self.assertEqual(calls, [])
        self.assertEqual(locals_map['f'](), 42)
        self.assertEqual(locals_map['g'](), 0)
        self.assertEqual(calls, ['value', 'len'])
        with self.assertRaisesRegex(ValueError, 'lookup failure'):
            locals_map['h']()

    def test_compile_filename(self):
        for filename in 'file.py', b'file.py':
            code = compile('pass', filename, 'exec')
            self.assertEqual(code.co_filename, 'file.py')
        # Buffer filename rejection awaits bytearray/memoryview fixtures.
        self.assertRaises(TypeError, compile, 'pass', list(b'file.py'), 'exec')

    def test_compile_filename_refleak(self):
        # Regression tests for reference leak in PyUnicode_FSDecoder.
        # See https://github.com/python/cpython/issues/139748.
        mortal_str = 'this is a mortal string'
        # check error path when 'mode' AC conversion failed
        self.assertRaises(TypeError, compile, b'', mortal_str, mode=1234)
        # check error path when 'optimize' AC conversion failed
        self.assertRaises(OverflowError, compile, b'', mortal_str,
                          'exec', optimize=1 << 1000)
        # check error path when 'dont_inherit' AC conversion failed
        class EvilBool:
            def __bool__(self): raise ValueError
        self.assertRaises(ValueError, compile, b'', mortal_str,
                          'exec', dont_inherit=EvilBool())

    def test_path_like_objects(self):
        # An implicit test for PyUnicode_FSDecoder().
        compile("42", FakePath("test_compile_pathlike"), "single")

    def test_filename_string_identity(self):
        class Filename(str):
            pass
        filename = Filename('example.py')
        for path in [filename, FakePath(filename)]:
            code = compile('pass', path, 'exec')
            self.assertIs(code.co_filename, filename)
            self.assertIs(type(code.co_filename), Filename)

    # CPython-checked filesystem conversion and generated-code regression.
    def test_filename_protocol_and_literal_quoting(self):
        for filename in ['quo\'te"\n\\file.py', b'caf\xc3\xa9.py', b'bad\xff.py',
                         b'bad\xed\xa0\x80.py', b'\xef\xbb\xbf.py', b'\xf0\x9f\x90\x8d.py']:
            code = compile('def f(): return 42\ndef g(): yield f()\nclass C: value = f()\nresult = [x for x in g()]', filename, 'exec')
            namespace = {}
            exec(code, namespace)
            self.assertEqual(namespace['result'], [42])
            self.assertEqual(namespace['C'].value, 42)
        self.assertEqual(compile('pass', b'caf\xc3\xa9.py', 'exec').co_filename, 'café.py')
        self.assertEqual(compile('pass', b'bad\xff.py', 'exec').co_filename, 'bad\udcff.py')
        self.assertEqual(compile('pass', b'bad\xed\xa0\x80.py', 'exec').co_filename, 'bad\udced\udca0\udc80.py')
        self.assertEqual(compile('pass', b'\xef\xbb\xbf.py', 'exec').co_filename, '\ufeff.py')
        self.assertEqual(compile('pass', FakePath(b'file.py'), 'exec').co_filename, 'file.py')
        for value in ['a\x00.py', b'a\x00.py']:
            self.assertRaises(ValueError, compile, 'pass', value, 'exec')
        self.assertRaises(TypeError, compile, 'pass', FakePath(123), 'exec')
        self.assertRaises(ValueError, compile, 'pass', FakePath(ValueError), 'exec')
        class InstanceOnly:
            pass
        path = InstanceOnly()
        path.__fspath__ = lambda: 'file.py'
        self.assertRaises(TypeError, compile, 'pass', path, 'exec')
        code = compile('def f(): raise ValueError("expected")\nf()', 'quo\'te"\nfile.py', 'exec')
        self.assertRaisesRegex(ValueError, 'expected', exec, code, {})

if __name__ == "__main__":
    unittest.main()
