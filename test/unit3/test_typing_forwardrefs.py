# Complete CPython 3.14 test_typing/test_annotationlib methods at 18ef0f0cb52.
import unittest
import typing, types, sys, collections, annotationlib
from annotationlib import ForwardRef
from typing import TypeVarTuple, Unpack, TypeVar, Generic, List, Tuple, Union, Callable, ParamSpec, Any, get_type_hints
from test_annotationlib import HarnessCase, EqualToForwardRef
get_args = typing.get_args
get_origin = typing.get_origin
gth = get_type_hints
T = TypeVar('T')
class A:
    pass


class TypeVarTests(HarnessCase):
    def test_var_substitution(self):
        T = TypeVar('T')
        subst = T.__typing_subst__
        self.assertIs(subst(int), int)
        self.assertEqual(subst(list[int]), list[int])
        self.assertEqual(subst(List[int]), List[int])
        self.assertEqual(subst(List), List)
        self.assertIs(subst(Any), Any)
        self.assertIs(subst(None), type(None))
        self.assertIs(subst(T), T)
        self.assertEqual(subst(int|str), int|str)
        self.assertEqual(subst(Union[int, str]), Union[int, str])



    def test_or(self):
        X = TypeVar('X')
        # use a string because str doesn't implement
        # __or__/__ror__ itself
        self.assertEqual(X | "x", Union[X, "x"])
        self.assertEqual("x" | X, Union["x", X])
        # make sure the order is correct
        self.assertEqual(get_args(X | "x"), (X, EqualToForwardRef("x")))
        self.assertEqual(get_args("x" | X), (EqualToForwardRef("x"), X))



