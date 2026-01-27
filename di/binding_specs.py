"""
Custom binding specs for pinject dependency injection.

Binding specs allow you to explicitly configure how dependencies
are resolved when parameter names don't match class names.
"""
import pinject


class RecipeAnnotationBindingSpec(pinject.BindingSpec):
    """
    Example binding spec for recipe annotation components.
    Customize this or create new binding specs as needed.
    """
    
    def configure(self, bind):
        """
        Configure bindings for recipe annotation components.
        
        Args:
            bind: The bind function from pinject
        """
        # Example bindings (uncomment and customize as needed):
        # bind('recipe_annotation_pipeline', to_instance=some_pipeline_instance)
        # bind('recipe_annotation_store', to_class=RecipeAnnotationStore)
        pass
    
    @pinject.provides(in_scope=pinject.PROTOTYPE)
    def provide_recipe_annotation_pipeline(self):
        """
        Provide a recipe annotation pipeline instance.
        Use @provides decorator for custom instantiation logic.
        """
        # Example implementation:
        # return RecipeAnnotationPipeline(...)
        pass



