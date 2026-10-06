# Compiler-related protocol ABCs from CPython 3.14 Lib/_collections_abc.py.
from abc import ABCMeta, abstractmethod
from types import GenericAlias

__all__ = ["Awaitable", "Coroutine", "AsyncIterable", "AsyncIterator", "AsyncGenerator",
           "Iterable", "Iterator", "Generator", "Callable"]


def _check_methods(C, *methods):
    mro = C.__mro__
    for method in methods:
        for B in mro:
            if method in B.__dict__:
                if B.__dict__[method] is None:
                    return NotImplemented
                break
        else:
            return NotImplemented
    return True


class Awaitable(metaclass=ABCMeta):

    __slots__ = ()

    @abstractmethod
    def __await__(self):
        yield

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Awaitable:
            return _check_methods(C, "__await__")
        return NotImplemented

    __class_getitem__ = classmethod(GenericAlias)


class Coroutine(Awaitable):

    __slots__ = ()

    @abstractmethod
    def send(self, value):
        """Send a value into the coroutine.
        Return next yielded value or raise StopIteration.
        """
        raise StopIteration

    @abstractmethod
    def throw(self, typ, val=None, tb=None):
        """Raise an exception in the coroutine.
        Return next yielded value or raise StopIteration.
        """
        if val is None:
            if tb is None:
                raise typ
            val = typ()
        if tb is not None:
            val = val.with_traceback(tb)
        raise val

    def close(self):
        """Raise GeneratorExit inside coroutine.
        """
        try:
            self.throw(GeneratorExit)
        except (GeneratorExit, StopIteration):
            pass
        else:
            raise RuntimeError("coroutine ignored GeneratorExit")

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Coroutine:
            return _check_methods(C, '__await__', 'send', 'throw', 'close')
        return NotImplemented


class AsyncIterable(metaclass=ABCMeta):

    __slots__ = ()

    @abstractmethod
    def __aiter__(self):
        return AsyncIterator()

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AsyncIterable:
            return _check_methods(C, "__aiter__")
        return NotImplemented

    __class_getitem__ = classmethod(GenericAlias)


class AsyncIterator(AsyncIterable):

    __slots__ = ()

    @abstractmethod
    async def __anext__(self):
        """Return the next item or raise StopAsyncIteration when exhausted."""
        raise StopAsyncIteration

    def __aiter__(self):
        return self

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AsyncIterator:
            return _check_methods(C, "__anext__", "__aiter__")
        return NotImplemented


class AsyncGenerator(AsyncIterator):

    __slots__ = ()

    async def __anext__(self):
        """Return the next item from the asynchronous generator.
        When exhausted, raise StopAsyncIteration.
        """
        return await self.asend(None)

    @abstractmethod
    async def asend(self, value):
        """Send a value into the asynchronous generator.
        Return next yielded value or raise StopAsyncIteration.
        """
        raise StopAsyncIteration

    @abstractmethod
    async def athrow(self, typ, val=None, tb=None):
        """Raise an exception in the asynchronous generator.
        Return next yielded value or raise StopAsyncIteration.
        """
        if val is None:
            if tb is None:
                raise typ
            val = typ()
        if tb is not None:
            val = val.with_traceback(tb)
        raise val

    async def aclose(self):
        """Raise GeneratorExit inside coroutine.
        """
        try:
            await self.athrow(GeneratorExit)
        except (GeneratorExit, StopAsyncIteration):
            pass
        else:
            raise RuntimeError("asynchronous generator ignored GeneratorExit")

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AsyncGenerator:
            return _check_methods(C, '__aiter__', '__anext__',
                                  'asend', 'athrow', 'aclose')
        return NotImplemented


class Iterable(metaclass=ABCMeta):

    __slots__ = ()

    @abstractmethod
    def __iter__(self):
        while False:
            yield None

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Iterable:
            return _check_methods(C, "__iter__")
        return NotImplemented

    __class_getitem__ = classmethod(GenericAlias)


class Iterator(Iterable):

    __slots__ = ()

    @abstractmethod
    def __next__(self):
        'Return the next item from the iterator. When exhausted, raise StopIteration'
        raise StopIteration

    def __iter__(self):
        return self

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Iterator:
            return _check_methods(C, '__iter__', '__next__')
        return NotImplemented