class GetTypeHintsTests(HarnessCase):
    def test_get_type_hints_from_various_objects(self):
        # For invalid objects should fail with TypeError (not AttributeError etc).
        with self.assertRaises(TypeError):
            gth(123)
        with self.assertRaises(TypeError):
            gth('abc')
        with self.assertRaises(TypeError):
            gth(None)


    def test_get_type_hints_classes_no_implicit_optional(self):
        class WithNoneDefault:
            field: int = None  # most type-checkers won't be happy with it

        self.assertEqual(gth(WithNoneDefault), {'field': int})


    def test_get_type_hints_for_builtins(self):
        # Should not fail for built-in classes and functions.
        self.assertEqual(gth(int), {})
        self.assertEqual(gth(type), {})
        self.assertEqual(gth(dir), {})
        self.assertEqual(gth(len), {})
        self.assertEqual(gth(object.__str__), {})
        self.assertEqual(gth(object().__str__), {})
        self.assertEqual(gth(str.join), {})


    def test_previous_behavior(self):
        def testf(x, y): ...
        testf.__annotations__['x'] = 'int'
        self.assertEqual(gth(testf), {'x': int})
        def testg(x: None): ...
        self.assertEqual(gth(testg), {'x': type(None)})


    def test_get_type_hints_for_object_with_annotations(self):
        class A: ...
        class B: ...
        b = B()
        b.__annotations__ = {'x': 'A'}
        self.assertEqual(gth(b, locals()), {'x': A})


    def test_get_type_hints_wrapped_cycle_self(self):
        # gh-146553: __wrapped__ self-reference must raise ValueError,
        # not loop forever.
        def f(x: int) -> str: ...
        f.__wrapped__ = f
        with self.assertRaisesRegex(ValueError, 'wrapper loop'):
            get_type_hints(f)


    def test_get_type_hints_wrapped_cycle_mutual(self):
        # gh-146553: mutual __wrapped__ cycle (a -> b -> a) must raise
        # ValueError, not loop forever.
        def a(): ...
        def b(): ...
        a.__wrapped__ = b
        b.__wrapped__ = a
        with self.assertRaisesRegex(ValueError, 'wrapper loop'):
            get_type_hints(a)


    def test_get_type_hints_classes_str_annotations(self):
        class Foo:
            y = str
            x: 'y'
        # This previously raised an error under PEP 563.
        self.assertEqual(get_type_hints(Foo), {'x': str})


    def test_get_type_hints_bad_module(self):
        # bpo-41515
        class BadModule:
            pass
        BadModule.__module__ = 'bad' # Something not in sys.modules
        self.assertNotIn('bad', sys.modules)
        self.assertEqual(get_type_hints(BadModule), {})


    def test_get_type_hints_annotated_bad_module(self):
        # See https://bugs.python.org/issue44468
        class BadBase:
            foo: tuple
        class BadType(BadBase):
            bar: list
        BadType.__module__ = BadBase.__module__ = 'bad'
        self.assertNotIn('bad', sys.modules)
        self.assertEqual(get_type_hints(BadType), {'foo': tuple, 'bar': list})


    def test_get_type_hints_collections_abc_callable(self):
        # https://github.com/python/cpython/issues/91621
        P = ParamSpec('P')
        def f(x: collections.abc.Callable[[int], int]): ...
        def g(x: collections.abc.Callable[..., int]): ...
        def h(x: collections.abc.Callable[P, int]): ...

        self.assertEqual(get_type_hints(f), {'x': collections.abc.Callable[[int], int]})
        self.assertEqual(get_type_hints(g), {'x': collections.abc.Callable[..., int]})
        self.assertEqual(get_type_hints(h), {'x': collections.abc.Callable[P, int]})


    def test_get_type_hints_format(self):
        class C:
            x: undefined

        with self.assertRaises(NameError):
            get_type_hints(C)

        with self.assertRaises(NameError):
            get_type_hints(C, format=annotationlib.Format.VALUE)

        annos = get_type_hints(C, format=annotationlib.Format.FORWARDREF)
        self.assertIsInstance(annos, dict)
        self.assertEqual(list(annos), ['x'])
        self.assertIsInstance(annos['x'], annotationlib.ForwardRef)
        self.assertEqual(annos['x'].__arg__, 'undefined')

        self.assertEqual(get_type_hints(C, format=annotationlib.Format.STRING),
                         {'x': 'undefined'})
        # Make sure using an int as format also works:
        self.assertEqual(get_type_hints(C, format=4), {'x': 'undefined'})


    def test_get_type_hints_format_function(self):
        def func(x: undefined) -> undefined: ...

        # VALUE
        with self.assertRaises(NameError):
            get_type_hints(func)
        with self.assertRaises(NameError):
            get_type_hints(func, format=annotationlib.Format.VALUE)

        # FORWARDREF
        self.assertEqual(
            get_type_hints(func, format=annotationlib.Format.FORWARDREF),
            {'x': EqualToForwardRef('undefined', owner=func),
             'return': EqualToForwardRef('undefined', owner=func)},
        )

        # STRING
        self.assertEqual(get_type_hints(func, format=annotationlib.Format.STRING),
                         {'x': 'undefined', 'return': 'undefined'})


    def test_callable_with_ellipsis_forward(self):

        def foo(a: 'Callable[..., T]'):
            pass

        self.assertEqual(get_type_hints(foo, globals(), locals()),
                         {'a': Callable[..., T]})


    def test_union_forward_recursion(self):
        ValueList = List['Value']
        Value = Union[str, ValueList]

        class C:
            foo: List[Value]
        class D:
            foo: Union[Value, ValueList]
        class E:
            foo: Union[List[Value], ValueList]
        class F:
            foo: Union[Value, List[Value], ValueList]

        self.assertEqual(get_type_hints(C, globals(), locals()), get_type_hints(C, globals(), locals()))
        self.assertEqual(get_type_hints(C, globals(), locals()),
                         {'foo': List[Union[str, List[Union[str, List['Value']]]]]})
        self.assertEqual(get_type_hints(D, globals(), locals()),
                         {'foo': Union[str, List[Union[str, List['Value']]]]})
        self.assertEqual(get_type_hints(E, globals(), locals()),
                         {'foo': Union[
                             List[Union[str, List[Union[str, List['Value']]]]],
                             List[Union[str, List['Value']]]
                         ]
                          })
        self.assertEqual(get_type_hints(F, globals(), locals()),
                         {'foo': Union[
                             str,
                             List[Union[str, List['Value']]],
                             List[Union[str, List[Union[str, List['Value']]]]]
                         ]
                          })


    def test_tuple_forward(self):

        def foo(a: Tuple['T']):
            pass

        self.assertEqual(get_type_hints(foo, globals(), locals()),
                         {'a': Tuple[T]})

        def foo(a: tuple[ForwardRef('T')]):
            pass

        self.assertEqual(get_type_hints(foo, globals(), locals()),
                         {'a': tuple[T]})


    def test_double_forward(self):
        def foo(a: 'List[\'int\']'):
            pass
        self.assertEqual(get_type_hints(foo, globals(), locals()),
                         {'a': List[int]})


    def test_union_forward(self):

        def foo(a: Union['T']):
            pass

        self.assertEqual(get_type_hints(foo, globals(), locals()),
                         {'a': Union[T]})

        def foo(a: tuple[ForwardRef('T')] | int):
            pass

        self.assertEqual(get_type_hints(foo, globals(), locals()),
                         {'a': tuple[T] | int})


    def test_default_globals(self):
        code = ("class C:\n"
                "    def foo(self, a: 'C') -> 'D': pass\n"
                "class D:\n"
                "    def bar(self, b: 'D') -> C: pass\n"
                )
        ns = {}
        exec(code, ns)
        hints = get_type_hints(ns['C'].foo)
        self.assertEqual(hints, {'a': ns['C'], 'return': ns['D']})


    def test_name_error(self):

        def foo(a: 'Noode[T]'):
            pass

        with self.assertRaises(NameError):
            get_type_hints(foo, locals())




