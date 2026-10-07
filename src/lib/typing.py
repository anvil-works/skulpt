"""CPython runtime objects for compiler-created type hints."""
from _typing import TypeAliasType, TypeVar, NoDefault, ParamSpec, ParamSpecArgs, ParamSpecKwargs, TypeVarTuple, Unpack, _UnpackGenericAlias
from types import GenericAlias, UnionType
import sys
import functools
import operator
import collections.abc
import types
class _LazyAnnotationLib:
    def __getattr__(self, attr):
        global _lazy_annotationlib
        import annotationlib
        _lazy_annotationlib = annotationlib
        return getattr(annotationlib, attr)


_lazy_annotationlib = _LazyAnnotationLib()

Union = UnionType

def get_args(tp):
    if isinstance(tp, _AnnotatedAlias):
        return (tp.__origin__, *tp.__metadata__)
    if isinstance(tp, (GenericAlias, UnionType, _UnpackGenericAlias, _GenericAlias)):
        args = tp.__args__
        if isinstance(tp, (_GenericAlias, GenericAlias)) and _should_unflatten_callable_args(tp, args):
            args = (list(args[:-1]), args[-1])
        return args
    return ()

def get_origin(tp):
    if isinstance(tp, _AnnotatedAlias):
        return Annotated
    if isinstance(tp, (GenericAlias, UnionType, _UnpackGenericAlias, _GenericAlias, _SpecialGenericAlias, ParamSpecArgs, ParamSpecKwargs)):
        return tp.__origin__
    return None

# CPython caching preserves specialization identity while allowing unhashable arguments.
_cleanups = []
_caches = {}


def _tp_cache(func=None, /, *, typed=False):
    """Internal wrapper caching __getitem__ of generic types.

    For non-hashable arguments, the original function is used as a fallback.
    """
    def decorator(func):
        # The callback 'inner' references the newly created lru_cache
        # indirectly by performing a lookup in the global '_caches' dictionary.
        # This breaks a reference that can be problematic when combined with
        # C API extensions that leak references to types. See GH-98253.

        cache = functools.lru_cache(typed=typed)(func)
        _caches[func] = cache
        _cleanups.append(cache.cache_clear)
        del cache

        @functools.wraps(func)
        def inner(*args, **kwds):
            try:
                return _caches[func](*args, **kwds)
            except TypeError:
                pass  # All real errors (not unhashable args) are raised below.
            return func(*args, **kwds)
        return inner

    if func is not None:
        return decorator(func)

    return decorator


class _Final:
    """Mixin to prohibit subclassing."""

    __slots__ = ('__weakref__',)

    def __init_subclass__(cls, /, *args, **kwds):
        if '_root' not in kwds:
            raise TypeError("Cannot subclass special typing classes")


class _NotIterable:
    """Mixin to prevent iteration, without being compatible with Iterable.

    That is, we could do::

        def __iter__(self): raise TypeError()

    But this would make users of this mixin duck type-compatible with
    collections.abc.Iterable - isinstance(foo, Iterable) would be True.

    Luckily, we can instead prevent iteration by setting __iter__ to None, which
    is treated specially.
    """

    __slots__ = ()
    __iter__ = None


# Internal indicator of special typing constructs.
# See __doc__ instance attribute for specific docs.
class _SpecialForm(_Final, _NotIterable, _root=True):
    __slots__ = ('_name', '__doc__', '_getitem')

    def __init__(self, getitem):
        self._getitem = getitem
        self._name = getitem.__name__
        self.__doc__ = getitem.__doc__

    def __getattr__(self, item):
        if item in {'__name__', '__qualname__'}:
            return self._name

        raise AttributeError(item)

    def __mro_entries__(self, bases):
        raise TypeError(f"Cannot subclass {self!r}")

    def __repr__(self):
        return 'typing.' + self._name

    def __reduce__(self):
        return self._name

    def __call__(self, *args, **kwds):
        raise TypeError(f"Cannot instantiate {self!r}")

    def __or__(self, other):
        return Union[self, other]

    def __ror__(self, other):
        return Union[other, self]

    def __instancecheck__(self, obj):
        raise TypeError(f"{self} cannot be used with isinstance()")

    def __subclasscheck__(self, cls):
        raise TypeError(f"{self} cannot be used with issubclass()")

    @_tp_cache
    def __getitem__(self, parameters):
        return self._getitem(self, parameters)



# Helpers invoked by native parameters, following CPython Lib/typing.py.
def _type_check(arg, msg, is_argument=True, module=None, *, allow_special_forms=False, owner=None):
    """Check that the argument is a type, and return it (internal helper).

    As a special case, accept None and return type(None) instead. Also wrap strings
    into ForwardRef instances. Consider several corner cases, for example plain
    special forms like Union are not valid, while Union[int, str] is OK, etc.
    The msg argument is a human-readable error message, e.g.::

        "Union[arg, ...]: arg should be a type."

    We append the repr() of the actual value (truncated to 100 chars).
    """
    invalid_generic_forms = (Generic,)
    if not allow_special_forms:
        invalid_generic_forms += (ClassVar,)
        if is_argument:
            invalid_generic_forms += (Final,)

    arg = _type_convert(arg, module=module, allow_special_forms=allow_special_forms, owner=owner)
    if (isinstance(arg, _GenericAlias) and
            arg.__origin__ in invalid_generic_forms):
        raise TypeError(f"{arg} is not valid as type argument")
    if arg in (Any, LiteralString, NoReturn, Never, Self, TypeAlias):
        return arg
    if allow_special_forms and arg in (ClassVar, Final):
        return arg
    if isinstance(arg, _SpecialForm) or arg is Unpack or arg in (Generic,):
        raise TypeError(f"Plain {arg} is not valid as type argument")
    if type(arg) is tuple:
        raise TypeError(f"{msg} Got {arg!r:.100}.")
    return arg


def _is_param_expr(arg):
    return arg is ... or isinstance(arg, (tuple, list, ParamSpec, _ConcatenateGenericAlias))

def _unpack_args(*args):
    newargs = []
    for arg in args:
        subargs = getattr(arg, '__typing_unpacked_tuple_args__', None)
        if subargs is not None and not (subargs and subargs[-1] is ...):
            newargs.extend(subargs)
        else:
            newargs.append(arg)
    return newargs


def _typevartuple_prepare_subst(self, alias, args):
    params = alias.__parameters__
    typevartuple_index = params.index(self)
    for param in params[typevartuple_index + 1:]:
        if isinstance(param, TypeVarTuple):
            raise TypeError(f"More than one TypeVarTuple parameter in {alias}")

    alen = len(args)
    plen = len(params)
    left = typevartuple_index
    right = plen - typevartuple_index - 1
    var_tuple_index = None
    fillarg = None
    for k, arg in enumerate(args):
        if not isinstance(arg, type):
            subargs = getattr(arg, '__typing_unpacked_tuple_args__', None)
            if subargs and len(subargs) == 2 and subargs[-1] is ...:
                if var_tuple_index is not None:
                    raise TypeError("More than one unpacked arbitrary-length tuple argument")
                var_tuple_index = k
                fillarg = subargs[0]
    if var_tuple_index is not None:
        left = min(left, var_tuple_index)
        right = min(right, alen - var_tuple_index - 1)
    elif left + right > alen:
        raise TypeError(f"Too few arguments for {alias};"
                        f" actual {alen}, expected at least {plen-1}")
    if left == alen - right and self.has_default():
        replacement = _unpack_args(self.__default__)
    else:
        replacement = args[left: alen - right]

    return (
        *args[:left],
        *([fillarg]*(typevartuple_index - left)),
        replacement,
        *([fillarg]*(plen - right - left - typevartuple_index - 1)),
        *args[alen - right:],
    )


