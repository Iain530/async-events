import asyncio
import weakref
import inspect
from collections import defaultdict
from functools import wraps
from typing import Callable
from functools import lru_cache, wraps

CACHE_SIZE = 1000


Event = object
EventListener = Callable[[Event], None]

class NewEvent(Event):
    pass


_subs: dict[type[Event], list[weakref.ReferenceType[EventListener]]] = defaultdict(list)


def _get_weakref(handler: EventListener) -> weakref.ref:
    if inspect.ismethod(handler):
        return weakref.WeakMethod(handler)
    return weakref.ref(handler)


def subscribe(handler: EventListener, *event_types: type[Event]) -> None:
    if not asyncio.iscoroutinefunction(handler):
        raise TypeError(f"Event handler must be a coroutine function")

    ref = _get_weakref(handler)
    for event_type in event_types:
        _subs[event_type].append(ref)


def listen(*event_types: type[Event]):
    def decorator(event_handler):

        @wraps(event_handler)
        async def wrapper(*args, **kwargs):
            return await event_handler(*args, **kwargs)
        
        subscribe(event_handler, *event_types)
        return wrapper
    return decorator


def unsubscribe(handler: EventListener, *event_types: type[Event]) -> None:
    for event_type in event_types:
        try:
            _subs[event_type].remove(_get_weakref(handler))
        except ValueError:
            raise


def dispatch(event: Event) -> None:
    asyncio.create_task(_dispatch(event))


async def _dispatch(event: Event) -> None:
    listener_types = _get_listener_types(type(event))
    for typ in listener_types:
        listeners = _get_listeners(typ)

        for listener in listeners:
            try:
                asyncio.create_task(listener(event))
            except Exception:
                raise  # TODO

        _remove_dead_listeners(typ)


def _get_listeners(event_type: type[Event]) -> list[EventListener]:
    return [listener for ref in _subs[event_type] if (listener := ref())]


def _remove_dead_listeners(event_type: type[Event]) -> None:
    _subs[event_type] = [ref for ref in _subs.get(event_type, []) if ref()]


@lru_cache(maxsize=CACHE_SIZE)
def _get_listener_types(event_type: type[Event]) -> tuple[type, ...]:
    return inspect.getmro(event_type)
