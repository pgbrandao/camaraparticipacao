from django.conf import settings
from django.db import connections, models, transaction, IntegrityError

import tenacity

from .common import *

@tenacity.retry(**TENACITY_ARGUMENTS)
@transaction.atomic
def load_comentarios_portal():
    if 'comentarios_portal' not in settings.DATABASES:
        print('Comentarios portal connection not available')
        return
 
    with connections['default'].cursor() as cursor:
        # model_mappings follow this format: (source_table_name, model)
        models = (
            get_model('PortalComentario'),
            get_model('PortalComentarioPosicionamento'),
        )

        for model in model_mappings:
            target_table_name = model._meta.db_table

            cursor.execute('ALTER TABLE public."%s" DISABLE TRIGGER ALL;' % (target_table_name,))
            cursor.execute('DELETE FROM public."%s"' % (target_table_name,))

            instance_list = []

            field_list = []
            for field in model._meta.fields:
                if field.name == 'local_id':
                    pass
                elif isinstance(field, models.ForeignKey):
                    field_list.append('{}_id'.format(field.name))
                else:
                    field_list.append(field.name)

            for _, _, _, qs in batch_qs(model.objects.using('comentarios_portal')):
                instance_list = []

                for instance_values in qs.values(*field_list):
                    instance_list.append(
                        model(**instance_values)
                    )

                model.objects.using('default').bulk_create(instance_list)

            cursor.execute('ALTER TABLE public."%s" ENABLE TRIGGER ALL;' % (target_table_name,))

            print('Loaded %s' % (target_table_name,))