def _paramspec_subst(self, arg):
    if isinstance(arg, (list, tuple)):
        arg = tuple(_type_check(a, "Expected a type.") for a in arg)
    elif not _is_param_expr(arg):
        raise TypeError(f"Expected a list of types, an ellipsis, "
                        f"ParamSpec, or Concatenate. Got {arg}")
    return arg


def _paramspec_prepare_subst(self, alias, args):
    params = alias.__parameters__
    i = params.index(self)
    if i == len(args) and self.has_default():
        args = (*args, self.__default__)
    if i >= len(args):
        raise TypeError(f"Too few arguments for {alias}")
    # Special case where Z[[int, str, bool]] == Z[int, str, bool] in PEP 612.
    if len(params) == 1 and not _is_param_expr(args[0]):
        assert i == 0
        args = (args,)
    # Convert lists to tuples to help other libraries cache the results.
    elif isinstance(args[i], list):
        args = (*args[:i], tuple(args[i]), *args[i+1:])
    return args


class Generic:
    __slots__ = ()
    def __class_getitem__(cls, args):
        return _generic_class_getitem(cls, args)
    def __init_subclass__(cls, *args, **kwargs):
        _generic_init_subclass(cls, *args, **kwargs)

def _is_typevar_like(x):
    return isinstance(x, (TypeVar, ParamSpec)) or _is_unpacked_typevartuple(x)

def _is_unpacked_typevartuple(x):
    return not isinstance(x, type) and getattr(x, '__typing_is_unpacked_typevartuple__', False) is True

def _type_convert(arg, module=None, *, allow_special_forms=False, owner=None):
    """For converting None to type(None), and strings to ForwardRef."""
    if arg is None:
        return type(None)
    if isinstance(arg, str):
        return _make_forward_ref(arg, module=module, is_class=allow_special_forms, owner=owner)
    return arg


def _generic_alias_mro_entries(alias, bases):
    if isinstance(alias.__origin__, _SpecialForm):
        raise TypeError(f"Cannot subclass {alias!r}")
    if alias._name:
        return _BaseGenericAlias.__mro_entries__(alias, bases)
    if alias.__origin__ is Generic:
        i = bases.index(alias)
        for base in bases[i+1:]:
            if isinstance(base, _GenericAlias) and base is not alias:
                return ()
    return (alias.__origin__,)

_CompilerGeneric = Generic

def _make_generic_base(params):
    return _GenericAlias(_CompilerGeneric, tuple(Unpack[param] if isinstance(param, TypeVarTuple) else param for param in params))

def _collect_type_parameters(args, *, enforce_default_ordering: bool = True):
    """Collect all type parameters in args
    in order of first appearance (lexicographic order).

    For example::

        >>> P = ParamSpec('P')
        >>> T = TypeVar('T')
        >>> _collect_type_parameters((T, Callable[P, T]))
        (~T, ~P)
    """
    # required type parameter cannot appear after parameter with default
    default_encountered = False
    # or after TypeVarTuple
    type_var_tuple_encountered = False
    parameters = []
    for t in args:
        if isinstance(t, type):
            # We don't want __parameters__ descriptor of a bare Python class.
            pass
        elif isinstance(t, tuple):
            # `t` might be a tuple, when `ParamSpec` is substituted with
            # `[T, int]`, or `[int, *Ts]`, etc.
            for x in t:
                for collected in _collect_type_parameters([x]):
                    if collected not in parameters:
                        parameters.append(collected)
        elif hasattr(t, '__typing_subst__'):
            if t not in parameters:
                if enforce_default_ordering:
                    if type_var_tuple_encountered and t.has_default():
                        raise TypeError('Type parameter with a default'
                                        ' follows TypeVarTuple')

                    if t.has_default():
                        default_encountered = True
                    elif default_encountered:
                        raise TypeError(f'Type parameter {t!r} without a default'
                                        ' follows type parameter with a default')

                parameters.append(t)
        else:
            if _is_unpacked_typevartuple(t):
                type_var_tuple_encountered = True
            for x in getattr(t, '__parameters__', ()):
                if x not in parameters:
                    parameters.append(x)
    return tuple(parameters)


def _check_generic_specialization(cls, arguments):
    """Check correct count for parameters of a generic cls (internal helper).

    This gives a nice error message in case of count mismatch.
    """
    expected_len = len(cls.__parameters__)
    if not expected_len:
        raise TypeError(f"{cls} is not a generic class")
    actual_len = len(arguments)
    if actual_len != expected_len:
        # deal with defaults
        if actual_len < expected_len:
            # If the parameter at index `actual_len` in the parameters list
            # has a default, then all parameters after it must also have
            # one, because we validated as much in _collect_type_parameters().
            # That means that no error needs to be raised here, despite
            # the number of arguments being passed not matching the number
            # of parameters: all parameters that aren't explicitly
            # specialized in this call are parameters with default values.
            if cls.__parameters__[actual_len].has_default():
                return

            expected_len -= sum(p.has_default() for p in cls.__parameters__)
            expect_val = f"at least {expected_len}"
        else:
            expect_val = expected_len

        raise TypeError(f"Too {'many' if actual_len > expected_len else 'few'} arguments"
                        f" for {cls}; actual {actual_len}, expected {expect_val}")


@_tp_cache
def _generic_class_getitem(cls, args):
    """Parameterizes a generic class.

    At least, parameterizing a generic class is the *main* thing this method
    does. For example, for some generic class `Foo`, this is called when we
    do `Foo[int]` - there, with `cls=Foo` and `args=int`.

    However, note that this method is also called when defining generic
    classes in the first place with `class Foo(Generic[T]): ...`.
    """
    if not isinstance(args, tuple):
        args = (args,)

    args = tuple(_type_convert(p) for p in args)
    is_generic_or_protocol = cls is Generic

    if is_generic_or_protocol:
        # Generic and Protocol can only be subscripted with unique type variables.
        if not args:
            raise TypeError(
                f"Parameter list to {cls.__qualname__}[...] cannot be empty"
            )
        if not all(_is_typevar_like(p) for p in args):
            raise TypeError(
                f"Parameters to {cls.__name__}[...] must all be type variables "
                f"or parameter specification variables.")
        if len(set(args)) != len(args):
            raise TypeError(
                f"Parameters to {cls.__name__}[...] must all be unique")
    else:
        # Subscripting a regular Generic subclass.
        try:
            parameters = cls.__parameters__
        except AttributeError as e:
            init_subclass = getattr(cls, '__init_subclass__', None)
            if init_subclass not in {None, Generic.__init_subclass__}:
                e.add_note(
                    f"Note: this exception may have been caused by "
                    f"{init_subclass.__qualname__!r} (or the "
                    f"'__init_subclass__' method on a superclass) not "
                    f"calling 'super().__init_subclass__()'"
                )
            raise
        for param in parameters:
            prepare = getattr(param, '__typing_prepare_subst__', None)
            if prepare is not None:
                args = prepare(cls, args)
        _check_generic_specialization(cls, args)

        new_args = []
        for param, new_arg in zip(parameters, args):
            if isinstance(param, TypeVarTuple):
                new_args.extend(new_arg)
            else:
                new_args.append(new_arg)
        args = tuple(new_args)

    return _GenericAlias(cls, args)


