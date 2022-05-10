from asyncevent import AsyncEvents, Event
from asynctest import Mock, CoroutineMock, patch
import asyncio
import pytest


class Signal:
    def __init__(self):
        self.event = asyncio.Event()
    
    def trigger(self, *args, **kwargs):
        self.event.set()

    def coroutine_mock(self):
        return CoroutineMock(side_effect=self.trigger)

    @property
    def triggered(self) -> bool:
        return self.event.is_set()

    async def wait_for_trigger(self, timeout: float = 5):
        try:
            await asyncio.wait_for(self.event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass


@pytest.fixture
def signal() -> Signal:
    return Signal()


@pytest.fixture
def event_system():
    es = AsyncEvents()
    yield es
    es.remove_all_subscribers()


async def test_subscribed_coroutine_called_when_event_dispatched(signal, event_system):
    fn = signal.coroutine_mock()
    event_system.subscribe(fn, Event)
    event = Event()

    event_system.dispatch(event)
    
    await signal.wait_for_trigger()
    fn.assert_awaited_once_with(event)


async def test_subscribed_coroutine_called_when_subclass_of_event_dispatched(signal, event_system):
    
    class MoreSpecificEvent(Event):
        pass

    fn = signal.coroutine_mock()
    event_system.subscribe(fn, Event)
    event = MoreSpecificEvent()
    
    event_system.dispatch(event)
    
    await signal.wait_for_trigger()
    fn.assert_awaited_once_with(event)


async def test_unsubscribe(signal, event_system):
    fn = signal.coroutine_mock()
    event_system.subscribe(fn, Event)

    event_system.unsubscribe(fn, Event)
    event_system.dispatch(Event())

    await signal.wait_for_trigger(timeout=0.5)
    fn.assert_not_called()


async def test_unsubscribe_logs_warning_if_not_subscribed(event_system):
    fn = CoroutineMock()

    with patch("asyncevent.asyncevent.LOGGER", Mock()) as mock_logger:
        event_system.unsubscribe(fn, Event)

        mock_logger.warning.assert_called_with(f"handler={fn} is not subscribed to event_type={Event}, could not unsubscribe")


async def test_listen(signal, event_system):

    @event_system.listen(Event)
    async def fn(event):
        signal.trigger()
    
    event = Event()
    event_system.dispatch(event)

    await signal.wait_for_trigger()
    assert signal.triggered


async def test_type_error_raised_when_not_coroutine_function(event_system):
    with pytest.raises(TypeError) as exc_info:
        event_system.subscribe(lambda: 1, Event)
    
    exc = exc_info.value
    assert exc.args[0] == "Event handler must be a coroutine function"
