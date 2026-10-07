"""
This file was modified from CPython.
Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
2011, 2012, 2013, 2014, 2015 Python Software Foundation; All Rights Reserved
"""
"""Define names for all type symbols known in the standard interpreter.
Types that are part of optional modules (e.g. array) are not listed.
"""
import sys

# Iterators in Python aren't a matter of type but of protocol.  A large
# and changing number of builtin types implement *some* flavor of
# iterator.  Don't check the type!  Use hasattr to check for both
# "__iter__" and "next" attributes instead.
MappingProxyType = type(type.__dict__)
WrapperDescriptorType = type(object.__init__)
MethodWrapperType = type(object().__str__)
MethodDescriptorType = type(str.join)
ClassMethodDescriptorType = type(dict.__dict__['fromkeys'])

NoneType = type(None)
TypeType = type
ObjectType = object
IntType = int
try:
    LongType = long
except: pass
FloatType = float
BooleanType = bool
try:
    ComplexType = complex
except NameError:
    pass
StringType = str

# StringTypes is already outdated.  Instead of writing "type(x) in
# types.StringTypes", you should use "isinstance(x, basestring)".  But
# we keep around for compatibility with Python 2.2.
try:
    UnicodeType = unicode
    StringTypes = (StringType, UnicodeType)
except NameError:
    StringTypes = (StringType,)

BufferType = buffer

TupleType = tuple
ListType = list
DictType = DictionaryType = dict

def _f(): pass
FunctionType = type(_f)
LambdaType = type(lambda: None)         # Same as FunctionType
CodeType = type(_f.__code__)
def _cell_factory():
    a = None
    def f():
        return a
    return f.__closure__[0]
CellType = type(_cell_factory())

def _g():
    yield 1
GeneratorType = type(_g())
if sys.version_info[0] >= 3:
    exec("async def _c(): pass")
    _coro = _c()
    CoroutineType = type(_coro)
    exec("async def _ag(): yield")
    AsyncGeneratorType = type(_ag())
    del _ag
    _coro.close()
    del _coro, _c

class _C:
    def _m(self): pass
ClassType = type(_C)
UnboundMethodType = type(_C._m)         # Same as MethodType
_x = _C()
InstanceType = type(_x)
MethodType = type(_x._m)
BuiltinFunctionType = type(len)
BuiltinMethodType = type([].append)     # Same as BuiltinFunctionType

ModuleType = type(sys)
FileType = file
try:
    XRangeType = xrange
except NameError:
    pass

# try:
#     raise TypeError
# except TypeError:
#     tb = sys.exc_info()[2]
#     TracebackType = type(tb)
#     FrameType = type(tb.tb_frame)
#     del tb

SliceType = slice
EllipsisType = type(Ellipsis)

# DictProxyType = type(TypeType.__dict__)
NotImplementedType = type(NotImplemented)

# For Jython, the following two types are identical
# GetSetDescriptorType = type(FunctionType.func_code)
# MemberDescriptorType = type(FunctionType.func_globals)

# Class construction helpers from CPython 3.14 at 18ef0f0cb52.
# Provide a PEP 3115 compliant mechanism for class creation
def new_class(name, bases=(), kwds=None, exec_body=None):
    """Create a class object dynamically using the appropriate metaclass."""
    resolved_bases = resolve_bases(bases)
    meta, ns, kwds = prepare_class(name, resolved_bases, kwds)
    if exec_body is not None:
        exec_body(ns)
    if resolved_bases is not bases:
        ns['__orig_bases__'] = bases
    return meta(name, resolved_bases, ns, **kwds)

def resolve_bases(bases):
    """Resolve MRO entries dynamically as specified by PEP 560."""
    new_bases = list(bases)
    updated = False
    shift = 0
    for i, base in enumerate(bases):
        if isinstance(base, type):
            continue
        if not hasattr(base, "__mro_entries__"):
            continue
        new_base = base.__mro_entries__(bases)
        updated = True
        if not isinstance(new_base, tuple):
            raise TypeError("__mro_entries__ must return a tuple")
        else:
            new_bases[i+shift:i+shift+1] = new_base
            shift += len(new_base) - 1
    if not updated:
        return bases
    return tuple(new_bases)

def prepare_class(name, bases=(), kwds=None):
    """Call the __prepare__ method of the appropriate metaclass.

    Returns (metaclass, namespace, kwds) as a 3-tuple

    *metaclass* is the appropriate metaclass
    *namespace* is the prepared class namespace
    *kwds* is an updated copy of the passed in kwds argument with any
    'metaclass' entry removed. If no kwds argument is passed in, this will
    be an empty dict.
    """
    if kwds is None:
        kwds = {}
    else:
        kwds = dict(kwds) # Don't alter the provided mapping
    if 'metaclass' in kwds:
        meta = kwds.pop('metaclass')
    else:
        if bases:
            meta = type(bases[0])
        else:
            meta = type
    if isinstance(meta, type):
        # when meta is a type, we first determine the most-derived metaclass
        # instead of invoking the initial candidate directly
        meta = _calculate_meta(meta, bases)
    if hasattr(meta, '__prepare__'):
        ns = meta.__prepare__(name, bases, **kwds)
    else:
        ns = {}
    return meta, ns, kwds

