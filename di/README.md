# Dependency Injection

Minimal singleton-only DI, built on [pinject](https://github.com/google/pinject).

## Registering a provider

Decorate a class with `@provides("<DI_name>")` to register it as the
singleton implementation for that name:

```python
from di import provides

@provides("recipe_annotation_store")
class RecipeAnnotationStore:
    ...
```

## Consuming a provider

Any class whose `__init__` takes a parameter literally named after a
registered DI name gets that singleton injected automatically:

```python
class RecipeAnnotationPipeline:
    def __init__(self, recipe_annotator: RecipeAnnotator, recipe_annotation_store: RecipeAnnotationStore):
        ...
```

`RecipeAnnotationPipeline` is "used" by the DI framework because its
`__init__` has parameters named `recipe_annotator` and
`recipe_annotation_store` — those exact strings must match the names
classes were registered under with `@provides`.

Parameters that don't match a registered name (plain config values,
lists, dicts, etc.) are not auto-wired and must still be passed
explicitly by the caller.

## Getting an instance

```python
from di import container

pipeline = container().get(RecipeAnnotationPipeline)
```

Every dependency resolved through a registered name is a singleton —
the same instance is reused for the lifetime of the process, across
every class that declares a parameter with that name.