class Generator(Iterator):

    __slots__ = ()

    def __next__(self):
        """Return the next item from the generator.
        When exhausted, raise StopIteration.
        """
        return self.send(None)

    @abstractmethod
    def send(self, value):
        """Send a value into the generator.
        Return next yielded value or raise StopIteration.
        """
        raise StopIteration

    @abstractmethod
    def throw(self, typ, val=None, tb=None):
        """Raise an exception in the generator.
        Return next yielded value or raise StopIteration.
        """
        if val is None:
            if tb is None:
                raise typ
            val = typ()
        if tb is not None:
            val = val.with_traceback(tb)
        raise val

    def close(self):
        """Raise GeneratorExit inside generator.
        """
        try:
            self.throw(GeneratorExit)
        except (GeneratorExit, StopIteration):
            pass
        else:
            raise RuntimeError("generator ignored GeneratorExit")

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Generator:
            return _check_methods(C, '__iter__', '__next__',
                                  'send', 'throw', 'close')
        return NotImplemented


class _CallableGenericAlias(GenericAlias):
    """ Represent `Callable[argtypes, resulttype]`.

    This sets ``__args__`` to a tuple containing the flattened
    ``argtypes`` followed by ``resulttype``.

    Example: ``Callable[[int, str], float]`` sets ``__args__`` to
    ``(int, str, float)``.
    """

    __slots__ = ()

    def __new__(cls, origin, args):
        if not (isinstance(args, tuple) and len(args) == 2):
            raise TypeError(
                "Callable must be used as Callable[[arg, ...], result].")
        t_args, t_result = args
        if isinstance(t_args, (tuple, list)):
            args = (*t_args, t_result)
        elif not _is_param_expr(t_args):
            raise TypeError(f"Expected a list of types, an ellipsis, "
                            f"ParamSpec, or Concatenate. Got {t_args}")
        return super().__new__(cls, origin, args)

    def __repr__(self):
        if len(self.__args__) == 2 and _is_param_expr(self.__args__[0]):
            return super().__repr__()
        from _typing import _type_repr as type_repr
        return (f'collections.abc.Callable'
                f'[[{", ".join([type_repr(a) for a in self.__args__[:-1]])}], '
                f'{type_repr(self.__args__[-1])}]')

    def __reduce__(self):
        args = self.__args__
        if not (len(args) == 2 and _is_param_expr(args[0])):
            args = list(args[:-1]), args[-1]
        return _CallableGenericAlias, (Callable, args)

    def __getitem__(self, item):
        # Called during TypeVar substitution, returns the custom subclass
        # rather than the default types.GenericAlias object.  Most of the
        # code is copied from typing's _GenericAlias and the builtin
        # types.GenericAlias.
        if not isinstance(item, tuple):
            item = (item,)

        new_args = super().__getitem__(item).__args__

        # args[0] occurs due to things like Z[[int, str, bool]] from PEP 612
        if not isinstance(new_args[0], (tuple, list)):
            t_result = new_args[-1]
            t_args = new_args[:-1]
            new_args = (t_args, t_result)
        return _CallableGenericAlias(Callable, tuple(new_args))


def _is_param_expr(obj):
    """Checks if obj matches either a list of types, ``...``, ``ParamSpec`` or
    ``_ConcatenateGenericAlias`` from typing.py
    """
    if obj is Ellipsis:
        return True
    if isinstance(obj, list):
        return True
    obj = type(obj)
    names = ('ParamSpec', '_ConcatenateGenericAlias')
    return obj.__module__ == 'typing' and any(obj.__name__ == name for name in names)


class Callable(metaclass=ABCMeta):

    __slots__ = ()

    @abstractmethod
    def __call__(self, *args, **kwds):
        return False

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Callable:
            return _check_methods(C, "__call__")
        return NotImplemented

    __class_getitem__ = classmethod(_CallableGenericAlias)


# Native compiler-produced types are explicitly registered, as in CPython.
_generator = type((lambda: (yield))())
Generator.register(_generator)
async def _coro(): pass
_coroutine = _coro()
Coroutine.register(type(_coroutine))
_coroutine.close()
async def _ag(): yield
_async_generator = _ag()
AsyncGenerator.register(type(_async_generator))
del _generator, _coro, _coroutine, _ag, _async_generator