class EvaluateForwardRefTests(HarnessCase):
    def test_evaluate_forward_ref(self):
        int_ref = ForwardRef('int')
        self.assertIs(typing.evaluate_forward_ref(int_ref), int)
        self.assertIs(
            typing.evaluate_forward_ref(int_ref, type_params=()),
            int,
        )
        self.assertIs(
            typing.evaluate_forward_ref(int_ref, format=annotationlib.Format.VALUE),
            int,
        )
        self.assertIs(
            typing.evaluate_forward_ref(
                int_ref, format=annotationlib.Format.FORWARDREF,
            ),
            int,
        )
        self.assertEqual(
            typing.evaluate_forward_ref(
                int_ref, format=annotationlib.Format.STRING,
            ),
            'int',
        )


    def test_evaluate_forward_ref_undefined(self):
        missing = ForwardRef('missing')
        with self.assertRaises(NameError):
            typing.evaluate_forward_ref(missing)
        self.assertIs(
            typing.evaluate_forward_ref(
                missing, format=annotationlib.Format.FORWARDREF,
            ),
            missing,
        )
        self.assertEqual(
            typing.evaluate_forward_ref(
                missing, format=annotationlib.Format.STRING,
            ),
            "missing",
        )


    def test_evaluate_forward_ref_nested(self):
        ref = ForwardRef("int | list['str']")
        self.assertEqual(
            typing.evaluate_forward_ref(ref),
            int | list[str],
        )
        self.assertEqual(
            typing.evaluate_forward_ref(ref, format=annotationlib.Format.FORWARDREF),
            int | list[str],
        )
        self.assertEqual(
            typing.evaluate_forward_ref(ref, format=annotationlib.Format.STRING),
            "int | list['str']",
        )

        why = ForwardRef('"\'str\'"')
        self.assertIs(typing.evaluate_forward_ref(why), str)


    def test_evaluate_forward_ref_none(self):
        none_ref = ForwardRef('None')
        self.assertIs(typing.evaluate_forward_ref(none_ref), None)


    def test_globals(self):
        A = "str"
        ref = ForwardRef('list[A]')
        with self.assertRaises(NameError):
            typing.evaluate_forward_ref(ref)
        self.assertEqual(
            typing.evaluate_forward_ref(ref, globals={'A': A}),
            list[str],
        )


    def test_partial_evaluation(self):
        ref = ForwardRef("list[A]")
        with self.assertRaises(NameError):
            typing.evaluate_forward_ref(ref)

        self.assertEqual(
            typing.evaluate_forward_ref(ref, format=annotationlib.Format.FORWARDREF),
            list[EqualToForwardRef('A')],
        )


    def test_evaluate_forward_ref_string_format(self):
        # Test evaluating forward references in STRING format
        # does not 'leak' internal names
        # See https://github.com/python/cpython/issues/150641

        def f(arg: unknown | str | int | list[str] | tuple[int, ...]): ...

        ref = annotationlib.get_annotations(f, format=annotationlib.Format.FORWARDREF)['arg']
        self.assertEqual(
            typing.evaluate_forward_ref(ref, format=annotationlib.Format.STRING),
            "unknown | str | int | list[str] | tuple[int, ...]",
        )




