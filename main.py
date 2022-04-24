from asyncevent import subscribe, dispatch, Event, NewEvent, on
import gc
import asyncio


# @on(Event)
# async def handle(event):
#     print(event)


class A:
    def __init__(self) -> None:
        # subscribe(self.handle, Event)
        pass

    @on(Event)  # TODO: tell if in class when decorator is applied
    async def handle(self, event):
        print(event)


async def main():
    a = A()
    while True:
        dispatch(Event())
        dispatch(NewEvent())
        await asyncio.sleep(1)
        gc.collect()
        a = 1


if __name__ == '__main__':
    asyncio.run(main())