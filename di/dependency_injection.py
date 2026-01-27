"""
Dependency Injection configuration using pinject.

This module sets up the dependency injection container and provides
bindings for all classes in the application.
"""
import pinject
import inspect
from typing import Optional, List, Any
from di.annotation_scanner import AnnotationScanner
from di.bind import BindAnnotation


class DependencyInjectionContainer:
    """
    Dependency injection container using pinject.
    Provides a centralized way to configure and resolve dependencies.
    Automatically scans for @bind annotations.
    """

    def __init__(self, modules: Optional[List[Any]] = None, auto_scan: bool = True):
        """
        Initialize the DI container with bindings.

        Args:
            modules: List of modules to scan for @bind annotations. If None, uses default modules.
            auto_scan: Whether to automatically scan for @bind annotations
        """
        self._obj_graph: Optional[pinject.ObjectGraph] = None
        self._binding_specs = []
        self._modules = modules
        self._auto_scan = auto_scan
        self._configure_bindings()

    def _configure_bindings(self) -> None:
        """
        Configure all dependency bindings.
        Scans for @bind annotations and creates bindings automatically.
        """
        binding_specs = []

        # Scan for @bind annotations if auto_scan is enabled
        if self._auto_scan:
            scanner = AnnotationScanner(modules=self._modules)

            # If modules provided, scan them
            if self._modules:
                for module in self._modules:
                    scanner.scan_module(module)
            else:
                # Scan all imported modules in the call stack
                # This will scan modules that have been imported
                self._scan_imported_modules(scanner)

            # Create binding spec from discovered annotations
            discovered_bindings = scanner.get_bindings()
            if discovered_bindings:
                annotation_binding_spec = scanner.create_binding_spec()
                binding_specs.append(annotation_binding_spec)

        # Add any additional custom binding specs here
        # binding_specs.append(CustomBindingSpec())

        # Create object graph with binding specs
        if binding_specs:
            self._obj_graph = pinject.new_object_graph(
                binding_specs=binding_specs,
                modules=self._modules
            )
        else:
            # If no custom bindings, use default pinject behavior
            # which automatically wires dependencies based on parameter names
            self._obj_graph = pinject.new_object_graph(modules=self._modules)

    def _scan_imported_modules(self, scanner: AnnotationScanner) -> None:
        """
        Scan imported modules for @bind annotations.
        This is a basic implementation - you may want to explicitly pass modules.
        """
        import sys
        import os
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Scan all loaded modules
        for module_name, module in sys.modules.items():
            # Skip built-in and third-party modules
            if module_name.startswith('_') or '.' not in module_name:
                continue
            # Only scan modules from this project
            if hasattr(module, '__file__') and module.__file__:
                module_path = os.path.abspath(module.__file__)
                if project_root in module_path:
                    try:
                        scanner.scan_module(module)
                    except Exception:
                        # Skip modules that can't be scanned
                        pass

    def provide(self, cls: type) -> object:
        """
        Provide an instance of the given class with dependencies injected.

        Args:
            cls: The class to instantiate

        Returns:
            An instance of the class with dependencies injected
        """
        if self._obj_graph is None:
            raise RuntimeError("Object graph not initialized")
        return self._obj_graph.provide(cls)

    def add_binding_spec(self, binding_spec: pinject.BindingSpec) -> None:
        """
        Add a custom binding spec to the container.

        Args:
            binding_spec: A pinject BindingSpec instance
        """
        self._binding_specs.append(binding_spec)
        # Recreate object graph with new binding spec
        if self._binding_specs:
            self._obj_graph = pinject.new_object_graph(
                binding_specs=self._binding_specs,
                modules=self._modules
            )
        else:
            self._obj_graph = pinject.new_object_graph(modules=self._modules)

    def scan_module(self, module: Any) -> None:
        """
        Manually scan a module for @bind annotations and update bindings.

        Args:
            module: The module to scan
        """
        scanner = AnnotationScanner(modules=[module])
        scanner.scan_module(module)
        discovered_bindings = scanner.get_bindings()
        if discovered_bindings:
            annotation_binding_spec = scanner.create_binding_spec()
            self.add_binding_spec(annotation_binding_spec)


# Global container instance
_container: Optional[DependencyInjectionContainer] = None


def get_container(modules: Optional[List[Any]] = None) -> DependencyInjectionContainer:
    """
    Get the global dependency injection container instance.
    Creates it if it doesn't exist (singleton pattern).

    Args:
        modules: Optional list of modules to scan for @bind annotations

    Returns:
        The global DependencyInjectionContainer instance
    """
    global _container
    if _container is None:
        _container = DependencyInjectionContainer(modules=modules)
    return _container


def reset_container() -> None:
    """
    Reset the global container (useful for testing).
    """
    global _container
    _container = None