class TestForwardRefClass(HarnessCase):
    def test_forward_equality(self):
        fr = ForwardRef("int")
        self.assertEqual(fr, ForwardRef("int"))
        self.assertNotEqual(List["int"], List[int])
        self.assertNotEqual(fr, ForwardRef("int", module=__name__))
        frm = ForwardRef("int", module=__name__)
        self.assertEqual(frm, ForwardRef("int", module=__name__))
        self.assertNotEqual(frm, ForwardRef("int", module="__other_name__"))


    def test_forward_equality_get_type_hints(self):
        c1 = ForwardRef("C")
        c1_gth = ForwardRef("C")
        c2 = ForwardRef("C")
        c2_gth = ForwardRef("C")

        class C:
            pass

        def foo(a: c1_gth, b: c2_gth):
            pass

        self.assertEqual(get_type_hints(foo, globals(), locals()), {"a": C, "b": C})
        self.assertEqual(c1, c2)
        self.assertEqual(c1, c1_gth)
        self.assertEqual(c1_gth, c2_gth)
        self.assertEqual(List[c1], List[c1_gth])
        self.assertNotEqual(List[c1], List[C])
        self.assertNotEqual(List[c1_gth], List[C])
        self.assertEqual(Union[c1, c1_gth], Union[c1])
        self.assertEqual(Union[c1, c1_gth, int], Union[c1, int])


    def test_forward_equality_hash(self):
        c1 = ForwardRef("int")
        c1_gth = ForwardRef("int")
        c2 = ForwardRef("int")
        c2_gth = ForwardRef("int")

        def foo(a: c1_gth, b: c2_gth):
            pass

        get_type_hints(foo, globals(), locals())

        self.assertEqual(hash(c1), hash(c2))
        self.assertEqual(hash(c1_gth), hash(c2_gth))
        self.assertEqual(hash(c1), hash(c1_gth))

        c3 = ForwardRef("int", module=__name__)
        c4 = ForwardRef("int", module="__other_name__")

        self.assertNotEqual(hash(c3), hash(c1))
        self.assertNotEqual(hash(c3), hash(c1_gth))
        self.assertNotEqual(hash(c3), hash(c4))
        self.assertEqual(hash(c3), hash(ForwardRef("int", module=__name__)))


    def test_forward_equality_namespace(self):
        def namespace1():
            a = ForwardRef("A")

            def fun(x: a):
                pass

            get_type_hints(fun, globals(), locals())
            return a

        def namespace2():
            a = ForwardRef("A")

            class A:
                pass

            def fun(x: a):
                pass

            get_type_hints(fun, globals(), locals())
            return a

        self.assertEqual(namespace1(), namespace1())
        self.assertEqual(namespace1(), namespace2())


    def test_forward_repr(self):
        self.assertEqual(repr(List["int"]), "typing.List[ForwardRef('int')]")
        self.assertEqual(
            repr(List[ForwardRef("int", module="mod")]),
            "typing.List[ForwardRef('int', module='mod')]",
        )
        self.assertEqual(
            repr(List[ForwardRef("int", module="mod", is_class=True)]),
            "typing.List[ForwardRef('int', module='mod', is_class=True)]",
        )
        self.assertEqual(
            repr(List[ForwardRef("int", owner="class")]),
            "typing.List[ForwardRef('int', owner='class')]",
        )


    def test_forward_recursion_actually(self):
        def namespace1():
            a = ForwardRef("A")
            A = a

            def fun(x: a):
                pass

            ret = get_type_hints(fun, globals(), locals())
            return a

        def namespace2():
            a = ForwardRef("A")
            A = a

            def fun(x: a):
                pass

            ret = get_type_hints(fun, globals(), locals())
            return a

        r1 = namespace1()
        r2 = namespace2()
        self.assertIsNot(r1, r2)
        self.assertEqual(r1, r2)


    def test_syntax_error(self):

        with self.assertRaises(SyntaxError):
            typing.Generic["/T"]


    def test_delayed_syntax_error(self):

        def foo(a: "Node[T"):
            pass

        with self.assertRaises(SyntaxError):
            get_type_hints(foo)


    def test_syntax_error_empty_string(self):
        for form in [typing.List, typing.Set, typing.Type, typing.Deque]:
            with self.subTest(form=form):
                with self.assertRaises(SyntaxError):
                    form[""]


    def test_or(self):
        X = ForwardRef("X")
        # __or__/__ror__ itself
        self.assertEqual(X | "x", Union[X, "x"])
        self.assertEqual("x" | X, Union["x", X])


    def test_multiple_ways_to_create(self):
        X1 = Union["X"]
        self.assertIsInstance(X1, ForwardRef)
        X2 = ForwardRef("X")
        self.assertIsInstance(X2, ForwardRef)
        self.assertEqual(X1, X2)



