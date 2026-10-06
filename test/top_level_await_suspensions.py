# CPython-checked module source: compile with PyCF_ALLOW_TOP_LEVEL_AWAIT.
class Pause:
    def __await__(self):
        yield 'pause'
        return 42
answer = await Pause()
