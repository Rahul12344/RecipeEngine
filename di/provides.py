"""
Registry of singleton dependency providers.

Decorate a class OR a zero-arg function with @provides("some_name") to
register it as the singleton provider for that name. Any other class whose
__init__ takes a parameter literally named "some_name" will have that
singleton injected automatically by the container (see di.container).

Use a class provider (instantiated as `cls()`) when the type itself is the
thing you want a singleton of. Use a function provider (called as `fn()`)
when building the singleton needs logic that doesn't belong in a class's own
zero-arg __init__ -- e.g. constructing a generically-configured instance of
a shared, reusable class (table name, serializer, etc.) without needing a
dedicated subclass just to carry that configuration.
"""
import inspect
from typing import Callable, Dict, Type, Union

Provider = Union[Type, Callable[[], object]]

_PROVIDERS: Dict[str, Provider] = {}


def provides(name: str):
    """Class or zero-arg-function decorator that registers the target as the
    singleton provider for `name`."""
    def decorator(target: Provider) -> Provider:
        existing = _PROVIDERS.get(name)
        if existing is not None and existing is not target:
            existing_kind = "class" if inspect.isclass(existing) else "function"
            raise ValueError(
                f"DI name '{name}' is already provided by {existing_kind} "
                f"'{getattr(existing, '__name__', existing)}'; cannot also "
                f"register it to {getattr(target, '__name__', target)}"
            )
        _PROVIDERS[name] = target
        if inspect.isclass(target):
            target.__di_name__ = name
        return target
    return decorator


def get_providers() -> Dict[str, Provider]:
    """Return a copy of the current name -> provider (class or function) registry."""
    return dict(_PROVIDERS)


def reset_providers() -> None:
    """Testing helper: clear the registry."""
    _PROVIDERS.clear()
