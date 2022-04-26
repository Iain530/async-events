from asyncevent import Event, dispatch, listen, subscribe, unsubscribe, _subs, _get_listeners
from asynctest import Mock, CoroutineMock
import asyncio
import time
import pytest


class Signal:
    def __init__(self):
        self.triggered = False
    
    def trigger(self, *args, **kwargs):
        self.triggered = True

    def coroutine_mock(self):
        return CoroutineMock(side_effect=self.trigger)

    async def wait_for_trigger(self, timeout: float = 5, delay: float = 0.1):
        start = time.time()
        while not self.triggered and time.time() - start < timeout:
            await asyncio.sleep(delay)


@pytest.fixture
def signal() -> Signal:
    return Signal()


async def test_subscribed_coroutine_called_when_event_dispatched(signal):
    fn = signal.coroutine_mock()
    subscribe(fn, Event)
    event = Event()

    dispatch(event)
    
    await signal.wait_for_trigger()
    fn.assert_awaited_once_with(event)


async def test_subscribed_coroutine_called_when_subclass_of_event_dispatched(signal):
    
    class MoreSpecificEvent(Event):
        pass

    fn = signal.coroutine_mock()
    subscribe(fn, Event)
    event = MoreSpecificEvent()
    
    dispatch(event)
    
    await signal.wait_for_trigger()
    fn.assert_awaited_once_with(event)


async def test_unsubscribe(signal):
    fn = signal.coroutine_mock()
    subscribe(fn, Event)

    unsubscribe(fn, Event)
    dispatch(Event())

    await signal.wait_for_trigger(timeout=0.5)
    fn.assert_not_called()


async def test_listen(signal):

    @listen(Event)
    async def fn(event):
        signal.trigger()
    
    event = Event()
    dispatch(event)

    await signal.wait_for_trigger()
    assert signal.triggered


async def test_type_error_raised_when_not_coroutine_function():
    with pytest.raises(TypeError) as exc_info:
        subscribe(lambda: 1, Event)
    
    exc = exc_info.value
    assert exc.args[0] == "Event handler must be a coroutine function"
