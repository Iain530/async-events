import asyncio
import weakref
import inspect
from collections import defaultdict
from functools import wraps
from typing import Callable



class Event:
    pass


class NewEvent(Event):
    pass


_subs = defaultdict(list)


def subscribe(handler, *event_types) -> None:
    if inspect.ismethod(handler):
        ref = weakref.WeakMethod(handler)
    else:
        ref = weakref.ref(handler)
    for event_type in event_types:
        _subs[event_type].append(ref)


def on(*event_types):
    def decorator(event_handler):

        @wraps(event_handler)
        async def wrapper(*args, **kwargs):
            return await event_handler(*args, **kwargs)
        
        subscribe(event_handler, *event_types)
        return wrapper
    return decorator


def unsubscribe(handler, *event_types) -> None:
    for event_type in event_types:
        try:
            _subs[event_type].remove(handler)
        except ValueError:
            pass


def dispatch(event) -> None:
    asyncio.create_task(_dispatch(event))


async def _dispatch(event) -> None:
    event_types = inspect.getmro(type(event))
    for event_type in event_types:
        listeners = _get_listeners(event_type)

        for listener in listeners:
            try:
                asyncio.create_task(listener(event))
            except Exception:
                raise

        _remove_dead_listeners(event_type)


def _get_listeners(event_type) -> list[Callable]:
    return [listener for ref in _subs[event_type] if (listener := ref())]


def _remove_dead_listeners(event_type) -> None:
    _subs[event_type] = [ref for ref in _subs.get(event_type, []) if ref()]
