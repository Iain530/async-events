from asyncevent import subscribe, dispatch, Event, NewEvent, listen
import gc
import asyncio


@listen(Event)
def handle(event):
    print(event)


class A:
    def __init__(self) -> None:
        subscribe(self.handle, Event)
        pass

    # @on(Event)  # TODO: tell if in class when decorator is applied
    def handle(self, event):
        print(event)


async def main():
    a = A()
    while True:
        dispatch(Event())
        dispatch(NewEvent())
        dispatch("1")
        await asyncio.sleep(1)
        gc.collect()
        a = 1


if __name__ == '__main__':
    asyncio.run(main())