def _generic_init_subclass(cls, *args, **kwargs):
    super(Generic, cls).__init_subclass__(*args, **kwargs)
    tvars = []
    if '__orig_bases__' in cls.__dict__:
        error = Generic in cls.__orig_bases__
    else:
        error = (Generic in cls.__bases__ and
                    cls.__name__ != 'Protocol')
    if error:
        raise TypeError("Cannot inherit from plain Generic")
    if '__orig_bases__' in cls.__dict__:
        tvars = _collect_type_parameters(cls.__orig_bases__)
        # Look for Generic[T1, ..., Tn].
        # If found, tvars must be a subset of it.
        # If not found, tvars is it.
        # Also check for and reject plain Generic,
        # and reject multiple Generic[...].
        gvars = None
        for base in cls.__orig_bases__:
            if (isinstance(base, _GenericAlias) and
                    base.__origin__ is Generic):
                if gvars is not None:
                    raise TypeError(
                        "Cannot inherit from Generic[...] multiple times.")
                gvars = base.__parameters__
        if gvars is not None:
            tvarset = set(tvars)
            gvarset = set(gvars)
            if not tvarset <= gvarset:
                s_vars = ', '.join(str(t) for t in tvars if t not in gvarset)
                s_args = ', '.join(str(g) for g in gvars)
                raise TypeError(f"Some type variables ({s_vars}) are"
                                f" not listed in Generic[{s_args}]")
            tvars = gvars
    cls.__parameters__ = tuple(tvars)


def _type_repr(value):
    if isinstance(value, tuple):
        return '[' + ', '.join(_type_repr(arg) for arg in value) + ']'
    # CPython typing uses annotationlib's Python formatter, distinct from
    # the native generic-alias formatter (notably for NoneType).
    if isinstance(value, (type, types.FunctionType, types.BuiltinFunctionType)):
        if value.__module__ == "builtins":
            return value.__qualname__
        return f"{value.__module__}.{value.__qualname__}"
    if value is ...:
        return "..."
    return repr(value)

class _BaseGenericAlias:
    def __init__(self, origin, *, inst=True, name=None):
        self._inst = inst
        self._name = name
        self.__origin__ = origin
        self.__slots__ = None

    def __init_subclass__(cls, *, _root=False):
        if not _root:
            raise TypeError("Cannot subclass special typing classes")

    def __mro_entries__(self, bases):
        res = []
        if self.__origin__ not in bases:
            res.append(self.__origin__)

        # Check if any base that occurs after us in `bases` is either itself a
        # subclass of Generic, or something which will add a subclass of Generic
        # to `__bases__` via its `__mro_entries__`. If not, add Generic
        # ourselves. The goal is to ensure that Generic (or a subclass) will
        # appear exactly once in the final bases tuple. If we let it appear
        # multiple times, we risk "can't form a consistent MRO" errors.
        i = bases.index(self)
        for b in bases[i+1:]:
            if isinstance(b, _BaseGenericAlias):
                break
            if not isinstance(b, type):
                meth = getattr(b, "__mro_entries__", None)
                new_bases = meth(bases) if meth else None
                if (
                    isinstance(new_bases, tuple) and
                    any(
                        isinstance(b2, type) and issubclass(b2, Generic)
                        for b2 in new_bases
                    )
                ):
                    break
            elif issubclass(b, Generic):
                break
        else:
            res.append(Generic)
        return tuple(res)


    def __getattr__(self, attr):
        if attr in {'__name__', '__qualname__'}:
            return self._name or self.__origin__.__name__
        if '__origin__' in self.__dict__ and not (attr.startswith('__') and attr.endswith('__')):
            return getattr(self.__origin__, attr)
        raise AttributeError(attr)

    def __setattr__(self, attr, value):
        if (attr.startswith('__') and attr.endswith('__')) or attr in {'_name', '_inst', '_nparams', '_defaults'}:
            super().__setattr__(attr, value)
        else:
            setattr(self.__origin__, attr, value)

    def __call__(self, *args, **kwargs):
        if not self._inst:
            raise TypeError(f"Type {self._name} cannot be instantiated; use {self.__origin__.__name__}() instead")
        result = self.__origin__(*args, **kwargs)
        try:
            result.__orig_class__ = self
        except Exception:
            pass
        return result

    def __instancecheck__(self, obj):
        return self.__subclasscheck__(type(obj))

    def __subclasscheck__(self, cls):
        raise TypeError("Subscripted generics cannot be used with class and instance checks")

class _GenericAlias(_BaseGenericAlias, _root=True):
    def __init__(self, origin, args, *, inst=True, name=None):
        super().__init__(origin, inst=inst, name=name)
        if not isinstance(args, tuple):
            args = (args,)
        self.__args__ = args
        self.__parameters__ = _collect_type_parameters(args, enforce_default_ordering=origin is Generic)
        if not name:
            self.__module__ = origin.__module__

    @_tp_cache
    def __getitem__(self, args):
        if self.__origin__ is Generic:
            raise TypeError(f"Cannot subscript already-subscripted {self}")
        if not self.__parameters__:
            raise TypeError(f"{self} is not a generic class")
        if not isinstance(args, tuple):
            args = (args,)
        args = _unpack_args(*(_type_convert(p) for p in args))
        return self.copy_with(self._determine_new_args(args))

    def __repr__(self):
        name = 'typing.' + self._name if self._name else _type_repr(self.__origin__)
        if not self.__args__:
            return f"{name}[()]"
        return name + '[' + ', '.join(_type_repr(arg) for arg in self.__args__) + ']'

    def __mro_entries__(self, bases):
        return _generic_alias_mro_entries(self, bases)

    def __iter__(self):
        yield Unpack[self]

    def __eq__(self, other):
        if not isinstance(other, _GenericAlias):
            return NotImplemented
        return (self.__origin__ == other.__origin__
                and self.__args__ == other.__args__)


    def __hash__(self):
        return hash((self.__origin__, self.__args__))


    def __or__(self, right):
        return Union[self, right]


    def __ror__(self, left):
        return Union[left, self]


    def _determine_new_args(self, args):
        """Determines new __args__ for __getitem__.

        For example, suppose we had:
          T1 = TypeVar('T1')
          T2 = TypeVar('T2')
          class A(Generic[T1, T2]): pass
          T3 = TypeVar('T3')
          B = A[int, T3]
          C = B[str]
        `B.__args__` is `(int, T3)`, so `C.__args__` should be `(int, str)`.
        Unfortunately, this is harder than it looks, because if `T3` is
        anything more exotic than a plain `TypeVar`, we need to consider
        edge cases.
        """
        params = self.__parameters__
        # In the example above, this would be {T3: str}
        for param in params:
            prepare = getattr(param, '__typing_prepare_subst__', None)
            if prepare is not None:
                args = prepare(self, args)
        alen = len(args)
        plen = len(params)
        if alen != plen:
            raise TypeError(f"Too {'many' if alen > plen else 'few'} arguments for {self};"
                            f" actual {alen}, expected {plen}")
        new_arg_by_param = dict(zip(params, args))
        return tuple(self._make_substitution(self.__args__, new_arg_by_param))


    def _make_substitution(self, args, new_arg_by_param):
        """Create a list of new type arguments."""
        new_args = []
        for old_arg in args:
            if isinstance(old_arg, type):
                new_args.append(old_arg)
                continue

            substfunc = getattr(old_arg, '__typing_subst__', None)
            if substfunc:
                new_arg = substfunc(new_arg_by_param[old_arg])
            else:
                subparams = getattr(old_arg, '__parameters__', ())
                if not subparams:
                    new_arg = old_arg
                else:
                    subargs = []
                    for x in subparams:
                        if isinstance(x, TypeVarTuple):
                            subargs.extend(new_arg_by_param[x])
                        else:
                            subargs.append(new_arg_by_param[x])
                    new_arg = old_arg[tuple(subargs)]

            if self.__origin__ == collections.abc.Callable and isinstance(new_arg, tuple):
                # CPython flattens Callable parameter expressions into __args__.
                new_args.extend(new_arg)
            elif _is_unpacked_typevartuple(old_arg):
                # Consider the following `_GenericAlias`, `B`:
                #   class A(Generic[*Ts]): ...
                #   B = A[T, *Ts]
                # If we then do:
                #   B[float, int, str]
                # The `new_arg` corresponding to `T` will be `float`, and the
                # `new_arg` corresponding to `*Ts` will be `(int, str)`. We
                # should join all these types together in a flat list
                # `(float, int, str)` - so again, we should `extend`.
                new_args.extend(new_arg)
            elif isinstance(old_arg, tuple):
                # Corner case:
                #    P = ParamSpec('P')
                #    T = TypeVar('T')
                #    class Base(Generic[P]): ...
                # Can be substituted like this:
                #    X = Base[[int, T]]
                # In this case, `old_arg` will be a tuple:
                new_args.append(
                    tuple(self._make_substitution(old_arg, new_arg_by_param)),
                )
            else:
                new_args.append(new_arg)
        return new_args


    def copy_with(self, args):
        return self.__class__(self.__origin__, args, name=self._name, inst=self._inst)


