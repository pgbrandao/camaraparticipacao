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
        models = (
            get_model('EnqueteFormularioPublicado'),
            get_model('EnqueteResposta'),
            get_model('EnqueteItemResposta'),
            get_model('EnquetePosicionamento'),
        )

        for model in models:
            target_table_name = model._meta.db_table

            cursor.execute('ALTER TABLE public."%s" DISABLE TRIGGER ALL;' % (target_table_name,))
            cursor.execute('DELETE FROM public."%s"' % (target_table_name,))

            instance_list = []

            for _, _, _, qs in batch_qs(model.objects.using('enquetes')):
                instance_list = []

                for instance_values in qs.values():
                    instance_list.append(
                        model(**instance_values)
                    )

                model.objects.using('default').bulk_create(instance_list)

            cursor.execute('ALTER TABLE public."%s" ENABLE TRIGGER ALL;' % (target_table_name,))

            print('Loaded %s' % (target_table_name,))
