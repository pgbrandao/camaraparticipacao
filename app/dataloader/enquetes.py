from django.conf import settings
from django.db import connections, transaction, IntegrityError

import tenacity

from .common import *

@tenacity.retry(**TENACITY_ARGUMENTS)
@transaction.atomic
def load_enquetes():
    if 'enquetes' not in settings.DATABASES:
        print('Enquetes connection not available')
        return
 
    with connections['default'].cursor() as cursor:
        # model_mappings follow this format: (source_table_name, model)
        model_mappings = (
            ('Formulario_Publicado', get_model('EnqueteFormularioPublicado')),
            ('Resposta', get_model('EnqueteResposta')),
            ('Item_Resposta', get_model('EnqueteItemResposta')),
            ('Posicionamento', get_model('EnquetePosicionamento')),
        )

        for source_table_name, model in model_mappings:
            target_table_name = model._meta.db_table

            cursor.execute('ALTER TABLE public."%s" DISABLE TRIGGER ALL;' % (target_table_name,))
            cursor.execute('DELETE FROM public."%s"' % (target_table_name,))

            instance_list = []

            rename_model_table(model, source_table_name)

            for _, _, _, qs in batch_qs(model.objects.using('enquetes')):
                instance_list = []

                for instance_values in qs.values():
                    instance_list.append(
                        model(**instance_values)
                    )

                rename_model_table(model, target_table_name)
                model.objects.using('default').bulk_create(instance_list)
                rename_model_table(model, source_table_name)

            rename_model_table(model, target_table_name)

            cursor.execute('ALTER TABLE public."%s" DISABLE TRIGGER ALL;' % (target_table_name,))

            print('Loaded %s' % (target_table_name,))