class _ConcatenateGenericAlias(_GenericAlias, _root=True):
    def copy_with(self, params):
        if isinstance(params[-1], (list, tuple)):
            return (*params[:-1], *params[-1])
        if isinstance(params[-1], _ConcatenateGenericAlias):
            params = (*params[:-1], *params[-1].__args__)
        return super().copy_with(params)



@_SpecialForm
def Concatenate(self, parameters):
    """Special form for annotating higher-order functions.

    ``Concatenate`` can be used in conjunction with ``ParamSpec`` and
    ``Callable`` to represent a higher-order function which adds, removes or
    transforms the parameters of a callable.

    For example::

        Callable[Concatenate[int, P], int]

    See PEP 612 for detailed information.
    """
    if parameters == ():
        raise TypeError("Cannot take a Concatenate of no types.")
    if not isinstance(parameters, tuple):
        parameters = (parameters,)
    if not (parameters[-1] is ... or isinstance(parameters[-1], ParamSpec)):
        raise TypeError("The last parameter to Concatenate should be a "
                        "ParamSpec variable or ellipsis.")
    msg = "Concatenate[arg, ...]: each arg must be a type."
    parameters = (*(_type_check(p, msg) for p in parameters[:-1]), parameters[-1])
    return _ConcatenateGenericAlias(self, parameters)




class _AnyMeta(type):
    def __instancecheck__(self, obj):
        if self is Any:
            raise TypeError("typing.Any cannot be used with isinstance()")
        return super().__instancecheck__(obj)

    def __repr__(self):
        if self is Any:
            return "typing.Any"
        return super().__repr__()  # respect to subclasses


class Any(metaclass=_AnyMeta):
    """Special type indicating an unconstrained type.

    - Any is assignable to every type.
    - Any assumed to have all methods and attributes.
    - All values are assignable to Any.

    Note that all the above statements are true from the point of view of
    static type checkers. At runtime, Any cannot be used with instance
    checks.
    """

    def __new__(cls, *args, **kwargs):
        if cls is Any:
            raise TypeError("Any cannot be instantiated")
        return super().__new__(cls)


@_SpecialForm
def NoReturn(self, parameters):
    """Special type indicating functions that never return.

    Example::

        from typing import NoReturn

        def stop() -> NoReturn:
            raise Exception('no way')

    NoReturn can also be used as a bottom type, a type that
    has no values. Starting in Python 3.11, the Never type should
    be used for this concept instead. Type checkers should treat the two
    equivalently.
    """
    raise TypeError(f"{self} is not subscriptable")


def _should_unflatten_callable_args(typ, args):
    """Internal helper for munging collections.abc.Callable's __args__.

    The canonical representation for a Callable's __args__ flattens the
    argument types, see https://github.com/python/cpython/issues/86361.

    For example::

        >>> import collections.abc
        >>> P = ParamSpec('P')
        >>> collections.abc.Callable[[int, int], str].__args__ == (int, int, str)
        True
        >>> collections.abc.Callable[P, str].__args__ == (P, str)
        True

    As a result, if we need to reconstruct the Callable from its __args__,
    we need to unflatten it.
    """
    return (
        typ.__origin__ is collections.abc.Callable
        and not (len(args) == 2 and _is_param_expr(args[0]))
    )


class _SpecialGenericAlias(_NotIterable, _BaseGenericAlias, _root=True):
    def __init__(self, origin, nparams, *, inst=True, name=None, defaults=()):
        if name is None:
            name = origin.__name__
        super().__init__(origin, inst=inst, name=name)
        self._nparams = nparams
        self._defaults = defaults
        if origin.__module__ == 'builtins':
            self.__doc__ = f'Deprecated alias to {origin.__qualname__}.'
        else:
            self.__doc__ = f'Deprecated alias to {origin.__module__}.{origin.__qualname__}.'

    @_tp_cache
    def __getitem__(self, params):
        if not isinstance(params, tuple):
            params = (params,)
        msg = "Parameters to generic types must be types."
        params = tuple(_type_check(p, msg) for p in params)
        if (self._defaults
            and len(params) < self._nparams
            and len(params) + len(self._defaults) >= self._nparams
        ):
            params = (*params, *self._defaults[len(params) - self._nparams:])
        actual_len = len(params)

        if actual_len != self._nparams:
            if self._defaults:
                expected = f"at least {self._nparams - len(self._defaults)}"
            else:
                expected = str(self._nparams)
            if not self._nparams:
                raise TypeError(f"{self} is not a generic class")
            raise TypeError(f"Too {'many' if actual_len > self._nparams else 'few'} arguments for {self};"
                            f" actual {actual_len}, expected {expected}")
        return self.copy_with(params)

    def copy_with(self, params):
        return _GenericAlias(self.__origin__, params,
                             name=self._name, inst=self._inst)

    def __repr__(self):
        return 'typing.' + self._name

    def __subclasscheck__(self, cls):
        if isinstance(cls, _SpecialGenericAlias):
            return issubclass(cls.__origin__, self.__origin__)
        if not isinstance(cls, _GenericAlias):
            return issubclass(cls, self.__origin__)
        return super().__subclasscheck__(cls)

    def __reduce__(self):
        return self._name

    def __or__(self, right):
        return Union[self, right]

    def __ror__(self, left):
        return Union[left, self]


class _CallableGenericAlias(_NotIterable, _GenericAlias, _root=True):
    def __repr__(self):
        assert self._name == 'Callable'
        args = self.__args__
        if len(args) == 2 and _is_param_expr(args[0]):
            return super().__repr__()
        return (f'typing.Callable'
                f'[[{", ".join([_type_repr(a) for a in args[:-1]])}], '
                f'{_type_repr(args[-1])}]')

    def __reduce__(self):
        args = self.__args__
        if not (len(args) == 2 and _is_param_expr(args[0])):
            args = list(args[:-1]), args[-1]
        return operator.getitem, (Callable, args)


