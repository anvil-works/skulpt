import contextvars
import decimal
import unittest


class TestContextVars(unittest.TestCase):
    def test_contextvar_basic(self):
        c = contextvars.ContextVar("c")
        self.assertEqual(c.name, "c")
        self.assertRaises(LookupError, c.get)
        self.assertIsNone(c.get(None))
        self.assertEqual(c.get("fallback"), "fallback")

        t1 = c.set(1)
        self.assertIs(t1.var, c)
        self.assertIs(t1.old_value, contextvars.Token.MISSING)
        self.assertEqual(c.get(), 1)
        self.assertEqual(c.get("fallback"), 1)

        t2 = c.set(2)
        self.assertEqual(t2.old_value, 1)
        self.assertEqual(c.get(), 2)

        c.reset(t2)
        self.assertEqual(c.get(), 1)
        c.reset(t1)
        self.assertRaises(LookupError, c.get)

    def test_contextvar_default(self):
        c = contextvars.ContextVar("d", default=42)
        self.assertEqual(c.get(), 42)
        self.assertEqual(c.get(99), 99)

        t = c.set(None)
        self.assertIsNone(c.get())
        self.assertIs(t.old_value, contextvars.Token.MISSING)
        c.reset(t)
        self.assertEqual(c.get(), 42)

    def test_contextvar_constructor_validation(self):
        self.assertRaises(TypeError, contextvars.ContextVar)
        self.assertRaises(TypeError, contextvars.ContextVar, 123)
        self.assertRaises(TypeError, contextvars.ContextVar, "x", 1)
        self.assertRaises(TypeError, contextvars.ContextVar, "x", unknown=1)
        self.assertRaises(TypeError, contextvars.Token)
        self.assertRaises(TypeError, contextvars.Context, 1)

    def test_token_errors(self):
        c1 = contextvars.ContextVar("c1")
        c2 = contextvars.ContextVar("c2")
        ctx1 = contextvars.Context()
        ctx2 = contextvars.Context()

        t = ctx1.run(c1.set, "v")
        self.assertRaises(TypeError, c1.reset, "not-a-token")
        self.assertRaises(ValueError, c2.reset, t)
        self.assertRaises(ValueError, ctx2.run, c1.reset, t)

        ctx1.run(c1.reset, t)
        self.assertRaises(RuntimeError, ctx1.run, c1.reset, t)
        # Reused token raises RuntimeError even on another var or context (CPython precedence)
        self.assertRaises(RuntimeError, c2.reset, t)
        self.assertRaises(RuntimeError, ctx2.run, c1.reset, t)

    def test_cpython_edge_cases(self):
        c = contextvars.ContextVar("edge")
        # ContextVar.get([default]) is positional-only
        self.assertRaises(TypeError, c.get, default=1)

        # Context is unhashable
        ctx = contextvars.Context()
        self.assertRaises(TypeError, hash, ctx)

        # NaN and self-referential contexts use identity short-circuiting for equality
        ctx.run(c.set, float("nan"))
        self.assertEqual(ctx, ctx)
        self.assertEqual(ctx, ctx.copy())
        self.assertFalse(ctx != ctx)

        self_ctx = contextvars.Context()
        self_ctx.run(c.set, self_ctx)
        self.assertEqual(self_ctx, self_ctx)

        # contextvars types cannot be subclassed
        for base in (contextvars.ContextVar, contextvars.Context, contextvars.Token, type(contextvars.Token.MISSING)):
            with self.assertRaises(TypeError):
                type("Sub", (base,), {})

    def test_context_run_and_copy(self):
        c = contextvars.ContextVar("c", default="default")

        def set_and_read(val, *, suffix=""):
            c.set(val + suffix)
            return c.get()

        ctx = contextvars.Context()
        self.assertEqual(ctx.run(set_and_read, "a", suffix="!"), "a!")
        self.assertEqual(c.get(), "default")
        self.assertEqual(ctx[c], "a!")

        ctx_copy = ctx.copy()
        self.assertEqual(ctx, ctx_copy)
        ctx_copy.run(c.set, "b")
        self.assertEqual(ctx[c], "a!")
        self.assertEqual(ctx_copy[c], "b")
        self.assertNotEqual(ctx, ctx_copy)

        # Re-entering an already entered context raises RuntimeError
        self.assertRaises(RuntimeError, ctx.run, lambda: ctx.run(lambda: None))

    def test_copy_context_isolation(self):
        c = contextvars.ContextVar("iso", default=0)
        t = c.set(10)
        try:
            snap = contextvars.copy_context()
            self.assertEqual(snap[c], 10)
            self.assertEqual(snap.run(lambda: (c.set(20), c.get())[1]), 20)
            self.assertEqual(c.get(), 10)
            self.assertEqual(snap[c], 20)
        finally:
            c.reset(t)

    def test_context_mapping_interface(self):
        c1 = contextvars.ContextVar("m1")
        c2 = contextvars.ContextVar("m2")
        ctx = contextvars.Context()
        self.assertEqual(len(ctx), 0)
        self.assertNotIn(c1, ctx)
        self.assertIsNone(ctx.get(c1))
        self.assertEqual(ctx.get(c1, "missing"), "missing")
        self.assertRaises(KeyError, lambda: ctx[c1])
        self.assertRaises(TypeError, lambda: "not_a_var" in ctx)
        self.assertRaises(TypeError, lambda: ctx["not_a_var"])
        self.assertRaises(TypeError, ctx.get, "not_a_var")

        ctx.run(c1.set, 1)
        ctx.run(c2.set, 2)
        self.assertEqual(len(ctx), 2)
        self.assertIn(c1, ctx)
        self.assertEqual(ctx[c1], 1)
        self.assertEqual(ctx.get(c2), 2)
        self.assertEqual(set(ctx), {c1, c2})
        self.assertEqual(set(ctx.keys()), {c1, c2})
        self.assertEqual(set(ctx.values()), {1, 2})
        self.assertEqual(dict(ctx.items()), {c1: 1, c2: 2})
        self.assertFalse(ctx == {c1: 1, c2: 2})

    def test_generic_alias(self):
        self.assertEqual(contextvars.ContextVar[int].__origin__, contextvars.ContextVar)
        self.assertEqual(contextvars.Token[str].__origin__, contextvars.Token)

    def test_decimal_uses_contextvar(self):
        self.assertTrue(decimal.HAVE_CONTEXTVAR)
        ctx = contextvars.Context()

        def run_with_prec():
            with decimal.localcontext() as dctx:
                dctx.prec = 4
                return str(decimal.Decimal(1) / decimal.Decimal(3))

        self.assertEqual(ctx.run(run_with_prec), "0.3333")
        # Outer decimal context is unaffected
        self.assertEqual(decimal.getcontext().prec, 28)

        # setcontext inside a separate Context does not affect outer context
        ctx.run(lambda: decimal.setcontext(decimal.Context(prec=6)))
        self.assertEqual(ctx.run(lambda: decimal.getcontext().prec), 6)
        self.assertEqual(decimal.getcontext().prec, 28)

        # Internal JS-only decimal ContextVar stays hidden from Python Context mapping views
        self.assertEqual(len(ctx), 0)
        self.assertEqual(list(ctx), [])


if __name__ == "__main__":
    unittest.main()
