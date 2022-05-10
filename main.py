from asyncevent import AsyncEvents, Event
import gc
import asyncio


events = AsyncEvents()


@events.listen(Event)
async def handle(event):
    print(event)


class A:
    def __init__(self) -> None:
        events.subscribe(self.handle, Event)
        pass

    async def handle(self, event):
        print(event)


async def main():
    a = A()
    while True:
        events.dispatch(Event())
        events.dispatch("1")
        await asyncio.sleep(1)
        gc.collect()
        a = 1


if __name__ == '__main__':
    asyncio.run(main())