class _CallableType(_SpecialGenericAlias, _root=True):
    def copy_with(self, params):
        return _CallableGenericAlias(self.__origin__, params,
                                     name=self._name, inst=self._inst)

    def __getitem__(self, params):
        if not isinstance(params, tuple) or len(params) != 2:
            raise TypeError("Callable must be used as "
                            "Callable[[arg, ...], result].")
        args, result = params
        # This relaxes what args can be on purpose to allow things like
        # PEP 612 ParamSpec.  Responsibility for whether a user is using
        # Callable[...] properly is deferred to static type checkers.
        if isinstance(args, list):
            params = (tuple(args), result)
        else:
            params = (args, result)
        return self.__getitem_inner__(params)

    @_tp_cache
    def __getitem_inner__(self, params):
        args, result = params
        msg = "Callable[args, result]: result must be a type."
        result = _type_check(result, msg)
        if args is Ellipsis:
            return self.copy_with((Ellipsis, result))
        if not isinstance(args, tuple):
            args = (args,)
        args = tuple(_type_convert(arg) for arg in args)
        params = args + (result,)
        return self.copy_with(params)


Callable = _CallableType(collections.abc.Callable, 2)
List = _SpecialGenericAlias(list, 1, inst=False, name="List")
Set = _SpecialGenericAlias(set, 1, inst=False, name="Set")
Type = _SpecialGenericAlias(type, 1, inst=False, name="Type")
Deque = _SpecialGenericAlias(collections.deque, 1, name="Deque")


class _TupleType(_SpecialGenericAlias, _root=True):
    @_tp_cache
    def __getitem__(self, params):
        if not isinstance(params, tuple):
            params = (params,)
        if len(params) >= 2 and params[-1] is ...:
            msg = "Tuple[t, ...]: t must be a type."
            params = tuple(_type_check(p, msg) for p in params[:-1])
            return self.copy_with((*params, Ellipsis))
        msg = "Tuple[t0, t1, ...]: each t must be a type."
        params = tuple(_type_check(p, msg) for p in params)
        return self.copy_with(params)


Tuple = _TupleType(tuple, -1, inst=False, name="Tuple")


# Forward-reference and type-hint evaluation from CPython 3.14 at 18ef0f0cb52.
def _make_forward_ref(code, *, parent_fwdref=None, **kwargs):
    if parent_fwdref is not None:
        if parent_fwdref.__forward_module__ is not None:
            kwargs['module'] = parent_fwdref.__forward_module__
        if parent_fwdref.__owner__ is not None:
            kwargs['owner'] = parent_fwdref.__owner__
    forward_ref = _lazy_annotationlib.ForwardRef(code, **kwargs)
    # For compatibility, eagerly compile the forwardref's code.
    forward_ref.__forward_code__
    return forward_ref


def evaluate_forward_ref(
    forward_ref,
    *,
    owner=None,
    globals=None,
    locals=None,
    type_params=None,
    format=None,
    _recursive_guard=frozenset(),
):
    """Evaluate a forward reference as a type hint.

    This is similar to calling the ForwardRef.evaluate() method,
    but unlike that method, evaluate_forward_ref() also
    recursively evaluates forward references nested within the type hint.

    *forward_ref* must be an instance of ForwardRef. *owner*, if given,
    should be the object that holds the annotations that the forward reference
    derived from, such as a module, class object, or function. It is used to
    infer the namespaces to use for looking up names. *globals* and *locals*
    can also be explicitly given to provide the global and local namespaces.
    *type_params* is a tuple of type parameters that are in scope when
    evaluating the forward reference. This parameter should be provided (though
    it may be an empty tuple) if *owner* is not given and the forward reference
    does not already have an owner set. *format* specifies the format of the
    annotation and is a member of the annotationlib.Format enum, defaulting to
    VALUE.

    """
    if format == _lazy_annotationlib.Format.STRING:
        return forward_ref.__resolved_str__
    if forward_ref.__forward_arg__ in _recursive_guard:
        return forward_ref

    if format is None:
        format = _lazy_annotationlib.Format.VALUE
    value = forward_ref.evaluate(globals=globals, locals=locals,
                                 type_params=type_params, owner=owner, format=format)

    if (isinstance(value, _lazy_annotationlib.ForwardRef)
            and format == _lazy_annotationlib.Format.FORWARDREF):
        return value

    if isinstance(value, str):
        value = _make_forward_ref(value, module=forward_ref.__forward_module__,
                                  owner=owner or forward_ref.__owner__,
                                  is_argument=forward_ref.__forward_is_argument__,
                                  is_class=forward_ref.__forward_is_class__)
    if owner is None:
        owner = forward_ref.__owner__
    return _eval_type(
        value,
        globals,
        locals,
        type_params,
        recursive_guard=_recursive_guard | {forward_ref.__forward_arg__},
        format=format,
        owner=owner,
        parent_fwdref=forward_ref,
    )


def _eval_type(t, globalns, localns, type_params=(), *, recursive_guard=frozenset(),
               format=None, owner=None, parent_fwdref=None, prefer_fwd_module=False):
    """Evaluate all forward references in the given type t.

    For use of globalns and localns see the docstring for get_type_hints().
    recursive_guard is used to prevent infinite recursion with a recursive
    ForwardRef.
    """
    if isinstance(t, _lazy_annotationlib.ForwardRef):
        # If the forward_ref has __forward_module__ set, evaluate() infers the globals
        # from the module, and it will probably pick better than the globals we have here.
        # We do this only for calls from get_type_hints() (which opts in through the
        # prefer_fwd_module flag), so that the default behavior remains more straightforward.
        if prefer_fwd_module and t.__forward_module__ is not None:
            globalns = None
            # If there are type params on the owner, we need to add them back, because
            # annotationlib won't.
            if owner_type_params := getattr(owner, "__type_params__", None):
                globalns = getattr(
                    sys.modules.get(t.__forward_module__, None), "__dict__", None
                )
                if globalns is not None:
                    globalns = dict(globalns)
                    for type_param in owner_type_params:
                        globalns[type_param.__name__] = type_param
        return evaluate_forward_ref(t, globals=globalns, locals=localns,
                                    type_params=type_params, owner=owner,
                                    _recursive_guard=recursive_guard, format=format)
    if isinstance(t, (_GenericAlias, GenericAlias, Union, _UnpackGenericAlias)):
        if isinstance(t, GenericAlias):
            args = tuple(
                _make_forward_ref(arg, parent_fwdref=parent_fwdref) if isinstance(arg, str) else arg
                for arg in t.__args__
            )
            is_unpacked = t.__unpacked__
            if _should_unflatten_callable_args(t, args):
                t = t.__origin__[(args[:-1], args[-1])]
            else:
                t = t.__origin__[args]
            if is_unpacked:
                t = Unpack[t]

        ev_args = tuple(
            _eval_type(
                a, globalns, localns, type_params, recursive_guard=recursive_guard,
                format=format, owner=owner, prefer_fwd_module=prefer_fwd_module,
            )
            for a in t.__args__
        )
        if ev_args == t.__args__:
            return t
        if isinstance(t, _UnpackGenericAlias):
            return Unpack[ev_args[0]]
        if isinstance(t, GenericAlias):
            return GenericAlias(t.__origin__, ev_args)
        if isinstance(t, Union):
            return functools.reduce(operator.or_, ev_args)
        else:
            return t.copy_with(ev_args)
    return t


