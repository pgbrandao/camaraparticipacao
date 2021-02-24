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
        models_list = [ 
            get_model('PortalComentario'),
            get_model('PortalComentarioPosicionamento'),
        ]

        for model in models_list:
            target_table_name = model._meta.db_table

            cursor.execute('ALTER TABLE public."%s" DISABLE TRIGGER ALL;' % (target_table_name,))
            cursor.execute('DELETE FROM public."%s"' % (target_table_name,))

            instance_list = []

            source_field_list = []
            target_field_list = []
            has_local_id = False
            for field in model._meta.fields:
                if field.name == 'local_id':
                    has_local_id = True
                elif isinstance(field, models.ForeignKey):
                    source_field_list.append(field.name)
                    target_field_list.append('{}_id'.format(field.name))
                else:
                    source_field_list.append(field.name)
                    target_field_list.append(field.name)

            if has_local_id:
                # TODO: This needs to be yielded using a qs, like the alternative below, to avoid memory issues.
                instance_list = []
                for row in connections['comentarios_portal'].cursor() \
                    .execute('SELECT {} FROM "{}"'.format(', '.join(source_field_list), model._meta.db_table)):

                    # import pdb;pdb.set_trace()
                    instance_list.append(
                        model(**dict(zip(target_field_list, row)))
                    )
                model.objects.using('default').bulk_create(instance_list)
            else:
                for _, _, _, qs in batch_qs(model.objects.using('comentarios_portal')):
                    instance_list = []

                    for instance_values in qs.values(*target_field_list):
                        instance_list.append(
                            model(**instance_values)
                        )

                    model.objects.using('default').bulk_create(instance_list)

            cursor.execute('ALTER TABLE public."%s" ENABLE TRIGGER ALL;' % (target_table_name,))

            print('Loaded %s' % (target_table_name,))
