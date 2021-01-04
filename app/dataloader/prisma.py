from django.conf import settings
from django.db import connections, models, transaction, IntegrityError

import tenacity

from .common import *

@tenacity.retry(**TENACITY_ARGUMENTS)
@transaction.atomic
def load_prisma():
    if 'prisma' not in settings.DATABASES:
        print('Prisma connection not available')
        return
 
    with connections['default'].cursor() as cursor:
        models = (
            get_model('PrismaAssunto'),
            get_model('PrismaCategoria'),
            get_model('PrismaDemanda'),
            get_model('PrismaDemandante'),
        )

        for model in models:
            target_table_name = model._meta.db_table

            cursor.execute('ALTER TABLE public."%s" DISABLE TRIGGER ALL;' % (target_table_name,))
            cursor.execute('DELETE FROM public."%s"' % (target_table_name,))

            instance_list = []

            # Remove local_id from queries to the source table
            field_list = []
            for field in model._meta.fields:
                if field.name == 'local_id':
                    pass
                elif isinstance(field, models.ForeignKey):
                    field_list.append('{}_id'.format(field.name))
                else:
                    field_list.append(field.name)

            # In models which would be ordered by local_id,
            # change ordering to another foreign key
            model_qs = model.objects.using('prisma')
            if (model._meta.pk.name == 'local_id'):
                fk_field = [field for field in model._meta.fields if isinstance(field, models.ForeignKey)][0]
                model_qs = model_qs.order_by(fk_field.name)

            for _, _, _, qs in batch_qs(model_qs):
                instance_list = []

                for instance_values in qs.values(*field_list):
                    instance_list.append(
                        model(**instance_values)
                    )

                model.objects.using('default').bulk_create(instance_list)

            cursor.execute('ALTER TABLE public."%s" ENABLE TRIGGER ALL;' % (target_table_name,))

            print('Loaded %s' % (target_table_name,))
