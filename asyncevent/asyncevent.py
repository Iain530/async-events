import asyncio
import inspect
import logging
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable
from functools import lru_cache, wraps
from weakref import ref, WeakMethod, ReferenceType

CACHE_SIZE = 100
LOGGER = logging.getLogger(__name__)


@dataclass
class Event:
    timestamp: datetime = field(default_factory=datetime.utcnow, init=False)


EventListenerType = Callable[[Event], None]


class AsyncEvents:
    def __init__(self) -> None:
        self._subs: dict[type[Event], set[ReferenceType[EventListenerType]]] = defaultdict(set)

    def subscribe(self, handler: EventListenerType, *event_types: type[Event]) -> None:
        """
        Subscribe handler to all event types passed. Any subclasses of
        specified event types passed will also trigger the handler.
        """
        if not asyncio.iscoroutinefunction(handler):
            raise TypeError("Event handler must be a coroutine function")

        ref = self._get_weakref(handler)
        for event_type in event_types:
            self._subs[event_type].add(ref)

    def listen(self, *event_types: type[Event]):
        """
        Decorator for subscribing async function (not methods) to event types.
        """
        def decorator(event_handler):

            @wraps(event_handler)
            async def wrapper(*args, **kwargs):
                return await event_handler(*args, **kwargs)

            self.subscribe(event_handler, *event_types)
            return wrapper
        return decorator

    def unsubscribe(self, handler: EventListenerType, *event_types: type[Event]) -> None:
        """
        Removes handler as a listener for specified event types.
        """
        for event_type in event_types:
            try:
                self._subs[event_type].remove(self._get_weakref(handler))
            except KeyError:
                LOGGER.warning(f"{handler=} is not subscribed to {event_type=}, could not unsubscribe")

    def dispatch(self, event: Event) -> None:
        """
        Fire an event asynchronously.
        """
        asyncio.create_task(self._dispatch(event))

    def remove_all_subscribers(self):
        self._subs = defaultdict(list)

    async def _dispatch(self, event: Event) -> None:
        listener_types = self._get_listener_types(type(event))
        for typ in listener_types:
            listeners = self._get_listeners(typ)

            for listener in listeners:
                try:
                    asyncio.create_task(listener(event))
                except Exception:
                    LOGGER.exception(f"Failed to create task for {listener=} and {event=}")

            self._remove_dead_listeners(typ)

    @staticmethod
    def _get_weakref(handler: EventListenerType) -> ref:
        if inspect.ismethod(handler):
            return WeakMethod(handler)
        return ref(handler)

    def _get_listeners(self, event_type: type[Event]) -> list[EventListenerType]:
        return [listener for ref in self._subs.get(event_type, []) if (listener := ref())]

    def _remove_dead_listeners(self, event_type: type[Event]) -> None:
        self._subs[event_type] = [ref for ref in self._subs.get(event_type, []) if ref()]

    @lru_cache(maxsize=CACHE_SIZE)
    def _get_listener_types(self, event_type: type[Event]) -> tuple[type, ...]:
        return inspect.getmro(event_type)