def get_type_hints(obj, globalns=None, localns=None, include_extras=False,
                   *, format=None):
    """Return type hints for an object.

    This is often the same as annotationlib.get_annotations(obj) or obj.__annotations__,
    but it handles forward references encoded as string literals and recursively replaces all
    'Annotated[T, ...]' with 'T' (unless 'include_extras=True').

    The argument may be a module, class, method, or function. The annotations
    are returned as a dictionary. For classes, annotations include also
    inherited members.

    TypeError is raised if the argument is not of a type that can contain
    annotations, and an empty dictionary is returned if no annotations are
    present.

    BEWARE -- the behavior of globalns and localns is counterintuitive
    (unless you are familiar with how eval() and exec() work).  The
    search order is locals first, then globals.

    - If no dict arguments are passed, an attempt is made to use the
      globals from obj (or the respective module's globals for classes),
      and these are also used as the locals.  If the object does not appear
      to have globals, an empty dictionary is used.  For classes, the search
      order is globals first then locals.

    - If one dict argument is passed, it is used for both globals and
      locals.

    - If two dict arguments are passed, they specify globals and
      locals, respectively.
    """
    if getattr(obj, '__no_type_check__', None):
        return {}
    Format = _lazy_annotationlib.Format
    if format is None:
        format = Format.VALUE
    # Classes require a special treatment.
    if isinstance(obj, type):
        hints = {}
        for base in reversed(obj.__mro__):
            ann = _lazy_annotationlib.get_annotations(base, format=format)
            if format == Format.STRING:
                hints.update(ann)
                continue
            if globalns is None:
                base_globals = getattr(sys.modules.get(base.__module__, None), '__dict__', {})
            else:
                base_globals = globalns
            base_locals = dict(vars(base)) if localns is None else localns
            if localns is None and globalns is None:
                # This is surprising, but required.  Before Python 3.10,
                # get_type_hints only evaluated the globalns of
                # a class.  To maintain backwards compatibility, we reverse
                # the globalns and localns order so that eval() looks into
                # *base_globals* first rather than *base_locals*.
                # This only affects ForwardRefs.
                base_globals, base_locals = base_locals, base_globals
            type_params = base.__type_params__
            base_globals, base_locals = _add_type_params_to_scope(
                type_params, base_globals, base_locals, True)
            for name, value in ann.items():
                if isinstance(value, str):
                    value = _make_forward_ref(value, is_argument=False, is_class=True)
                value = _eval_type(value, base_globals, base_locals, (),
                                   format=format, owner=obj, prefer_fwd_module=True)
                if value is None:
                    value = type(None)
                hints[name] = value
        if include_extras or format == Format.STRING:
            return hints
        else:
            return {k: _strip_annotations(t) for k, t in hints.items()}

    hints = _lazy_annotationlib.get_annotations(obj, format=format)
    if (
        not hints
        and not isinstance(obj, types.ModuleType)
        and not callable(obj)
        and not hasattr(obj, '__annotations__')
        and not hasattr(obj, '__annotate__')
    ):
        raise TypeError(f"{obj!r} is not a module, class, or callable.")
    if format == Format.STRING:
        return hints

    if globalns is None:
        if isinstance(obj, types.ModuleType):
            globalns = obj.__dict__
        else:
            nsobj = obj
            # Find globalns for the unwrapped object.
            seen = {id(nsobj)}
            while hasattr(nsobj, '__wrapped__'):
                nsobj = nsobj.__wrapped__
                if id(nsobj) in seen:
                    raise ValueError(f'wrapper loop when unwrapping {obj!r}')
                seen.add(id(nsobj))
            globalns = getattr(nsobj, '__globals__', {})
        if localns is None:
            localns = globalns
    elif localns is None:
        localns = globalns
    type_params = getattr(obj, "__type_params__", ())
    globalns, localns = _add_type_params_to_scope(type_params, globalns, localns, False)
    for name, value in hints.items():
        if isinstance(value, str):
            # class-level forward refs were handled above, this must be either
            # a module-level annotation or a function argument annotation
            value = _make_forward_ref(
                value,
                is_argument=not isinstance(obj, types.ModuleType),
                is_class=False,
            )
        value = _eval_type(value, globalns, localns, (), format=format, owner=obj, prefer_fwd_module=True)
        if value is None:
            value = type(None)
        hints[name] = value
    return hints if include_extras else {k: _strip_annotations(t) for k, t in hints.items()}


def _add_type_params_to_scope(type_params, globalns, localns, is_class):
    if not type_params:
        return globalns, localns
    globalns = dict(globalns)
    localns = dict(localns)
    for param in type_params:
        if not is_class or param.__name__ not in globalns:
            globalns[param.__name__] = param
            localns.pop(param.__name__, None)
    return globalns, localns


def _strip_annotations(t):
    """Strip the annotations from a given type."""
    if isinstance(t, _AnnotatedAlias):
        return _strip_annotations(t.__origin__)
    if hasattr(t, "__origin__") and t.__origin__ in (Required, NotRequired, ReadOnly):
        return _strip_annotations(t.__args__[0])
    # CPython's Unpack alias is a Python _GenericAlias subclass; ours is native.
    if isinstance(t, _UnpackGenericAlias):
        stripped_arg = _strip_annotations(t.__args__[0])
        return t if stripped_arg == t.__args__[0] else Unpack[stripped_arg]
    if isinstance(t, _GenericAlias):
        stripped_args = tuple(_strip_annotations(a) for a in t.__args__)
        if stripped_args == t.__args__:
            return t
        return t.copy_with(stripped_args)
    if isinstance(t, GenericAlias):
        stripped_args = tuple(_strip_annotations(a) for a in t.__args__)
        if stripped_args == t.__args__:
            return t
        return GenericAlias(t.__origin__, stripped_args)
    if isinstance(t, Union):
        stripped_args = tuple(_strip_annotations(a) for a in t.__args__)
        if stripped_args == t.__args__:
            return t
        return functools.reduce(operator.or_, stripped_args)

    return t



def __getattr__(attr):
    # CPython lazily exports the annotationlib class under its historical name.
    if attr == "ForwardRef":
        obj = _lazy_annotationlib.ForwardRef
        globals()[attr] = obj
        return obj
    raise AttributeError(f"module {__name__!r} has no attribute {attr!r}")



def _typevar_subst(self, arg):
    msg = "Parameters to generic types must be types."
    arg = _type_check(arg, msg, is_argument=True)
    if ((isinstance(arg, (_GenericAlias, _UnpackGenericAlias)) and arg.__origin__ is Unpack) or
        (isinstance(arg, GenericAlias) and getattr(arg, '__unpacked__', False))):
        raise TypeError(f"{arg} is not valid as type argument")
    return arg


# Annotation qualifiers from CPython 3.14 at 18ef0f0cb52.
class _TypedCacheSpecialForm(_SpecialForm, _root=True):
    def __getitem__(self, parameters):
        if not isinstance(parameters, tuple):
            parameters = (parameters,)
        return self._getitem(self, *parameters)


def _deduplicate(params, *, unhashable_fallback=False):
    # Weed out strict duplicates, preserving the first of each occurrence.
    try:
        return dict.fromkeys(params)
    except TypeError:
        if not unhashable_fallback:
            raise
        # Happens for cases like `Annotated[dict, {'x': IntValidator()}]`
        new_unhashable = []
        for t in params:
            if t not in new_unhashable:
                new_unhashable.append(t)
        return new_unhashable


def _flatten_literal_params(parameters):
    """Internal helper for Literal creation: flatten Literals among parameters."""
    params = []
    for p in parameters:
        if isinstance(p, _LiteralGenericAlias):
            params.extend(p.__args__)
        else:
            params.append(p)
    return tuple(params)


def _value_and_type_iter(parameters):
    return ((p, type(p)) for p in parameters)


class _LiteralGenericAlias(_GenericAlias, _root=True):
    def __eq__(self, other):
        if not isinstance(other, _LiteralGenericAlias):
            return NotImplemented

        return set(_value_and_type_iter(self.__args__)) == set(_value_and_type_iter(other.__args__))

    def __hash__(self):
        return hash(frozenset(_value_and_type_iter(self.__args__)))


