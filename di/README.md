# Dependency Injection with Pinject

This module provides dependency injection capabilities using pinject with `@bind` annotations.

## Basic Usage with @bind Annotations

Use the `@bind()` decorator to mark classes or methods for dependency injection:

```python
from di import bind, get_container

# Annotate a class for dependency injection
@bind()
class MyService:
    def __init__(self, dependency: SomeDependency):
        self.dependency = dependency

# Get the DI container (automatically scans for @bind annotations)
container = get_container()

# Get an instance with dependencies automatically injected
service = container.provide(MyService)
```

## @bind Decorator Options

### Binding a Class to Itself (Default)

```python
@bind()
class RecipeSourceRetriever:
    pass

# This creates a binding: recipe_source_retriever -> RecipeSourceRetriever
```

### Binding a Class to an Interface

```python
@bind(bind_to=IRecipeRetriever)
class RecipeSourceRetriever:
    pass

# This creates a binding: i_recipe_retriever -> RecipeSourceRetriever
```

### Binding to a Singleton Instance

```python
@bind(bind_to_instance=MyService(), scope="singleton")
class MyService:
    pass

# Or bind a class to a singleton instance
@bind(scope="singleton")
class DatabaseConnection:
    pass
```

### Binding a Method as a Provider

```python
@bind(provides="my_service", scope="singleton")
def provide_my_service():
    return MyService(config)

# This creates a binding: my_service -> result of provide_my_service()
```

## Complete Example

```python
from di import bind, get_container

# Define dependencies with @bind
@bind()
class DatabaseConnection:
    def __init__(self, connection_string: str):
        self.conn = connection_string

@bind()
class RecipeRepository:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

@bind(provides="connection_string")
def provide_connection_string():
    return "postgresql://localhost/db"

# Use the container
container = get_container()
repository = container.provide(RecipeRepository)
# DatabaseConnection and connection_string are automatically injected
```

## How Parameter Name Matching Works

The `@bind()` decorator converts class names to parameter names:
- `RecipeSourceRetriever` → `recipe_source_retriever`
- `MyService` → `my_service`
- `DatabaseConnection` → `database_connection`

When a class constructor has a parameter like `recipe_source_retriever: RecipeSourceRetriever`,
pinject will automatically find and inject the bound class.

## Scopes

- `scope="prototype"` (default): New instance every time
- `scope="singleton"`: Same instance every time

```python
@bind(scope="singleton")
class SharedService:
    pass
```

## Explicit Module Scanning

By default, the container scans all imported modules. You can also explicitly specify modules:

```python
import my_module
from di import get_container

container = get_container(modules=[my_module])
```

## Manual Module Scanning

You can also manually scan a module after container creation:

```python
container = get_container()
container.scan_module(my_module)
```

