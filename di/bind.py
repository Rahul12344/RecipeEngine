"""
Binding decorators for dependency injection.

Use @bind() to annotate classes or methods that should be used for dependency injection.
"""
from typing import Any, Callable, Optional, Type
from functools import wraps
import inspect


class BindAnnotation:
    """Metadata stored on classes/methods with @bind decorator."""

    def __init__(
        self,
        bind_to: Optional[Type] = None,
        bind_to_instance: Optional[Any] = None,
        scope: str = "prototype",
        provides: Optional[str] = None
    ):
        """
        Initialize binding annotation.

        Args:
            bind_to: Class to bind to (for class bindings)
            bind_to_instance: Instance to bind to (for singleton bindings)
            scope: "prototype" (new instance each time) or "singleton" (same instance)
            provides: Name of the dependency this provides (for method bindings)
        """
        self.bind_to = bind_to
        self.bind_to_instance = bind_to_instance
        self.scope = scope
        self.provides = provides


def bind(
    bind_to: Optional[Type] = None,
    bind_to_instance: Optional[Any] = None,
    scope: str = "prototype",
    provides: Optional[str] = None
):
    """
    Decorator to mark a class or method for dependency injection binding.

    Usage examples:

    # Bind a class to itself (default)
    @bind()
    class MyService:
        pass

    # Bind a class to an interface
    @bind(bind_to=IService)
    class MyService:
        pass

    # Bind to a singleton instance
    @bind(bind_to_instance=MyService(), scope="singleton")
    class MyService:
        pass

    # Bind a method as a provider
    @bind(provides="my_service", scope="singleton")
    def provide_my_service():
        return MyService()

    Args:
        bind_to: Class to bind to (for class bindings)
        bind_to_instance: Instance to bind to (for singleton bindings)
        scope: "prototype" (new instance each time) or "singleton" (same instance)
        provides: Name of the dependency this provides (for method bindings)
    """
    def decorator(obj: Any) -> Any:
        # Store binding metadata on the object
        if not hasattr(obj, '__bind_annotation__'):
            obj.__bind_annotation__ = BindAnnotation(
                bind_to=bind_to,
                bind_to_instance=bind_to_instance,
                scope=scope,
                provides=provides
            )
        return obj

    return decorator



