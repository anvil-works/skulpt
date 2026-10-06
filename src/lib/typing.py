"""Compiler-created typing objects; further typing APIs remain unimplemented."""
from _typing import TypeAliasType, TypeVar, NoDefault, ParamSpec, ParamSpecArgs, ParamSpecKwargs, TypeVarTuple, Unpack, _UnpackGenericAlias, _type_repr as _native_type_repr
from types import GenericAlias, UnionType
Union = UnionType

def get_args(tp):
    if isinstance(tp, (GenericAlias, UnionType, _UnpackGenericAlias, _GenericAlias)):
        return tp.__args__
    return ()

def get_origin(tp):
    if isinstance(tp, (GenericAlias, UnionType, _UnpackGenericAlias, _GenericAlias, ParamSpecArgs, ParamSpecKwargs)):
        return tp.__origin__
    return None

# Helpers invoked by native parameters, following CPython Lib/typing.py.
def _type_check(arg, message):
    if arg is None:
        return type(None)
    if isinstance(arg, str):
        raise NotImplementedError("string type arguments require ForwardRef support")
    if type(arg) is tuple:
        raise TypeError(message + " Got " + repr(arg) + ".")
    return arg

def _is_param_expr(arg):
    return arg is ... or isinstance(arg, (tuple, list, ParamSpec))

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

def _type_convert(arg):
    return _type_check(arg, "Expected a type.")

def _generic_alias_mro_entries(alias, bases):
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
    return _native_type_repr(value)

class _BaseGenericAlias:
    def __init__(self, origin, *, inst=True, name=None):
        self._inst = inst
        self._name = name
        self.__origin__ = origin
        self.__slots__ = None

    def __init_subclass__(cls, *, _root=False):
        if not _root:
            raise TypeError("Cannot subclass special typing classes")

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

            if _is_unpacked_typevartuple(old_arg):
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

