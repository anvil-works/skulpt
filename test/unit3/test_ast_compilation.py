# CPython 3.14 Lib/test/test_ast/test_ast.py at 18ef0f0cb52.
# ASTValidatorTests methods and their production compile harness are unchanged.
# Pattern cases follow with match; whole-stdlib validation follows stdlib support.
import ast
import unittest
from test_type_parameters import SubTest

class ASTValidation(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def mod(self, mod, msg=None, mode="exec", *, exc=ValueError):
        mod.lineno = mod.col_offset = 0
        ast.fix_missing_locations(mod)
        if msg is None:
            compile(mod, "<test>", mode)
        else:
            with self.assertRaises(exc) as cm:
                compile(mod, "<test>", mode)
            self.assertIn(msg, str(cm.exception))

    def expr(self, node, msg=None, *, exc=ValueError):
        mod = ast.Module([ast.Expr(node)], [])
        self.mod(mod, msg, exc=exc)

    def stmt(self, stmt, msg=None):
        mod = ast.Module([stmt], [])
        self.mod(mod, msg)

    def test_module(self):
        m = ast.Interactive([ast.Expr(ast.Name("x", ast.Store()))])
        self.mod(m, "must have Load context", "single")
        m = ast.Expression(ast.Name("x", ast.Store()))
        self.mod(m, "must have Load context", "eval")

    def _check_arguments(self, fac, check):
        def arguments(args=None, posonlyargs=None, vararg=None,
                      kwonlyargs=None, kwarg=None,
                      defaults=None, kw_defaults=None):
            if args is None:
                args = []
            if posonlyargs is None:
                posonlyargs = []
            if kwonlyargs is None:
                kwonlyargs = []
            if defaults is None:
                defaults = []
            if kw_defaults is None:
                kw_defaults = []
            args = ast.arguments(args, posonlyargs, vararg, kwonlyargs,
                                 kw_defaults, kwarg, defaults)
            return fac(args)
        args = [ast.arg("x", ast.Name("x", ast.Store()))]
        check(arguments(args=args), "must have Load context")
        check(arguments(posonlyargs=args), "must have Load context")
        check(arguments(kwonlyargs=args), "must have Load context")
        check(arguments(defaults=[ast.Constant(3)]),
                       "more positional defaults than args")
        check(arguments(kw_defaults=[ast.Constant(4)]),
                       "length of kwonlyargs is not the same as kw_defaults")
        args = [ast.arg("x", ast.Name("x", ast.Load()))]
        check(arguments(args=args, defaults=[ast.Name("x", ast.Store())]),
                       "must have Load context")
        args = [ast.arg("a", ast.Name("x", ast.Load())),
                ast.arg("b", ast.Name("y", ast.Load()))]
        check(arguments(kwonlyargs=args,
                          kw_defaults=[None, ast.Name("x", ast.Store())]),
                          "must have Load context")

    def test_funcdef(self):
        a = ast.arguments([], [], None, [], [], None, [])
        f = ast.FunctionDef("x", a, [], [], None, None, [])
        self.stmt(f, "empty body on FunctionDef")
        f = ast.FunctionDef("x", a, [ast.Pass()], [ast.Name("x", ast.Store())], None, None, [])
        self.stmt(f, "must have Load context")
        f = ast.FunctionDef("x", a, [ast.Pass()], [],
                            ast.Name("x", ast.Store()), None, [])
        self.stmt(f, "must have Load context")
        f = ast.FunctionDef("x", ast.arguments(), [ast.Pass()])
        self.stmt(f)
        def fac(args):
            return ast.FunctionDef("x", args, [ast.Pass()], [], None, None, [])
        self._check_arguments(fac, self.stmt)

    def test_classdef(self):
        def cls(bases=None, keywords=None, body=None, decorator_list=None, type_params=None):
            if bases is None:
                bases = []
            if keywords is None:
                keywords = []
            if body is None:
                body = [ast.Pass()]
            if decorator_list is None:
                decorator_list = []
            if type_params is None:
                type_params = []
            return ast.ClassDef("myclass", bases, keywords,
                                body, decorator_list, type_params)
        self.stmt(cls(bases=[ast.Name("x", ast.Store())]),
                  "must have Load context")
        self.stmt(cls(keywords=[ast.keyword("x", ast.Name("x", ast.Store()))]),
                  "must have Load context")
        self.stmt(cls(body=[]), "empty body on ClassDef")
        self.stmt(cls(body=[None]), "None disallowed")
        self.stmt(cls(decorator_list=[ast.Name("x", ast.Store())]),
                  "must have Load context")

    def test_delete(self):
        self.stmt(ast.Delete([]), "empty targets on Delete")
        self.stmt(ast.Delete([None]), "None disallowed")
        self.stmt(ast.Delete([ast.Name("x", ast.Load())]),
                  "must have Del context")

    def test_assign(self):
        self.stmt(ast.Assign([], ast.Constant(3)), "empty targets on Assign")
        self.stmt(ast.Assign([None], ast.Constant(3)), "None disallowed")
        self.stmt(ast.Assign([ast.Name("x", ast.Load())], ast.Constant(3)),
                  "must have Store context")
        self.stmt(ast.Assign([ast.Name("x", ast.Store())],
                                ast.Name("y", ast.Store())),
                  "must have Load context")

    def test_augassign(self):
        aug = ast.AugAssign(ast.Name("x", ast.Load()), ast.Add(),
                            ast.Name("y", ast.Load()))
        self.stmt(aug, "must have Store context")
        aug = ast.AugAssign(ast.Name("x", ast.Store()), ast.Add(),
                            ast.Name("y", ast.Store()))
        self.stmt(aug, "must have Load context")

    def test_for(self):
        x = ast.Name("x", ast.Store())
        y = ast.Name("y", ast.Load())
        p = ast.Pass()
        self.stmt(ast.For(x, y, [], []), "empty body on For")
        self.stmt(ast.For(ast.Name("x", ast.Load()), y, [p], []),
                  "must have Store context")
        self.stmt(ast.For(x, ast.Name("y", ast.Store()), [p], []),
                  "must have Load context")
        e = ast.Expr(ast.Name("x", ast.Store()))
        self.stmt(ast.For(x, y, [e], []), "must have Load context")
        self.stmt(ast.For(x, y, [p], [e]), "must have Load context")

    def test_while(self):
        self.stmt(ast.While(ast.Constant(3), [], []), "empty body on While")
        self.stmt(ast.While(ast.Name("x", ast.Store()), [ast.Pass()], []),
                  "must have Load context")
        self.stmt(ast.While(ast.Constant(3), [ast.Pass()],
                             [ast.Expr(ast.Name("x", ast.Store()))]),
                             "must have Load context")

    def test_if(self):
        self.stmt(ast.If(ast.Constant(3), [], []), "empty body on If")
        i = ast.If(ast.Name("x", ast.Store()), [ast.Pass()], [])
        self.stmt(i, "must have Load context")
        i = ast.If(ast.Constant(3), [ast.Expr(ast.Name("x", ast.Store()))], [])
        self.stmt(i, "must have Load context")
        i = ast.If(ast.Constant(3), [ast.Pass()],
                   [ast.Expr(ast.Name("x", ast.Store()))])
        self.stmt(i, "must have Load context")

    def test_with(self):
        p = ast.Pass()
        self.stmt(ast.With([], [p]), "empty items on With")
        i = ast.withitem(ast.Constant(3), None)
        self.stmt(ast.With([i], []), "empty body on With")
        i = ast.withitem(ast.Name("x", ast.Store()), None)
        self.stmt(ast.With([i], [p]), "must have Load context")
        i = ast.withitem(ast.Constant(3), ast.Name("x", ast.Load()))
        self.stmt(ast.With([i], [p]), "must have Store context")

    def test_raise(self):
        r = ast.Raise(None, ast.Constant(3))
        self.stmt(r, "Raise with cause but no exception")
        r = ast.Raise(ast.Name("x", ast.Store()), None)
        self.stmt(r, "must have Load context")
        r = ast.Raise(ast.Constant(4), ast.Name("x", ast.Store()))
        self.stmt(r, "must have Load context")

    def test_try(self):
        p = ast.Pass()
        t = ast.Try([], [], [], [p])
        self.stmt(t, "empty body on Try")
        t = ast.Try([ast.Expr(ast.Name("x", ast.Store()))], [], [], [p])
        self.stmt(t, "must have Load context")
        t = ast.Try([p], [], [], [])
        self.stmt(t, "Try has neither except handlers nor finalbody")
        t = ast.Try([p], [], [p], [p])
        self.stmt(t, "Try has orelse but no except handlers")
        t = ast.Try([p], [ast.ExceptHandler(None, "x", [])], [], [])
        self.stmt(t, "empty body on ExceptHandler")
        e = [ast.ExceptHandler(ast.Name("x", ast.Store()), "y", [p])]
        self.stmt(ast.Try([p], e, [], []), "must have Load context")
        e = [ast.ExceptHandler(None, "x", [p])]
        t = ast.Try([p], e, [ast.Expr(ast.Name("x", ast.Store()))], [p])
        self.stmt(t, "must have Load context")
        t = ast.Try([p], e, [p], [ast.Expr(ast.Name("x", ast.Store()))])
        self.stmt(t, "must have Load context")

    def test_try_star(self):
        p = ast.Pass()
        t = ast.TryStar([], [], [], [p])
        self.stmt(t, "empty body on TryStar")
        t = ast.TryStar([ast.Expr(ast.Name("x", ast.Store()))], [], [], [p])
        self.stmt(t, "must have Load context")
        t = ast.TryStar([p], [], [], [])
        self.stmt(t, "TryStar has neither except handlers nor finalbody")
        t = ast.TryStar([p], [], [p], [p])
        self.stmt(t, "TryStar has orelse but no except handlers")
        t = ast.TryStar([p], [ast.ExceptHandler(None, "x", [])], [], [])
        self.stmt(t, "empty body on ExceptHandler")
        e = [ast.ExceptHandler(ast.Name("x", ast.Store()), "y", [p])]
        self.stmt(ast.TryStar([p], e, [], []), "must have Load context")
        e = [ast.ExceptHandler(None, "x", [p])]
        t = ast.TryStar([p], e, [ast.Expr(ast.Name("x", ast.Store()))], [p])
        self.stmt(t, "must have Load context")
        t = ast.TryStar([p], e, [p], [ast.Expr(ast.Name("x", ast.Store()))])
        self.stmt(t, "must have Load context")

    def test_assert(self):
        self.stmt(ast.Assert(ast.Name("x", ast.Store()), None),
                  "must have Load context")
        assrt = ast.Assert(ast.Name("x", ast.Load()),
                           ast.Name("y", ast.Store()))
        self.stmt(assrt, "must have Load context")

    def test_import(self):
        self.stmt(ast.Import([]), "empty names on Import")

    def test_importfrom(self):
        imp = ast.ImportFrom(None, [ast.alias("x", None)], -42)
        self.stmt(imp, "Negative ImportFrom level")
        self.stmt(ast.ImportFrom(None, [], 0), "empty names on ImportFrom")

    def test_global(self):
        self.stmt(ast.Global([]), "empty names on Global")

    def test_nonlocal(self):
        self.stmt(ast.Nonlocal([]), "empty names on Nonlocal")

    def test_expr(self):
        e = ast.Expr(ast.Name("x", ast.Store()))
        self.stmt(e, "must have Load context")

    def test_boolop(self):
        b = ast.BoolOp(ast.And(), [])
        self.expr(b, "less than 2 values")
        b = ast.BoolOp(ast.And(), [ast.Constant(3)])
        self.expr(b, "less than 2 values")
        b = ast.BoolOp(ast.And(), [ast.Constant(4), None])
        self.expr(b, "None disallowed")
        b = ast.BoolOp(ast.And(), [ast.Constant(4), ast.Name("x", ast.Store())])
        self.expr(b, "must have Load context")

    def test_unaryop(self):
        u = ast.UnaryOp(ast.Not(), ast.Name("x", ast.Store()))
        self.expr(u, "must have Load context")

    def test_lambda(self):
        a = ast.arguments([], [], None, [], [], None, [])
        self.expr(ast.Lambda(a, ast.Name("x", ast.Store())),
                  "must have Load context")
        def fac(args):
            return ast.Lambda(args, ast.Name("x", ast.Load()))
        self._check_arguments(fac, self.expr)

    def test_ifexp(self):
        l = ast.Name("x", ast.Load())
        s = ast.Name("y", ast.Store())
        for args in (s, l, l), (l, s, l), (l, l, s):
            self.expr(ast.IfExp(*args), "must have Load context")

    def test_dict(self):
        d = ast.Dict([], [ast.Name("x", ast.Load())])
        self.expr(d, "same number of keys as values")
        d = ast.Dict([ast.Name("x", ast.Load())], [None])
        self.expr(d, "None disallowed")

    def test_set(self):
        self.expr(ast.Set([None]), "None disallowed")
        s = ast.Set([ast.Name("x", ast.Store())])
        self.expr(s, "must have Load context")

    def _check_comprehension(self, fac):
        self.expr(fac([]), "comprehension with no generators")
        g = ast.comprehension(ast.Name("x", ast.Load()),
                              ast.Name("x", ast.Load()), [], 0)
        self.expr(fac([g]), "must have Store context")
        g = ast.comprehension(ast.Name("x", ast.Store()),
                              ast.Name("x", ast.Store()), [], 0)
        self.expr(fac([g]), "must have Load context")
        x = ast.Name("x", ast.Store())
        y = ast.Name("y", ast.Load())
        g = ast.comprehension(x, y, [None], 0)
        self.expr(fac([g]), "None disallowed")
        g = ast.comprehension(x, y, [ast.Name("x", ast.Store())], 0)
        self.expr(fac([g]), "must have Load context")

    def _simple_comp(self, fac):
        g = ast.comprehension(ast.Name("x", ast.Store()),
                              ast.Name("x", ast.Load()), [], 0)
        self.expr(fac(ast.Name("x", ast.Store()), [g]),
                  "must have Load context")
        def wrap(gens):
            return fac(ast.Name("x", ast.Store()), gens)
        self._check_comprehension(wrap)

    def test_listcomp(self):
        self._simple_comp(ast.ListComp)

    def test_setcomp(self):
        self._simple_comp(ast.SetComp)

    def test_generatorexp(self):
        self._simple_comp(ast.GeneratorExp)

    def test_dictcomp(self):
        g = ast.comprehension(ast.Name("y", ast.Store()),
                              ast.Name("p", ast.Load()), [], 0)
        c = ast.DictComp(ast.Name("x", ast.Store()),
                         ast.Name("y", ast.Load()), [g])
        self.expr(c, "must have Load context")
        c = ast.DictComp(ast.Name("x", ast.Load()),
                         ast.Name("y", ast.Store()), [g])
        self.expr(c, "must have Load context")
        def factory(comps):
            k = ast.Name("x", ast.Load())
            v = ast.Name("y", ast.Load())
            return ast.DictComp(k, v, comps)
        self._check_comprehension(factory)

    def test_yield(self):
        self.expr(ast.Yield(ast.Name("x", ast.Store())), "must have Load")
        self.expr(ast.YieldFrom(ast.Name("x", ast.Store())), "must have Load")

    def test_compare(self):
        left = ast.Name("x", ast.Load())
        comp = ast.Compare(left, [ast.In()], [])
        self.expr(comp, "no comparators")
        comp = ast.Compare(left, [ast.In()], [ast.Constant(4), ast.Constant(5)])
        self.expr(comp, "different number of comparators and operands")
        comp = ast.Compare(ast.Constant("blah"), [ast.In()], [left])
        self.expr(comp)
        comp = ast.Compare(left, [ast.In()], [ast.Constant("blah")])
        self.expr(comp)

    def test_call(self):
        func = ast.Name("x", ast.Load())
        args = [ast.Name("y", ast.Load())]
        keywords = [ast.keyword("w", ast.Name("z", ast.Load()))]
        call = ast.Call(ast.Name("x", ast.Store()), args, keywords)
        self.expr(call, "must have Load context")
        call = ast.Call(func, [None], keywords)
        self.expr(call, "None disallowed")
        bad_keywords = [ast.keyword("w", ast.Name("z", ast.Store()))]
        call = ast.Call(func, args, bad_keywords)
        self.expr(call, "must have Load context")

    def test_attribute(self):
        attr = ast.Attribute(ast.Name("x", ast.Store()), "y", ast.Load())
        self.expr(attr, "must have Load context")

    def test_subscript(self):
        sub = ast.Subscript(ast.Name("x", ast.Store()), ast.Constant(3),
                            ast.Load())
        self.expr(sub, "must have Load context")
        x = ast.Name("x", ast.Load())
        sub = ast.Subscript(x, ast.Name("y", ast.Store()),
                            ast.Load())
        self.expr(sub, "must have Load context")
        s = ast.Name("x", ast.Store())
        for args in (s, None, None), (None, s, None), (None, None, s):
            sl = ast.Slice(*args)
            self.expr(ast.Subscript(x, sl, ast.Load()),
                      "must have Load context")
        sl = ast.Tuple([], ast.Load())
        self.expr(ast.Subscript(x, sl, ast.Load()))
        sl = ast.Tuple([s], ast.Load())
        self.expr(ast.Subscript(x, sl, ast.Load()), "must have Load context")

    def test_starred(self):
        left = ast.List([ast.Starred(ast.Name("x", ast.Load()), ast.Store())],
                        ast.Store())
        assign = ast.Assign([left], ast.Constant(4))
        self.stmt(assign, "must have Store context")

    def _sequence(self, fac):
        self.expr(fac([None], ast.Load()), "None disallowed")
        self.expr(fac([ast.Name("x", ast.Store())], ast.Load()),
                  "must have Load context")

    def test_list(self):
        self._sequence(ast.List)

    def test_tuple(self):
        self._sequence(ast.Tuple)

class ASTCompilation(unittest.TestCase):
    def test_edited_generic_function_and_immutable_constants(self):
        tree = ast.parse('def f[T](x: T): return x + 1')
        tree.body[0].body[0].value.right.value = 3
        ns = {}
        exec(compile(tree, '<edited>', 'exec'), ns)
        self.assertEqual(ns['f'](4), 7)
        self.assertIs(ns['f'].__annotations__['x'], ns['f'].__type_params__[0])
        value = (123456789123456789123456789, frozenset({1, 2}), b'hi', 2j)
        tree = ast.fix_missing_locations(ast.Expression(ast.Constant(value)))
        self.assertEqual(eval(compile(tree, '<constant>', 'eval')), value)
        self.assertEqual(ast.dump(compile(tree, '<constant>', 'eval', ast.PyCF_ONLY_AST)), ast.dump(tree))

if __name__ == '__main__': unittest.main()