class NativeTypeVarForwardRefRegression(HarnessCase):
    # Objects/typevarobject.c:typevar_new_impl, checked in pinned CPython.
    def test_string_bound_and_raw_constraints(self):
        var = TypeVar('Bound', bound='int')
        self.assertEqual(var.__bound__, ForwardRef('int'))
        self.assertEqual(TypeVar('Constraints', 'int', 'str').__constraints__, ('int', 'str'))
        with self.assertRaises(SyntaxError):
            TypeVar('InvalidBound', int, bound='/')
        with self.assertRaises(TypeError):
            TypeVar('Invalid', bound=(1, 2))
        self.assertEqual(TypeVar('Subst').__typing_subst__('int'), ForwardRef('int'))



class TypeVarTupleForwardRefTests(HarnessCase):
    def test_get_type_hints_on_unpack_args(self):
        Ts = TypeVarTuple('Ts')

        def func1(*args: *Ts): pass
        self.assertEqual(gth(func1), {'args': Unpack[Ts]})

        def func2(*args: *tuple[int, str]): pass
        self.assertEqual(gth(func2), {'args': Unpack[tuple[int, str]]})

        class CustomVariadic(Generic[*Ts]): pass

        def func3(*args: *CustomVariadic[int, str]): pass
        self.assertEqual(gth(func3), {'args': Unpack[CustomVariadic[int, str]]})


    def test_get_type_hints_on_unpack_args_string(self):
        Ts = TypeVarTuple('Ts')

        def func1(*args: '*Ts'): pass
        self.assertEqual(gth(func1, localns={'Ts': Ts}),
                        {'args': Unpack[Ts]})

        def func2(*args: '*tuple[int, str]'): pass
        self.assertEqual(gth(func2), {'args': Unpack[tuple[int, str]]})

        class CustomVariadic(Generic[*Ts]): pass

        def func3(*args: '*CustomVariadic[int, str]'): pass
        self.assertEqual(gth(func3, localns={'CustomVariadic': CustomVariadic}),
                         {'args': Unpack[CustomVariadic[int, str]]})


class NativeUnpackForwardRefRegression(HarnessCase):
    # Native aliases must participate in CPython typing's GenericAlias paths.
    def test_native_alias_evaluation_and_substitution(self):
        def func(x: Unpack[tuple['X', ...]]): pass
        self.assertEqual(get_type_hints(func, globals(), {'X': int}),
                         {'x': Unpack[tuple[int, ...]]})
        self.assertEqual(Unpack['X'].__args__, (ForwardRef('X'),))
        with self.assertRaises(TypeError):
            TypeVar('T').__typing_subst__(Unpack[tuple[int, ...]])

if __name__ == '__main__': unittest.main()
