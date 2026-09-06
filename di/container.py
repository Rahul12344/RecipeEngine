"""
Singleton dependency container, built on pinject.

Every dependency registered via @provides is wired as a pinject SINGLETON
binding under its provided name -- a class provider is bound with
to_class=cls; a function provider is exposed as a dynamically-attached
pinject provider method (pinject's bind() has no to_provider kwarg in the
installed version, so a provider function is wired the same way a
BindingSpec's own @pinject.provides-decorated methods are). A class opts
into receiving a dependency by naming an __init__ parameter after that
dependency's registered name; pinject resolves it from there (regardless of
whether it came from a class or function provider) and reuses the same
instance everywhere.
"""
import inspect
import types
from typing import Callable, Optional, Type, TypeVar

import pinject

from di.provides import get_providers

T = TypeVar("T")


def _make_provider_method(name: str, fn: Callable[[], object]):
    """Build a pinject provider method (to be bound to a BindingSpec instance)
    for a function-based provider registered under `name`."""
    @pinject.provides(arg_name=name, in_scope=pinject.SINGLETON)
    def provider_method(self):
        return fn()
    return provider_method


class _ProvidesBindingSpec(pinject.BindingSpec):
    def __init__(self, providers: dict):
        self._class_providers = {}
        for name, target in providers.items():
            if inspect.isclass(target):
                self._class_providers[name] = target
            else:
                # Attach a bound provider method per function provider so
                # pinject's method-scanning (the same mechanism it uses for
                # a BindingSpec's own @pinject.provides methods) picks it up.
                method = _make_provider_method(name, target)
                setattr(self, f"_provide_{name}", types.MethodType(method, self))

    def configure(self, bind) -> None:
        for name, cls in self._class_providers.items():
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
