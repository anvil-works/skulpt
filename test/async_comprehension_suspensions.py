# CPython-checked native async suspension regression; also run with Skulpt's
# host suspension setting both disabled and enabled by generator_suspensions.js.
class Pause:
    def __init__(self, value): self.value = value
    def __await__(self):
        yield 'pause'
        return self.value

async def values():
    for i in range(2): yield await Pause(i)

async def run():
    i = 'outer'
    result = [(lambda: i, (last := await Pause(i))) async for i in values()]
    return i, last, [f() for f, _ in result], [v for _, v in result]

c = run()
seen = []
while True:
    try: seen.append(c.send(None))
    except StopIteration as error:
        assert error.value == ('outer', 1, [1, 1], [0, 1])
        break
assert seen == ['pause'] * 4

async def run_gen():
    gen = ((i, await Pause(i)) for i in range(2))
    return [value async for value in gen]
c = run_gen()
assert c.send(None) == 'pause'
assert c.send(None) == 'pause'
try: c.send(None)
except StopIteration as error: assert error.value == [(0, 0), (1, 1)]
else: assert False, 'generator expression did not finish'
