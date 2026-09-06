"""
Singleton dependency container, built on pinject.

Every dependency registered via @provides is wired as a pinject SINGLETON
binding under its provided name. A class opts into receiving a dependency
by naming an __init__ parameter after that dependency's registered name;
pinject resolves it from there and reuses the same instance everywhere.
"""
from typing import Optional, Type, TypeVar

import pinject

from di.provides import get_providers

T = TypeVar("T")


class _ProvidesBindingSpec(pinject.BindingSpec):
    def __init__(self, providers: dict):
        self._providers = providers

    def configure(self, bind) -> None:
        for name, cls in self._providers.items():
            bind(name, to_class=cls, in_scope=pinject.SINGLETON)


class Container:
    """Resolves classes with their @provides-registered dependencies injected."""

    def __init__(self):
        providers = get_providers()
        binding_specs = [_ProvidesBindingSpec(providers)] if providers else []
        # modules=None disables pinject's default behavior of scanning every
        # currently-imported module for implicit bindings; we only want the
        # explicit @provides bindings above, and the scan is also fragile
        # (it can crash importing unrelated stdlib modules, e.g. dbm.gnu).
        self._obj_graph = pinject.new_object_graph(binding_specs=binding_specs, modules=None)

    def get(self, cls: Type[T]) -> T:
        """Instantiate `cls`, injecting any @provides dependencies it declares by name."""
        return self._obj_graph.provide(cls)


_container: Optional[Container] = None


def container() -> Container:
    """Return the process-wide Container, creating it (from the current registry) on first use."""
    global _container
    if _container is None:
        _container = Container()
    return _container


def reset_container() -> None:
    """Testing helper: drop the cached container, e.g. after registering new providers."""
    global _container
    _container = None
