# CPython 3.14 Lib/test/test_exception_group.py at 18ef0f0cb52.
import unittest
import collections
import types

class SubTest:
    def __enter__(self): return self
    def __exit__(self, *args): return False
class HarnessCase(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def assertIsSubclass(self, cls, parent): self.assertTrue(issubclass(cls, parent))

class TestExceptionGroupTypeHierarchy(HarnessCase):
    def test_exception_group_types(self):
        self.assertIsSubclass(ExceptionGroup, Exception)
        self.assertIsSubclass(ExceptionGroup, BaseExceptionGroup)
        self.assertIsSubclass(BaseExceptionGroup, BaseException)

    def test_exception_is_not_generic_type(self):
        with self.assertRaisesRegex(TypeError, 'Exception'):
            Exception[OSError]

    def test_exception_group_is_generic_type(self):
        E = OSError
        self.assertIsInstance(ExceptionGroup[E], types.GenericAlias)
        self.assertIsInstance(BaseExceptionGroup[E], types.GenericAlias)


class BadConstructorArgs(HarnessCase):
    def test_bad_EG_construction__too_many_args(self):
        MSG = r'BaseExceptionGroup.__new__\(\) takes exactly 2 arguments'
        with self.assertRaisesRegex(TypeError, MSG):
            ExceptionGroup('no errors')
        with self.assertRaisesRegex(TypeError, MSG):
            ExceptionGroup([ValueError('no msg')])
        with self.assertRaisesRegex(TypeError, MSG):
            ExceptionGroup('eg', [ValueError('too')], [TypeError('many')])

    def test_bad_EG_construction__bad_message(self):
        MSG = 'argument 1 must be str, not '
        with self.assertRaisesRegex(TypeError, MSG):
            ExceptionGroup(ValueError(12), SyntaxError('bad syntax'))
        with self.assertRaisesRegex(TypeError, MSG):
            ExceptionGroup(None, [ValueError(12)])

    def test_bad_EG_construction__bad_excs_sequence(self):
        MSG = r'second argument \(exceptions\) must be a sequence'
        with self.assertRaisesRegex(TypeError, MSG):
            ExceptionGroup('errors not sequence', {ValueError(42)})
        with self.assertRaisesRegex(TypeError, MSG):
            ExceptionGroup("eg", None)

        MSG = r'second argument \(exceptions\) must be a non-empty sequence'
        with self.assertRaisesRegex(ValueError, MSG):
            ExceptionGroup("eg", [])

    def test_bad_EG_construction__nested_non_exceptions(self):
        MSG = (r'Item [0-9]+ of second argument \(exceptions\)'
              ' is not an exception')
        with self.assertRaisesRegex(ValueError, MSG):
            ExceptionGroup('expect instance, not type', [OSError]);
        with self.assertRaisesRegex(ValueError, MSG):
            ExceptionGroup('bad error', ["not an exception"])


class InstanceCreation(HarnessCase):
    def test_EG_wraps_Exceptions__creates_EG(self):
        excs = [ValueError(1), TypeError(2)]
        self.assertIs(
            type(ExceptionGroup("eg", excs)),
            ExceptionGroup)

    def test_BEG_wraps_Exceptions__creates_EG(self):
        excs = [ValueError(1), TypeError(2)]
        self.assertIs(
            type(BaseExceptionGroup("beg", excs)),
            ExceptionGroup)

    def test_EG_wraps_BaseException__raises_TypeError(self):
        MSG= "Cannot nest BaseExceptions in an ExceptionGroup"
        with self.assertRaisesRegex(TypeError, MSG):
            eg = ExceptionGroup("eg", [ValueError(1), KeyboardInterrupt(2)])

    def test_BEG_wraps_BaseException__creates_BEG(self):
        beg = BaseExceptionGroup("beg", [ValueError(1), KeyboardInterrupt(2)])
        self.assertIs(type(beg), BaseExceptionGroup)

    def test_EG_subclass_wraps_non_base_exceptions(self):
        class MyEG(ExceptionGroup):
            pass

        self.assertIs(
            type(MyEG("eg", [ValueError(12), TypeError(42)])),
            MyEG)

    def test_EG_subclass_does_not_wrap_base_exceptions(self):
        class MyEG(ExceptionGroup):
            pass

        msg = "Cannot nest BaseExceptions in 'MyEG'"
        with self.assertRaisesRegex(TypeError, msg):
            MyEG("eg", [ValueError(12), KeyboardInterrupt(42)])

    def test_BEG_and_E_subclass_does_not_wrap_base_exceptions(self):
        class MyEG(BaseExceptionGroup, ValueError):
            pass

        msg = "Cannot nest BaseExceptions in 'MyEG'"
        with self.assertRaisesRegex(TypeError, msg):
            MyEG("eg", [ValueError(12), KeyboardInterrupt(42)])

    def test_EG_and_specific_subclass_can_wrap_any_nonbase_exception(self):
        class MyEG(ExceptionGroup, ValueError):
            pass

        # The restriction is specific to Exception, not "the other base class"
        MyEG("eg", [ValueError(12), Exception()])

    def test_BEG_and_specific_subclass_can_wrap_any_nonbase_exception(self):
        class MyEG(BaseExceptionGroup, ValueError):
            pass

        # The restriction is specific to Exception, not "the other base class"
        MyEG("eg", [ValueError(12), Exception()])

    def test_BEG_subclass_wraps_anything(self):
        class MyBEG(BaseExceptionGroup):
            pass

        self.assertIs(
            type(MyBEG("eg", [ValueError(12), TypeError(42)])),
            MyBEG)
        self.assertIs(
            type(MyBEG("eg", [ValueError(12), KeyboardInterrupt(42)])),
            MyBEG)


class StrAndReprTests(HarnessCase):
    def test_ExceptionGroup(self):
        eg = BaseExceptionGroup(
            'flat', [ValueError(1), TypeError(2)])

        self.assertEqual(str(eg), "flat (2 sub-exceptions)")
        self.assertEqual(repr(eg),
            "ExceptionGroup('flat', [ValueError(1), TypeError(2)])")

        eg = BaseExceptionGroup(
            'nested', [eg, ValueError(1), eg, TypeError(2)])

        self.assertEqual(str(eg), "nested (4 sub-exceptions)")
        self.assertEqual(repr(eg),
            "ExceptionGroup('nested', "
                "[ExceptionGroup('flat', "
                    "[ValueError(1), TypeError(2)]), "
                 "ValueError(1), "
                 "ExceptionGroup('flat', "
                    "[ValueError(1), TypeError(2)]), TypeError(2)])")

    def test_BaseExceptionGroup(self):
        eg = BaseExceptionGroup(
            'flat', [ValueError(1), KeyboardInterrupt(2)])

        self.assertEqual(str(eg), "flat (2 sub-exceptions)")
        self.assertEqual(repr(eg),
            "BaseExceptionGroup("
                "'flat', "
                "[ValueError(1), KeyboardInterrupt(2)])")

        eg = BaseExceptionGroup(
            'nested', [eg, ValueError(1), eg])

        self.assertEqual(str(eg), "nested (3 sub-exceptions)")
        self.assertEqual(repr(eg),
            "BaseExceptionGroup('nested', "
                "[BaseExceptionGroup('flat', "
                    "[ValueError(1), KeyboardInterrupt(2)]), "
                "ValueError(1), "
                "BaseExceptionGroup('flat', "
                    "[ValueError(1), KeyboardInterrupt(2)])])")

    def test_custom_exception(self):
        class MyEG(ExceptionGroup):
            pass

        eg = MyEG(
            'flat', [ValueError(1), TypeError(2)])

        self.assertEqual(str(eg), "flat (2 sub-exceptions)")
        self.assertEqual(repr(eg), "MyEG('flat', [ValueError(1), TypeError(2)])")

        eg = MyEG(
            'nested', [eg, ValueError(1), eg, TypeError(2)])

        self.assertEqual(str(eg), "nested (4 sub-exceptions)")
        self.assertEqual(repr(eg), (
                 "MyEG('nested', "
                     "[MyEG('flat', [ValueError(1), TypeError(2)]), "
                      "ValueError(1), "
                      "MyEG('flat', [ValueError(1), TypeError(2)]), "
                      "TypeError(2)])"))

    def test_exceptions_mutation(self):
        class MyEG(ExceptionGroup):
            pass

        excs = [ValueError(1), TypeError(2)]
        eg = MyEG('test', excs)

        self.assertEqual(repr(eg), "MyEG('test', [ValueError(1), TypeError(2)])")
        excs.clear()

        # Ensure that clearing the exceptions sequence doesn't change the repr.
        self.assertEqual(repr(eg), "MyEG('test', [ValueError(1), TypeError(2)])")

        # Ensure that the args are still as passed.
        self.assertEqual(eg.args, ('test', []))

        excs = (ValueError(1), KeyboardInterrupt(2))
        eg = BaseExceptionGroup('test', excs)

        # Ensure that immutable sequences still work fine.
        self.assertEqual(
            repr(eg),
            "BaseExceptionGroup('test', (ValueError(1), KeyboardInterrupt(2)))"
        )

        # Test non-standard custom sequences.
        excs = collections.deque([ValueError(1), TypeError(2)])
        eg = ExceptionGroup('test', excs)

        self.assertEqual(
            repr(eg),
            "ExceptionGroup('test', deque([ValueError(1), TypeError(2)]))"
        )
        excs.clear()

        # Ensure that clearing the exceptions sequence doesn't change the repr.
        self.assertEqual(
            repr(eg),
            "ExceptionGroup('test', deque([ValueError(1), TypeError(2)]))"
        )

    def test_repr_small_size_args(self):
        eg = ExceptionGroup("msg", [ValueError()])
        eg.args = ()
        # repr of the ExceptionGroup with empty args should not crash
        self.assertEqual(repr(eg), "ExceptionGroup('msg', (ValueError(),))")

        eg.args = (1,)
        # repr of the ExceptionGroup with 1-size args should not crash
        self.assertEqual(repr(eg), "ExceptionGroup('msg', (ValueError(),))")

    # The helper's Sequence ABC base is omitted; len/getitem supply its protocol.
    def test_repr_raises(self):
        class MySeq:
            def __init__(self, raises):
                self.raises = raises

            def __len__(self):
                return 1

            def __getitem__(self, index):
                if index == 0:
                    return ValueError(1)
                raise IndexError

            def __repr__(self):
                if self.raises:
                    raise self.raises
                return None

        seq = MySeq(None)
        with self.assertRaisesRegex(
            TypeError,
            r"__repr__ returned non-string \(type NoneType\)"
        ):
            ExceptionGroup("test", seq)

        seq = MySeq(ValueError)
        with self.assertRaises(ValueError):
            BaseExceptionGroup("test", seq)


def create_simple_eg():
    excs = []
    try:
        try:
            raise MemoryError("context and cause for ValueError(1)")
        except MemoryError as e:
            raise ValueError(1) from e
    except ValueError as e:
        excs.append(e)

    try:
        try:
            raise OSError("context for TypeError")
        except OSError as e:
            raise TypeError(int)
    except TypeError as e:
        excs.append(e)

    try:
        try:
            raise ImportError("context for ValueError(2)")
        except ImportError as e:
            raise ValueError(2)
    except ValueError as e:
        excs.append(e)

    try:
        raise ExceptionGroup('simple eg', excs)
    except ExceptionGroup as e:
        return e

class ExceptionGroupFields(HarnessCase):
    def test_fields_are_readonly(self):
        eg = ExceptionGroup('eg', [TypeError(1), OSError(2)])

        self.assertEqual(type(eg.exceptions), tuple)

        eg.message
        with self.assertRaises(AttributeError):
            eg.message = "new msg"

        eg.exceptions
        with self.assertRaises(AttributeError):
            eg.exceptions = [OSError('xyz')]


class ExceptionGroupTestBase(HarnessCase):
    def assertMatchesTemplate(self, exc, exc_type, template):
        """ Assert that the exception matches the template

            A template describes the shape of exc. If exc is a
            leaf exception (i.e., not an exception group) then
            template is an exception instance that has the
            expected type and args value of exc. If exc is an
            exception group, then template is a list of the
            templates of its nested exceptions.
        """
        if exc_type is not None:
            self.assertIs(type(exc), exc_type)

        if isinstance(exc, BaseExceptionGroup):
            # All upstream templates here are lists; narrow the harness-only ABC check.
            self.assertIsInstance(template, list)
            self.assertEqual(len(exc.exceptions), len(template))
            for e, t in zip(exc.exceptions, template):
                self.assertMatchesTemplate(e, None, t)
        else:
            self.assertIsInstance(template, BaseException)
            self.assertEqual(type(exc), type(template))
            self.assertEqual(exc.args, template.args)


class Predicate:
    def __init__(self, func):
        self.func = func

    def __call__(self, e):
        return self.func(e)

    def method(self, e):
        return self.func(e)


class ExceptionGroupSubgroupTests(ExceptionGroupTestBase):
    def setUp(self):
        self.eg = create_simple_eg()
        self.eg_template = [ValueError(1), TypeError(int), ValueError(2)]

    def test_basics_subgroup_split__bad_arg_type(self):
        class C:
            pass

        bad_args = ["bad arg",
                    C,
                    OSError('instance not type'),
                    [OSError, TypeError],
                    (OSError, 42),
                   ]
        for arg in bad_args:
            with self.assertRaises(TypeError):
                self.eg.subgroup(arg)
            with self.assertRaises(TypeError):
                self.eg.split(arg)

    def test_basics_subgroup_by_type__passthrough(self):
        eg = self.eg
        self.assertIs(eg, eg.subgroup(BaseException))
        self.assertIs(eg, eg.subgroup(Exception))
        self.assertIs(eg, eg.subgroup(BaseExceptionGroup))
        self.assertIs(eg, eg.subgroup(ExceptionGroup))

    def test_basics_subgroup_by_type__no_match(self):
        self.assertIsNone(self.eg.subgroup(OSError))

    def test_basics_subgroup_by_type__match(self):
        eg = self.eg
        testcases = [
            # (match_type, result_template)
            (ValueError, [ValueError(1), ValueError(2)]),
            (TypeError, [TypeError(int)]),
            ((ValueError, TypeError), self.eg_template)]

        for match_type, template in testcases:
            with self.subTest(match=match_type):
                subeg = eg.subgroup(match_type)
                self.assertEqual(subeg.message, eg.message)
                self.assertMatchesTemplate(subeg, ExceptionGroup, template)

    def test_basics_subgroup_by_predicate__passthrough(self):
        f = lambda e: True
        for callable in [f, Predicate(f), Predicate(f).method]:
            self.assertIs(self.eg, self.eg.subgroup(callable))

    def test_basics_subgroup_by_predicate__no_match(self):
        f = lambda e: False
        for callable in [f, Predicate(f), Predicate(f).method]:
            self.assertIsNone(self.eg.subgroup(callable))

    def test_basics_subgroup_by_predicate__match(self):
        eg = self.eg
        testcases = [
            # (match_type, result_template)
            (ValueError, [ValueError(1), ValueError(2)]),
            (TypeError, [TypeError(int)]),
            ((ValueError, TypeError), self.eg_template)]

        for match_type, template in testcases:
            f = lambda e: isinstance(e, match_type)
            for callable in [f, Predicate(f), Predicate(f).method]:
                with self.subTest(callable=callable):
                    subeg = eg.subgroup(f)
                    self.assertEqual(subeg.message, eg.message)
                    self.assertMatchesTemplate(subeg, ExceptionGroup, template)


class ExceptionGroupSplitTests(ExceptionGroupTestBase):
    def setUp(self):
        self.eg = create_simple_eg()
        self.eg_template = [ValueError(1), TypeError(int), ValueError(2)]

    def test_basics_split_by_type__passthrough(self):
        for E in [BaseException, Exception,
                  BaseExceptionGroup, ExceptionGroup]:
            match, rest = self.eg.split(E)
            self.assertMatchesTemplate(
                match, ExceptionGroup, self.eg_template)
            self.assertIsNone(rest)

    def test_basics_split_by_type__no_match(self):
        match, rest = self.eg.split(OSError)
        self.assertIsNone(match)
        self.assertMatchesTemplate(
            rest, ExceptionGroup, self.eg_template)

    def test_basics_split_by_type__match(self):
        eg = self.eg
        VE = ValueError
        TE = TypeError
        testcases = [
            # (matcher, match_template, rest_template)
            (VE, [VE(1), VE(2)], [TE(int)]),
            (TE, [TE(int)], [VE(1), VE(2)]),
            ((VE, TE), self.eg_template, None),
            ((OSError, VE), [VE(1), VE(2)], [TE(int)]),
        ]

        for match_type, match_template, rest_template in testcases:
            match, rest = eg.split(match_type)
            self.assertEqual(match.message, eg.message)
            self.assertMatchesTemplate(
                match, ExceptionGroup, match_template)
            if rest_template is not None:
                self.assertEqual(rest.message, eg.message)
                self.assertMatchesTemplate(
                    rest, ExceptionGroup, rest_template)
            else:
                self.assertIsNone(rest)

    def test_basics_split_by_predicate__passthrough(self):
        f = lambda e: True
        for callable in [f, Predicate(f), Predicate(f).method]:
            match, rest = self.eg.split(callable)
            self.assertMatchesTemplate(match, ExceptionGroup, self.eg_template)
            self.assertIsNone(rest)

    def test_basics_split_by_predicate__no_match(self):
        f = lambda e: False
        for callable in [f, Predicate(f), Predicate(f).method]:
            match, rest = self.eg.split(callable)
            self.assertIsNone(match)
            self.assertMatchesTemplate(rest, ExceptionGroup, self.eg_template)

    def test_basics_split_by_predicate__match(self):
        eg = self.eg
        VE = ValueError
        TE = TypeError
        testcases = [
            # (matcher, match_template, rest_template)
            (VE, [VE(1), VE(2)], [TE(int)]),
            (TE, [TE(int)], [VE(1), VE(2)]),
            ((VE, TE), self.eg_template, None),
        ]

        for match_type, match_template, rest_template in testcases:
            f = lambda e: isinstance(e, match_type)
            for callable in [f, Predicate(f), Predicate(f).method]:
                match, rest = eg.split(callable)
                self.assertEqual(match.message, eg.message)
                self.assertMatchesTemplate(
                    match, ExceptionGroup, match_template)
                if rest_template is not None:
                    self.assertEqual(rest.message, eg.message)
                    self.assertMatchesTemplate(
                        rest, ExceptionGroup, rest_template)


class ExceptionGroupRegression(HarnessCase):
    def test_nested_custom_derive_and_metadata(self):
        class Group(ExceptionGroup):
            def __new__(cls, message, exceptions, tag):
                return super().__new__(cls, message, exceptions)
            def __init__(self, message, exceptions, tag):
                super().__init__(message, exceptions)
                self.tag = tag
            def derive(self, exceptions):
                return Group(self.message, exceptions, self.tag)
        value, type_error = ValueError(1), TypeError(2)
        nested = Group('nested', [value, type_error], 3)
        group = Group('root', [nested, value], 4)
        cause, context = OSError('cause'), ImportError('context')
        group.__cause__, group.__context__ = cause, context
        group.__notes__ = ('one', 'two')
        matching, rest = group.split(ValueError)
        self.assertEqual((matching.tag, rest.tag), (4, 4))
        self.assertEqual(matching.exceptions[0].tag, 3)
        self.assertEqual(rest.exceptions[0].tag, 3)
        self.assertIs(matching.exceptions[0].exceptions[0], value)
        self.assertIs(matching.exceptions[1], value)
        self.assertIs(rest.exceptions[0].exceptions[0], type_error)
        for part in (matching, rest):
            self.assertIs(part.__cause__, cause)
            self.assertIs(part.__context__, context)
            self.assertEqual(part.__notes__, ['one', 'two'])
        matching.__notes__.append('three')
        self.assertEqual(rest.__notes__, ['one', 'two'])
        self.assertEqual(group.__notes__, ('one', 'two'))
        self.assertIs(group.subgroup(lambda exc: exc is group), group)
        self.assertIs(group.split(BaseExceptionGroup)[0], group)

    def test_exact_tuple_identity_and_message_string_protocol(self):
        exceptions = (ValueError(),)
        group = ExceptionGroup('message', exceptions)
        self.assertIs(group.exceptions, exceptions)
        class Tuple(tuple): pass
        self.assertIs(type(ExceptionGroup('message', Tuple(exceptions)).exceptions), tuple)
        class Message(str):
            def __str__(self): return 'display'
        message = Message('stored')
        group = ExceptionGroup(message, exceptions)
        self.assertIs(group.message, message)
        self.assertEqual(str(group), 'display (1 sub-exception)')
        class Broken(str):
            def __str__(self): raise ValueError('string conversion')
        group = ExceptionGroup(Broken('stored'), exceptions)
        with self.assertRaisesRegex(ValueError, 'string conversion'):
            str(group)

    def test_derive_validation_and_callable_failures(self):
        class Broken(ExceptionGroup):
            def derive(self, exceptions):
                return ValueError()
        group = Broken('broken', [ValueError(), TypeError()])
        with self.assertRaisesRegex(TypeError, 'derive must return an instance of BaseExceptionGroup'):
            group.split(ValueError)
        def predicate(exception):
            raise ValueError('predicate')
        with self.assertRaisesRegex(ValueError, 'predicate'):
            group.subgroup(predicate)
        class Tuple(tuple): pass
        with self.assertRaises(TypeError):
            group.split(Tuple((ValueError,)))
        self.assertEqual(ExceptionGroup.__bases__, (BaseExceptionGroup, Exception))
        self.assertEqual(ExceptionGroup.__mro__, (ExceptionGroup, BaseExceptionGroup, Exception, BaseException, object))
        with self.assertRaises(TypeError):
            BaseExceptionGroup.new_attribute = 1
        ExceptionGroup.new_attribute = 1
        self.assertEqual(ExceptionGroup.new_attribute, 1)
        del ExceptionGroup.new_attribute

if __name__ == "__main__": unittest.main()
