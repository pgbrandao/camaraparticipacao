from django.conf import settings
from django.db import connections, transaction, IntegrityError

import tenacity

from .common import *

@tenacity.retry(**TENACITY_ARGUMENTS)
@transaction.atomic
def load_prisma():
    if 'prisma' not in settings.DATABASES:
        print('Prisma connection not available')
        return
 
    with connections['default'].cursor() as cursor:
        # model_mappings follow this format: (source_table_name, model)
        model_mappings = (
            ('vwAssunto', get_model('PrismaAssunto')),
            ('vwCategoria', get_model('PrismaCategoria')),
            ('vwDemanda', get_model('PrismaDemanda')),
            ('vwDemandante', get_model('PrismaDemandante')),
            ('vwMensagem', get_model('PrismaMensagem')),
        )

        for source_table_name, model in model_mappings:
            target_table_name = model._meta.db_table

            cursor.execute('ALTER TABLE public."%s" DISABLE TRIGGER ALL;' % (target_table_name,))
            cursor.execute('DELETE FROM public."%s"' % (target_table_name,))

            instance_list = []

            # TODO: Find a better way to do this.
            model._meta.db_table = source_table_name

            for _, _, _, qs in batch_qs(model.objects.using('prisma')):
                instance_list = []

                for instance_values in qs.values():
                    instance_list.append(
                        model(**instance_values)
                    )

                # TODO: Find a better way to do this.
                model._meta.db_table = target_table_name
                model.objects.using('default').bulk_create(instance_list)
                model._meta.db_table = source_table_name

            # TODO: Find a better way to do this.
            model._meta.db_table = target_table_name

            cursor.execute('ALTER TABLE public."%s" DISABLE TRIGGER ALL;' % (target_table_name,))

            print('Loaded %s' % (target_table_name,))
