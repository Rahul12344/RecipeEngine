"""
Registry of singleton dependency providers.

Use @provides("some_name") on a class to register it as the singleton
implementation for that name. Any other class whose __init__ takes a
parameter literally named "some_name" will have that singleton injected
automatically by the container (see di.container).
"""
from typing import Dict, Type

_PROVIDERS: Dict[str, Type] = {}


def provides(name: str):
    """Class decorator that registers `cls` as the singleton provider for `name`."""
    def decorator(cls: Type) -> Type:
        existing = _PROVIDERS.get(name)
        if existing is not None and existing is not cls:
            raise ValueError(
                f"DI name '{name}' is already provided by {existing.__name__}; "
                f"cannot also register it to {cls.__name__}"
            )
        _PROVIDERS[name] = cls
        cls.__di_name__ = name
        return cls
    return decorator


def get_providers() -> Dict[str, Type]:
    """Return a copy of the current name -> class registry."""
    return dict(_PROVIDERS)


def reset_providers() -> None:
    """Testing helper: clear the registry."""
    _PROVIDERS.clear()