class _AnnotatedAlias(_NotIterable, _GenericAlias, _root=True):
    """Runtime representation of an annotated type.

    At its core 'Annotated[t, dec1, dec2, ...]' is an alias for the type 't'
    with extra metadata. The alias behaves like a normal typing alias.
    Instantiating is the same as instantiating the underlying type; binding
    it to types is also the same.

    The metadata itself is stored in a '__metadata__' attribute as a tuple.
    """

    def __init__(self, origin, metadata):
        if isinstance(origin, _AnnotatedAlias):
            metadata = origin.__metadata__ + metadata
            origin = origin.__origin__
        super().__init__(origin, origin, name='Annotated')
        self.__metadata__ = metadata

    def copy_with(self, params):
        assert len(params) == 1
        new_type = params[0]
        return _AnnotatedAlias(new_type, self.__metadata__)

    def __repr__(self):
        return "typing.Annotated[{}, {}]".format(
            _type_repr(self.__origin__),
            ", ".join(repr(a) for a in self.__metadata__)
        )

    def __reduce__(self):
        return operator.getitem, (
            Annotated, (self.__origin__,) + self.__metadata__
        )

    def __eq__(self, other):
        if not isinstance(other, _AnnotatedAlias):
            return NotImplemented
        return (self.__origin__ == other.__origin__
                and self.__metadata__ == other.__metadata__)

    def __hash__(self):
        return hash((self.__origin__, self.__metadata__))

    def __getattr__(self, attr):
        if attr in {'__name__', '__qualname__'}:
            return 'Annotated'
        return super().__getattr__(attr)

    def __mro_entries__(self, bases):
        return (self.__origin__,)


@_SpecialForm
def Never(self, parameters):
    """The bottom type, a type that has no members.

    This can be used to define a function that should never be
    called, or a function that never returns::

        from typing import Never

        def never_call_me(arg: Never) -> None:
            pass

        def int_or_str(arg: int | str) -> None:
            never_call_me(arg)  # type checker error
            match arg:
                case int():
                    print("It's an int")
                case str():
                    print("It's a str")
                case _:
                    never_call_me(arg)  # OK, arg is of type Never
    """
    raise TypeError(f"{self} is not subscriptable")


@_SpecialForm
def Self(self, parameters):
    """Used to spell the type of "self" in classes.

    Example::

        from typing import Self

        class Foo:
            def return_self(self) -> Self:
                ...
                return self

    This is especially useful for:
        - classmethods that are used as alternative constructors
        - annotating an `__enter__` method which returns self
    """
    raise TypeError(f"{self} is not subscriptable")


@_SpecialForm
def LiteralString(self, parameters):
    """Represents an arbitrary literal string.

    Example::

        from typing import LiteralString

        def run_query(sql: LiteralString) -> None:
            ...

        def caller(arbitrary_string: str, literal_string: LiteralString) -> None:
            run_query("SELECT * FROM students")  # OK
            run_query(literal_string)  # OK
            run_query("SELECT * FROM " + literal_string)  # OK
            run_query(arbitrary_string)  # type checker error
            run_query(  # type checker error
                f"SELECT * FROM students WHERE name = {arbitrary_string}"
            )

    Only string literals and other LiteralStrings are compatible
    with LiteralString. This provides a tool to help prevent
    security issues such as SQL injection.
    """
    raise TypeError(f"{self} is not subscriptable")


@_SpecialForm
def ClassVar(self, parameters):
    """Special type construct to mark class variables.

    An annotation wrapped in ClassVar indicates that a given
    attribute is intended to be used as a class variable and
    should not be set on instances of that class.

    Usage::

        class Starship:
            stats: ClassVar[dict[str, int]] = {} # class variable
            damage: int = 10                     # instance variable

    ClassVar accepts only types and cannot be further subscribed.

    Note that ClassVar is not a class itself, and cannot
    be used with isinstance() or issubclass().
    """
    item = _type_check(parameters, f'{self} accepts only single type.', allow_special_forms=True)
    return _GenericAlias(self, (item,))


@_SpecialForm
def Final(self, parameters):
    """Special typing construct to indicate final names to type checkers.

    A final name cannot be re-assigned or overridden in a subclass.

    For example::

        MAX_SIZE: Final = 9000
        MAX_SIZE += 1  # Error reported by type checker

        class Connection:
            TIMEOUT: Final[int] = 10

        class FastConnector(Connection):
            TIMEOUT = 1  # Error reported by type checker

    There is no runtime checking of these properties.
    """
    item = _type_check(parameters, f'{self} accepts only single type.', allow_special_forms=True)
    return _GenericAlias(self, (item,))


@_SpecialForm
def Optional(self, parameters):
    """Optional[X] is equivalent to X | None."""
    arg = _type_check(parameters, f"{self} requires a single type.")
    return Union[arg, type(None)]


@_TypedCacheSpecialForm
@_tp_cache(typed=True)
def Literal(self, *parameters):
    """Special typing form to define literal types (a.k.a. value types).

    This form can be used to indicate to type checkers that the corresponding
    variable or function parameter has a value equivalent to the provided
    literal (or one of several literals)::

        def validate_simple(data: Any) -> Literal[True]:  # always returns True
            ...

        MODE = Literal['r', 'rb', 'w', 'wb']
        def open_helper(file: str, mode: MODE) -> str:
            ...

        open_helper('/some/path', 'r')  # Passes type check
        open_helper('/other/path', 'typo')  # Error in type checker

    Literal[...] cannot be subclassed. At runtime, an arbitrary value
    is allowed as type argument to Literal[...], but type checkers may
    impose restrictions.
    """
    # There is no '_type_check' call because arguments to Literal[...] are
    # values, not types.
    parameters = _flatten_literal_params(parameters)
    value_and_type_parameters = list(_value_and_type_iter(parameters))
    deduplicated_parameters = tuple(
        p
        for p, _ in _deduplicate(
            value_and_type_parameters,
            unhashable_fallback=True,
        )
    )

    return _LiteralGenericAlias(self, deduplicated_parameters)


@_SpecialForm
def TypeAlias(self, parameters):
    """Special form for marking type aliases.

    TypeAlias can be used to indicate that an assignment should
    be recognized as a proper type alias definition by type
    checkers.

    For example::

        Predicate: TypeAlias = Callable[..., bool]

    It's invalid when used anywhere except as in the example above.
    """
    raise TypeError(f"{self} is not subscriptable")


@_SpecialForm
def TypeGuard(self, parameters):
    """Special typing construct for marking user-defined type predicate functions.

    ``TypeGuard`` can be used to annotate the return type of a user-defined
    type predicate function.  ``TypeGuard`` only accepts a single type argument.
    At runtime, functions marked this way should return a boolean.

    ``TypeGuard`` aims to benefit *type narrowing* -- a technique used by static
    type checkers to determine a more precise type of an expression within a
    program's code flow.  Usually type narrowing is done by analyzing
    conditional code flow and applying the narrowing to a block of code.  The
    conditional expression here is sometimes referred to as a "type predicate".

    Sometimes it would be convenient to use a user-defined boolean function
    as a type predicate.  Such a function should use ``TypeGuard[...]`` or
    ``TypeIs[...]`` as its return type to alert static type checkers to
    this intention. ``TypeGuard`` should be used over ``TypeIs`` when narrowing
    from an incompatible type (e.g., ``list[object]`` to ``list[int]``) or when
    the function does not return ``True`` for all instances of the narrowed type.

    Using  ``-> TypeGuard[NarrowedType]`` tells the static type checker that
    for a given function:

    1. The return value is a boolean.
    2. If the return value is ``True``, the type of its argument
       is ``NarrowedType``.

    For example::

         def is_str_list(val: list[object]) -> TypeGuard[list[str]]:
             '''Determines whether all objects in the list are strings'''
             return all(isinstance(x, str) for x in val)

         def func1(val: list[object]):
             if is_str_list(val):
                 # Type of ``val`` is narrowed to ``list[str]``.
                 print(" ".join(val))
             else:
                 # Type of ``val`` remains as ``list[object]``.
                 print("Not a list of strings!")

    Strict type narrowing is not enforced -- ``TypeB`` need not be a narrower
    form of ``TypeA`` (it can even be a wider form) and this may lead to
    type-unsafe results.  The main reason is to allow for things like
    narrowing ``list[object]`` to ``list[str]`` even though the latter is not
    a subtype of the former, since ``list`` is invariant.  The responsibility of
    writing type-safe type predicates is left to the user.

    ``TypeGuard`` also works with type variables.  For more information, see
    PEP 647 (User-Defined Type Guards).
    """
    item = _type_check(parameters, f'{self} accepts only single type.')
    return _GenericAlias(self, (item,))


