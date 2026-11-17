"""Synchronous ExitStack, adapted from CPython's contextlib."""

class ExitStack(object):
    """Context manager for dynamic management of a stack of exit callbacks.

    Skulpt does not yet link implicit exception contexts during unwinding.
    """

    __module__ = "contextlib"

    def __init__(self):
        self._exit_callbacks = []

    def pop_all(self):
        """Transfer the callbacks to a new stack without running them."""
        new_stack = type(self)()
        new_stack._exit_callbacks = self._exit_callbacks
        self._exit_callbacks = []
        return new_stack

    def push(self, exit):
        """Register an exit callback or a context manager's __exit__ method."""
        try:
            exit_method = type(exit).__exit__
        except AttributeError:
            self._exit_callbacks.append(exit)
        else:
            from types import MethodType
            self._exit_callbacks.append(MethodType(exit_method, exit))
        return exit

    def enter_context(self, cm):
        """Enter a context manager and register its exit if entry succeeds."""
        # Special methods are looked up on the type, just as with does.
        cls = type(cm)
        try:
            enter = cls.__enter__
            exit = cls.__exit__
        except AttributeError:
            error = TypeError(
                "'{}.{}' object does not support the context manager protocol"
                .format(cls.__module__, cls.__qualname__)
            )
            error.__cause__ = None
            raise error
        # Loading types can suspend. Resolve it before acquiring the resource.
        from types import MethodType
        result = enter(cm)
        self._exit_callbacks.append(MethodType(exit, cm))
        return result

    def callback(*args, **kwargs):
        """Register a callback that cannot suppress exceptions."""
        # Until Skulpt supports positional-only parameters, read self and
        # callback from args so those names can be passed on as keywords.
        if len(args) < 2:
            raise TypeError("ExitStack.callback() requires a callback")
        self, callback = args[:2]
        callback_args = args[2:]

        def _exit_wrapper(exc_type, exc, traceback):
            callback(*callback_args, **kwargs)

        _exit_wrapper.__wrapped__ = callback
        self._exit_callbacks.append(_exit_wrapper)
        return callback

    def __enter__(self):
        return self

    def __exit__(self, *exc_details):
        exc = exc_details[1]
        received_exc = exc is not None
        pending_raise = False

        # Each callback sees the outcome from the one inside it, as with
        # nested with statements. Skulpt has no active exception state to
        # reproduce CPython's implicit __context__ chain during unwinding.
        while self._exit_callbacks:
            callback = self._exit_callbacks.pop()
            try:
                if exc is None:
                    exc_details = None, None, None
                else:
                    exc_details = type(exc), exc, exc.__traceback__
                if callback(*exc_details):
                    pending_raise = False
                    exc = None
            except BaseException as new_exc:
                pending_raise = True
                exc = new_exc

        if pending_raise:
            raise exc
        return received_exc and exc is None

    def close(self):
        """Immediately unwind the context stack."""
        self.__exit__(None, None, None)
