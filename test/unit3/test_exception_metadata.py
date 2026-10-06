# CPython 3.14 Lib/test/test_exceptions.py at 18ef0f0cb52.
import unittest

class SubTest:
    def __enter__(self): return self
    def __exit__(self, *args): return False

class ExceptionMetadataTests(unittest.TestCase):
    def subTest(self, *args, **kwargs): return SubTest()
    def assertNotHasAttr(self, obj, name): self.assertFalse(hasattr(obj, name))

    def test_notes(self):
        for e in [BaseException(1), Exception(2), ValueError(3)]:
            with self.subTest(e=e):
                self.assertNotHasAttr(e, '__notes__')
                e.add_note("My Note")
                self.assertEqual(e.__notes__, ["My Note"])

                with self.assertRaises(TypeError):
                    e.add_note(42)
                self.assertEqual(e.__notes__, ["My Note"])

                e.add_note("Your Note")
                self.assertEqual(e.__notes__, ["My Note", "Your Note"])

                del e.__notes__
                self.assertNotHasAttr(e, '__notes__')

                e.add_note("Our Note")
                self.assertEqual(e.__notes__, ["Our Note"])

                e.__notes__ = 42
                self.assertEqual(e.__notes__, 42)

                with self.assertRaises(TypeError):
                    e.add_note("will not work")
                self.assertEqual(e.__notes__, 42)

    def testChainingAttrs(self):
        e = Exception()
        self.assertIsNone(e.__context__)
        self.assertIsNone(e.__cause__)

        e = TypeError()
        self.assertIsNone(e.__context__)
        self.assertIsNone(e.__cause__)

        class MyException(OSError):
            pass

        e = MyException()
        self.assertIsNone(e.__context__)
        self.assertIsNone(e.__cause__)

    def testChainingDescriptors(self):
        try:
            raise Exception()
        except Exception as exc:
            e = exc

        self.assertIsNone(e.__context__)
        self.assertIsNone(e.__cause__)
        self.assertFalse(e.__suppress_context__)

        e.__context__ = NameError()
        e.__cause__ = None
        self.assertIsInstance(e.__context__, NameError)
        self.assertIsNone(e.__cause__)
        self.assertTrue(e.__suppress_context__)
        e.__suppress_context__ = False
        self.assertFalse(e.__suppress_context__)
        with self.assertRaisesRegex(TypeError,
                                    'attribute value type must be bool'):
            e.__suppress_context__ = 1
        with self.assertRaisesRegex(TypeError,
                                    "can't delete numeric/char attribute"):
            del e.__suppress_context__
        self.assertFalse(e.__suppress_context__)

class ExceptionNotesRegression(unittest.TestCase):
    def test_notes_descriptors_and_native_append(self):
        class Notes(list):
            def append(self, note):
                raise AssertionError('native append must bypass Python overrides')
        class Note(str):
            pass
        class Error(Exception):
            @property
            def __notes__(self):
                return self.storage
            @__notes__.setter
            def __notes__(self, value):
                self.storage = value
        error = Error()
        note = Note('first')
        self.assertIsNone(error.add_note(note))
        self.assertIs(error.storage[0], note)
        error.storage = Notes()
        error.add_note('second')
        self.assertEqual(error.storage, ['second'])
        class Broken(Exception):
            @property
            def __notes__(self):
                raise ValueError('getter')
        with self.assertRaisesRegex(ValueError, 'getter'):
            Broken().add_note('note')
        class ReadOnly(Exception):
            @property
            def __notes__(self):
                raise AttributeError('absent')
        with self.assertRaises(AttributeError):
            ReadOnly().add_note('note')
        error = Exception()
        with self.assertRaises(TypeError):
            error.__cause__ = 1
        with self.assertRaises(TypeError):
            del error.__cause__
        self.assertFalse(error.__suppress_context__)
        cause = ValueError()
        error.__cause__ = cause
        self.assertIs(error.__cause__, cause)
        self.assertTrue(error.__suppress_context__)



class NameErrorTests(unittest.TestCase):

    def test_name_error_has_name(self):
        try:
            bluch
        except NameError as exc:
            self.assertEqual("bluch", exc.name)


class AttributeErrorTests(unittest.TestCase):

    def test_attributes(self):
        # Setting 'attr' should not be a problem.
        exc = AttributeError('Ouch!')
        self.assertIsNone(exc.name)
        self.assertIsNone(exc.obj)

        sentinel = object()
        exc = AttributeError('Ouch', name='carry', obj=sentinel)
        self.assertEqual(exc.name, 'carry')
        self.assertIs(exc.obj, sentinel)

    def test_getattr_has_name_and_obj(self):
        class A:
            blech = None

        obj = A()
        try:
            obj.bluch
        except AttributeError as exc:
            self.assertEqual("bluch", exc.name)
            self.assertEqual(obj, exc.obj)
        try:
            object.__getattribute__(obj, "bluch")
        except AttributeError as exc:
            self.assertEqual("bluch", exc.name)
            self.assertEqual(obj, exc.obj)

    def test_getattr_has_name_and_obj_for_method(self):
        class A:
            def blech(self):
                return

        obj = A()
        try:
            obj.bluch()
        except AttributeError as exc:
            self.assertEqual("bluch", exc.name)
            self.assertEqual(obj, exc.obj)

class AttributeContextRegression(unittest.TestCase):
    # Objects/object.c:_PyObject_SetAttributeErrorContext; CPython checked.
    def test_user_exceptions_preserve_message_and_explicit_context(self):
        class A:
            def __getattribute__(self, name):
                raise AttributeError('manual')
        obj = A()
        for read in (lambda: obj.missing, lambda: getattr(obj, 'missing')):
            with self.assertRaises(AttributeError) as caught:
                read()
            self.assertEqual(str(caught.exception), 'manual')
            self.assertEqual(caught.exception.name, 'missing')
            self.assertIs(caught.exception.obj, obj)
        class B:
            def __getattr__(self, name):
                raise AttributeError('chosen', name='custom', obj=5)
        with self.assertRaises(AttributeError) as caught:
            B().missing
        self.assertEqual(str(caught.exception), 'chosen')
        self.assertEqual(caught.exception.name, 'custom')
        self.assertEqual(caught.exception.obj, 5)
        class C:
            def __getattribute__(self, name):
                raise AttributeError('explicit', name=None)
        with self.assertRaises(AttributeError) as caught:
            C().missing
        self.assertIsNone(caught.exception.name)
        self.assertIsNone(caught.exception.obj)

    def test_name_error_keywords_and_deletion(self):
        exc = NameError('missing', name='target')
        self.assertEqual(exc.args, ('missing',))
        self.assertEqual(exc.name, 'target')
        del exc.name
        self.assertIsNone(exc.name)
        with self.assertRaises(TypeError):
            NameError('missing', obj=1)
        self.assertEqual(UnboundLocalError('missing', name='local').name, 'local')

    def test_compiler_name_error_context(self):
        for source in ('del absent',
                       'def f():\n global absent\n del absent\nf()',
                       'def outer():\n def inner():return absent\n inner()\n absent=1\nouter()'):
            with self.assertRaises(NameError) as caught:
                exec(source, {})
            self.assertEqual(caught.exception.name, 'absent')

if __name__ == '__main__': unittest.main()