@_SpecialForm
def TypeIs(self, parameters):
    """Special typing construct for marking user-defined type predicate functions.

    ``TypeIs`` can be used to annotate the return type of a user-defined
    type predicate function.  ``TypeIs`` only accepts a single type argument.
    At runtime, functions marked this way should return a boolean and accept
    at least one argument.

    ``TypeIs`` aims to benefit *type narrowing* -- a technique used by static
    type checkers to determine a more precise type of an expression within a
    program's code flow.  Usually type narrowing is done by analyzing
    conditional code flow and applying the narrowing to a block of code.  The
    conditional expression here is sometimes referred to as a "type predicate".

    Sometimes it would be convenient to use a user-defined boolean function
    as a type predicate.  Such a function should use ``TypeIs[...]`` or
    ``TypeGuard[...]`` as its return type to alert static type checkers to
    this intention.  ``TypeIs`` usually has more intuitive behavior than
    ``TypeGuard``, but it cannot be used when the input and output types
    are incompatible (e.g., ``list[object]`` to ``list[int]``) or when the
    function does not return ``True`` for all instances of the narrowed type.

    Using  ``-> TypeIs[NarrowedType]`` tells the static type checker that for
    a given function:

    1. The return value is a boolean.
    2. If the return value is ``True``, the type of its argument
       is the intersection of the argument's original type and
       ``NarrowedType``.
    3. If the return value is ``False``, the type of its argument
       is narrowed to exclude ``NarrowedType``.

    For example::

        from typing import assert_type, final, TypeIs

        class Parent: pass
        class Child(Parent): pass
        @final
        class Unrelated: pass

        def is_parent(val: object) -> TypeIs[Parent]:
            return isinstance(val, Parent)

        def run(arg: Child | Unrelated):
            if is_parent(arg):
                # Type of ``arg`` is narrowed to the intersection
                # of ``Parent`` and ``Child``, which is equivalent to
                # ``Child``.
                assert_type(arg, Child)
            else:
                # Type of ``arg`` is narrowed to exclude ``Parent``,
                # so only ``Unrelated`` is left.
                assert_type(arg, Unrelated)

    The type inside ``TypeIs`` must be consistent with the type of the
    function's argument; if it is not, static type checkers will raise
    an error.  An incorrectly written ``TypeIs`` function can lead to
    unsound behavior in the type system; it is the user's responsibility
    to write such functions in a type-safe manner.

    ``TypeIs`` also works with type variables.  For more information, see
    PEP 742 (Narrowing types with ``TypeIs``).
    """
    item = _type_check(parameters, f'{self} accepts only single type.')
    return _GenericAlias(self, (item,))


@_SpecialForm
def Required(self, parameters):
    """Special typing construct to mark a TypedDict key as required.

    This is mainly useful for total=False TypedDicts.

    For example::

        class Movie(TypedDict, total=False):
            title: Required[str]
            year: int

        m = Movie(
            title='The Matrix',  # type checker error if key is omitted
            year=1999,
        )

    There is no runtime checking that a required key is actually provided
    when instantiating a related TypedDict.
    """
    item = _type_check(parameters, f'{self._name} accepts only a single type.')
    return _GenericAlias(self, (item,))


@_SpecialForm
def NotRequired(self, parameters):
    """Special typing construct to mark a TypedDict key as potentially missing.

    For example::

        class Movie(TypedDict):
            title: str
            year: NotRequired[int]

        m = Movie(
            title='The Matrix',  # type checker error if key is omitted
            year=1999,
        )
    """
    item = _type_check(parameters, f'{self._name} accepts only a single type.')
    return _GenericAlias(self, (item,))


@_SpecialForm
def ReadOnly(self, parameters):
    """A special typing construct to mark an item of a TypedDict as read-only.

    For example::

        class Movie(TypedDict):
            title: ReadOnly[str]
            year: int

        def mutate_movie(m: Movie) -> None:
            m["year"] = 1992  # allowed
            m["title"] = "The Matrix"  # type checker error

    There is no runtime checking for this property.
    """
    item = _type_check(parameters, f'{self._name} accepts only a single type.')
    return _GenericAlias(self, (item,))


@_TypedCacheSpecialForm
@_tp_cache(typed=True)
def Annotated(self, *params):
    """Add context-specific metadata to a type.

    Example: Annotated[int, runtime_check.Unsigned] indicates to the
    hypothetical runtime_check module that this type is an unsigned int.
    Every other consumer of this type can ignore this metadata and treat
    this type as int.

    The first argument to Annotated must be a valid type.

    Details:

    - It's an error to call `Annotated` with less than two arguments.
    - Access the metadata via the ``__metadata__`` attribute::

        assert Annotated[int, '$'].__metadata__ == ('$',)

    - Nested Annotated types are flattened::

        assert Annotated[Annotated[T, Ann1, Ann2], Ann3] == Annotated[T, Ann1, Ann2, Ann3]

    - Instantiating an annotated type is equivalent to instantiating the
    underlying type::

        assert Annotated[C, Ann1](5) == C(5)

    - Annotated can be used as a generic type alias::

        type Optimized[T] = Annotated[T, runtime.Optimize()]
        # type checker will treat Optimized[int]
        # as equivalent to Annotated[int, runtime.Optimize()]

        type OptimizedList[T] = Annotated[list[T], runtime.Optimize()]
        # type checker will treat OptimizedList[int]
        # as equivalent to Annotated[list[int], runtime.Optimize()]

    - Annotated cannot be used with an unpacked TypeVarTuple::

        type Variadic[*Ts] = Annotated[*Ts, Ann1]  # NOT valid

      This would be equivalent to::

        Annotated[T1, T2, T3, ..., Ann1]

      where T1, T2 etc. are TypeVars, which would be invalid, because
      only one type should be passed to Annotated.
    """
    if len(params) < 2:
        raise TypeError("Annotated[...] should be used "
                        "with at least two arguments (a type and an "
                        "annotation).")
    if _is_unpacked_typevartuple(params[0]):
        raise TypeError("Annotated[...] should not be used with an "
                        "unpacked TypeVarTuple")
    msg = "Annotated[t, ...]: t must be a type."
    origin = _type_check(params[0], msg, allow_special_forms=True)
    metadata = tuple(params[1:])
    return _AnnotatedAlias(origin, metadata)


Dict = _SpecialGenericAlias(dict, 2, inst=False, name="Dict")
Counter = _SpecialGenericAlias(collections.Counter, 1)
