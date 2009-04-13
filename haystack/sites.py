from haystack.indexes import BasicSearchIndex
from haystack.fields import *
try:
    set
except NameError:
    from sets import Set as set


class AlreadyRegistered(Exception):
    pass

class NotRegistered(Exception):
    pass

class NotAModel(Exception):
    pass


class SearchSite(object):
    """
    Encapsulates all the indexes that should be available.
    
    This allows you to register indexes on models you don't control (reusable
    apps, django.contrib, etc.) as well as customize on a per-site basis what
    indexes should be available (different indexes for different sites, same
    codebase).
    """
    
    def __init__(self):
        self._registry = {}
    
    def register(self, model_ct, index_class=None):
        """
        Registers a model with the site.
        
        The model should be a Model class, not instances.
        
        If no custom index is provided, a generic SearchIndex will be applied
        to the model.
        """
        if not index_class:
            index_class = BasicSearchIndex
        
        if model_ct in self._registry:
            # raise AlreadyRegistered("The model '%s' is already registered." % model_ct)
            # DRL_FIXME: Issue a warning instead?
            return
        
        self._registry[model_ct] = index_class(model_ct)
    
    def unregister(self, model_ct):
        """
        Unregisters a model from the site.
        """
        if model_ct not in self._registry:
            # raise NotRegistered("The model '%s' is not registered." % ct)
            # DRL_FIXME: Issue a warning instead?
            return
        
        self._teardown_signals(self.get_model(model_ct), self._registry[model_ct])
        del(self._registry[model_ct])
    
    def get_model_ct(self, model):
        """
        From a Model instance, get the appropriate Content-Type.
        """
        if not hasattr(model, '_meta'):
            # raise NotAModel("That object does not appear to be a Django model.")
            # DRL_FIXME: Issue a warning instead?
            return ""
        
        return "%s.%s" % (model._meta.app_label, model._meta.module_name)
    
    def get_model(self, model_ct):
        """
        From a Content-Type instance, get the appropriate Model.
        """
        from django.db import models
        return models.get_model(*model_ct.split('.'))
    
    def activate(self, model):
        ct = self.get_model_ct(model)
        
        if ct in self._registry:
            # Since we know about this model, setup everything needed to track it.
            self._setup_signals(model, self._registry[ct])
            return True
        
        return False
    
    def _setup_signals(self, model, index):
        from django.db.models import signals
        signals.post_save.connect(index.update_object, sender=model)
        signals.post_delete.connect(index.remove_object, sender=model)
    
    def _teardown_signals(self, model, index):
        from django.db.models import signals
        signals.post_save.disconnect(index.update_object, sender=model)
        signals.post_delete.disconnect(index.remove_object, sender=model)
    
    def get_index(self, model):
        """Provide the index that're being used for a particular model."""
        ct = self.get_model_ct(model)
        
        if ct not in self._registry:
            raise NotRegistered('The model %s is not registered' % ct)
        
        return self._registry[ct]
    
    def get_indexes(self):
        """Provide a dict of all indexes that're being used."""
        return self._registry
    
    def get_indexed_models(self):
        """Provide a list of all models being indexed."""
        model_list = []
        model_cts = self._registry.keys()
        
        for ct in model_cts:
            model_list.append(self.get_model(ct))
        
        return model_list
    
    def build_unified_schema(self):
        """
        Builds a list of all fields appearing in any of the SearchIndexes registered
        with a site.
    
        This is useful when building a schema for an engine. A list of dictionaries
        is returned, with each dictionary being a field and the attributes about the
        field. Valid keys are 'field', 'type', 'indexed' and 'multi_valued'.
    
        With no arguments, it will pull in the main site to discover the available
        SearchIndexes.
        """
        content_field_name = ''
        fields = []
        field_names = set()
    
        for model, index in self.get_indexes().items():
            for field_name, field_object in index.fields.items():
                if field_name in field_names:
                    # We've already got this field in the list. Skip.
                    continue
            
                field_names.add(field_name)
                field_data = {
                    'field_name': field_name,
                    'type': 'text',
                    'indexed': 'true',
                    'multi_valued': 'false',
                }
            
                if field_object.document is True:
                    content_field_name = field_name
            
                if field_object.indexed is False:
                    field_data['indexed'] = 'false'
            
                if isinstance(field_object, DateField) or isinstance(field_object, DateTimeField):
                    field_data['type'] = 'date'
                elif isinstance(field_object, IntegerField):
                    field_data['type'] = 'slong'
                elif isinstance(field_object, FloatField):
                    field_data['type'] = 'sfloat'
                elif isinstance(field_object, BooleanField):
                    field_data['type'] = 'boolean'
                elif isinstance(field_object, MultiValueField):
                    field_data['multi_valued'] = 'true'
        
                fields.append(field_data)
    
        return (content_field_name, fields)


# The common case. Feel free to override/replace/define your own in your URLconfs.
site = SearchSite()
