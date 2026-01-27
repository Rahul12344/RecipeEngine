"""
Scanner to discover @bind annotations in modules and create pinject bindings.
"""
import inspect
import importlib
from typing import List, Type, Any, Optional
import pinject
from di.bind import BindAnnotation


class AnnotationBindingSpec(pinject.BindingSpec):
    """
    Pinject binding spec created from @bind annotations.
    """

    def __init__(self, bindings: List[tuple]):
        """
        Initialize with discovered bindings.

        Args:
            bindings: List of (binding_name, target, scope, bind_to_instance) tuples
        """
        self._bindings = bindings

    def get_bindings(self) -> List[tuple]:
        """Get all bindings."""
        return self._bindings

    def configure(self, bind):
        """Configure bindings from annotations."""
        for binding_name, target, scope, bind_to_instance in self._bindings:
            if bind_to_instance is not None:
                # Bind to a specific instance
                bind(binding_name, to_instance=bind_to_instance)
            elif inspect.isclass(target):
                # Bind to a class
                if scope == "singleton":
                    bind(binding_name, to_class=target, in_scope=pinject.SINGLETON)
                else:
                    bind(binding_name, to_class=target, in_scope=pinject.PROTOTYPE)
            else:
                # Bind to a callable (method/function) - use as provider
                # For singleton, call once and bind to instance
                if scope == "singleton":
                    instance = target()
                    bind(binding_name, to_instance=instance)
                else:
                    # For prototype, bind to provider function
                    bind(binding_name, to_provider=target, in_scope=pinject.PROTOTYPE)


class AnnotationScanner:
    """
    Scans modules for @bind annotations and creates bindings.
    """

    def __init__(self, modules: Optional[List[Any]] = None):
        """
        Initialize the scanner.

        Args:
            modules: List of modules to scan. If None, will scan all imported modules.
        """
        self.modules = modules or []
        self._discovered_bindings: List[tuple] = []

    def scan_module(self, module: Any) -> None:
        """
        Scan a module for @bind annotations.

        Args:
            module: The module to scan
        """
        for name, obj in inspect.getmembers(module):
            # Skip private attributes
            if name.startswith('_'):
                continue

            # Check if it has a @bind annotation
            if hasattr(obj, '__bind_annotation__'):
                annotation: BindAnnotation = obj.__bind_annotation__
                self._process_binding(name, obj, annotation)

    def _process_binding(
        self,
        name: str,
        obj: Any,
        annotation: BindAnnotation
    ) -> None:
        """
        Process a discovered binding annotation.

        Args:
            name: Name of the object
            obj: The object (class, function, etc.)
            annotation: The binding annotation
        """
        if inspect.isclass(obj):
            # Class binding
            if annotation.bind_to_instance is not None:
                # Bind to instance - use the instance itself
                binding_name = self._get_binding_name(obj, annotation)
                # Create instance if it's a class
                instance = annotation.bind_to_instance if not inspect.isclass(annotation.bind_to_instance) else annotation.bind_to_instance()
                self._discovered_bindings.append((
                    binding_name,
                    obj,
                    annotation.scope,
                    instance
                ))
            elif annotation.bind_to is not None:
                # Bind class to another class (interface binding)
                # The binding name should match the parameter name for the interface
                binding_name = self._get_binding_name(annotation.bind_to, annotation)
                self._discovered_bindings.append((
                    binding_name,
                    obj,  # The implementation class
                    annotation.scope,
                    None
                ))
            else:
                # Bind class to itself - use class name converted to parameter name
                binding_name = self._get_binding_name(obj, annotation)
                self._discovered_bindings.append((
                    binding_name,
                    obj,
                    annotation.scope,
                    None
                ))
        elif inspect.isfunction(obj) or inspect.ismethod(obj):
            # Method/function binding (provider)
            if annotation.provides:
                binding_name = annotation.provides
            else:
                # Convert function name to parameter name format
                # e.g., provide_my_service -> my_service
                binding_name = name.replace('provide_', '').replace('_provider', '')
            self._discovered_bindings.append((
                binding_name,
                obj,
                annotation.scope,
                None
            ))

    def _get_binding_name(self, obj: Any, annotation: BindAnnotation) -> str:
        """
        Get the binding name for an object.

        Args:
            obj: The object to get binding name for
            annotation: The binding annotation

        Returns:
            The binding name (parameter name format)
        """
        if inspect.isclass(obj):
            # Convert class name to parameter name (CamelCase -> snake_case)
            class_name = obj.__name__
            # Simple conversion: MyClass -> my_class
            # This is a basic implementation; you might want a more robust converter
            binding_name = self._camel_to_snake(class_name)
            return binding_name
        return obj.__name__

    def _camel_to_snake(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
        import re
        # Insert an underscore before any uppercase letter that follows a lowercase letter
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        # Insert an underscore before any uppercase letter that follows a lowercase letter or number
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def create_binding_spec(self) -> AnnotationBindingSpec:
        """
        Create a pinject BindingSpec from discovered bindings.

        Returns:
            AnnotationBindingSpec with all discovered bindings
        """
        return AnnotationBindingSpec(self._discovered_bindings)

    def get_bindings(self) -> List[tuple]:
        """Get all discovered bindings."""
        return self._discovered_bindings