def _calculate_meta(meta, bases):
    """Calculate the most derived metaclass."""
    winner = meta
    for base in bases:
        base_meta = type(base)
        if issubclass(winner, base_meta):
            continue
        if issubclass(base_meta, winner):
            winner = base_meta
            continue
        # else:
        raise TypeError("metaclass conflict: "
                        "the metaclass of a derived class "
                        "must be a (non-strict) subclass "
                        "of the metaclasses of all its bases")
    return winner


def get_original_bases(cls, /):
    """Return the class's "original" bases prior to modification by `__mro_entries__`.

    Examples::

        from typing import TypeVar, Generic, NamedTuple, TypedDict

        T = TypeVar("T")
        class Foo(Generic[T]): ...
        class Bar(Foo[int], float): ...
        class Baz(list[str]): ...
        Eggs = NamedTuple("Eggs", [("a", int), ("b", str)])
        Spam = TypedDict("Spam", {"a": int, "b": str})

        assert get_original_bases(Bar) == (Foo[int], float)
        assert get_original_bases(Baz) == (list[str],)
        assert get_original_bases(Eggs) == (NamedTuple,)
        assert get_original_bases(Spam) == (TypedDict,)
        assert get_original_bases(int) == (object,)
    """
    try:
        return cls.__dict__.get("__orig_bases__", cls.__bases__)
    except AttributeError:
        raise TypeError(
            f"Expected an instance of type, not {type(cls).__name__!r}"
        ) from None


del sys, _f, _g, _C, _x                           # Not for export

GenericAlias = type(type[int])
# Generator-based coroutines from CPython 3.14 at 18ef0f0cb52.
# CPython _collections_abc._check_methods, without ABC registration machinery.
# Structural protocol checks cover native and Python generator-like objects.
def _has_methods(cls, *methods):
    for method in methods:
        for base in cls.__mro__:
            if method in base.__dict__:
                if base.__dict__[method] is None:
                    return False
                break
        else:
            return False
    return True

class _GeneratorWrapper:
    # TODO: Implement this in C.
    def __init__(self, gen):
        self.__wrapped = gen
        self.__isgen = gen.__class__ is GeneratorType
        self.__name__ = getattr(gen, '__name__', None)
        self.__qualname__ = getattr(gen, '__qualname__', None)
    def send(self, val):
        return self.__wrapped.send(val)
    def throw(self, tp, *rest):
        return self.__wrapped.throw(tp, *rest)
    def close(self):
        return self.__wrapped.close()
    @property
    def gi_code(self):
        return self.__wrapped.gi_code
    @property
    def gi_frame(self):
        return self.__wrapped.gi_frame
    @property
    def gi_running(self):
        return self.__wrapped.gi_running
    @property
    def gi_yieldfrom(self):
        return self.__wrapped.gi_yieldfrom
    @property
    def gi_suspended(self):
        return self.__wrapped.gi_suspended
    cr_code = gi_code
    cr_frame = gi_frame
    cr_running = gi_running
    cr_await = gi_yieldfrom
    cr_suspended = gi_suspended
    def __next__(self):
        return next(self.__wrapped)
    def __iter__(self):
        if self.__isgen:
            return self.__wrapped
        return self
    __await__ = __iter__

def coroutine(func):
    """Convert regular generator function to a coroutine."""

    if not callable(func):
        raise TypeError('types.coroutine() expects a callable')

    if (func.__class__ is FunctionType and
        getattr(func, '__code__', None).__class__ is CodeType):

        co_flags = func.__code__.co_flags

        # Check if 'func' is a coroutine function.
        # (0x180 == CO_COROUTINE | CO_ITERABLE_COROUTINE)
        if co_flags & 0x180:
            return func

        # Check if 'func' is a generator function.
        # (0x20 == CO_GENERATOR)
        if co_flags & 0x20:
            # TODO: Implement this in C.
            co = func.__code__
            # 0x100 == CO_ITERABLE_COROUTINE
            func.__code__ = co.replace(co_flags=co.co_flags | 0x100)
            return func

    # The following code is primarily to support functions that
    # return generator-like objects (for instance generators
    # compiled with Cython).

    # Delay functools and _collections_abc import for speeding up types import.
    import functools
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        coro = func(*args, **kwargs)
        if (coro.__class__ is CoroutineType or
            coro.__class__ is GeneratorType and coro.gi_code.co_flags & 0x100):
            # 'coro' is a native coroutine object or an iterable coroutine
            return coro
        if (_has_methods(type(coro), '__iter__', '__next__', 'send', 'throw', 'close') and
            not _has_methods(type(coro), '__await__', 'send', 'throw', 'close')):
            # 'coro' is either a pure Python generator iterator, or it
            # implements collections.abc.Generator (and does not implement
            # collections.abc.Coroutine).
            return _GeneratorWrapper(coro)
        # 'coro' is either an instance of collections.abc.Coroutine or
        # some other object -- pass it through.
        return coro

    return wrapped

__all__ = list(n for n in globals() if n[:1] != '_')
