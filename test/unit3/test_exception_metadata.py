import unittest


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
