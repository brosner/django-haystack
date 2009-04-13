from django.core.management.base import NoArgsCommand
from django.template import loader, Context
from haystack.constants import DEFAULT_OPERATOR


class Command(NoArgsCommand):
    help = "Generates a Solr schema that reflects the indexes."
    
    def handle_noargs(self, **options):
        """Generates a Solr schema that reflects the indexes."""
        # Cause the default site to load.
        from django.conf import settings
        from haystack.models import load_searchindexes
        load_searchindexes(None)
        from haystack.sites import site
        
        default_operator = getattr(settings, 'HAYSTACK_DEFAULT_OPERATOR', DEFAULT_OPERATOR)
        content_field_name, fields = site.build_unified_schema()
        
        t = loader.get_template('search_configuration/solr.xml')
        c = Context({
            'content_field_name': content_field_name,
            'fields': fields,
            'default_operator': default_operator,
        })
        schema_xml = t.render(c)
        print
        print
        print
        print "Save the following output to 'schema.xml' and place it in your Solr configuration directory."
        print '--------------------------------------------------------------------------------------------'
        print
        print schema_xml
