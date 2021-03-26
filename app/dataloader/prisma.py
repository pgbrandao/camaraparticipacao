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
 
    with connections['default'].cursor() as default_cursor, \
         connections['prisma'].cursor() as prisma_cursor:

        models_list = [
            # get_model('PrismaAssunto'),
            # get_model('PrismaCategoria'),
            { 'model': get_model('PrismaDemanda'),
              'table_name': '"SqlProPrisma"."dbo"."vwDemanda"',
              'order_field': '"IdDemanda"',
              'fields':
                [ \
                    { 'django_field': 'iddemanda'                             , 'sql_server_field': 'IdDemanda'                          } ,
                    { 'django_field': 'iddemandante_id'                       , 'sql_server_field': 'IdDemandante'                       } ,
                    { 'django_field': 'demanda_protocolo'                     , 'sql_server_field': 'Demanda.Protocolo'                  } ,
                    { 'django_field': 'demanda_fila'                          , 'sql_server_field': 'Demanda.Fila'                       } ,
                    { 'django_field': 'demanda_prioridade'                    , 'sql_server_field': 'Demanda.Prioridade'                 } ,
                    { 'django_field': 'demanda_canal'                         , 'sql_server_field': 'Demanda.Canal'                      } ,
                    { 'django_field': 'demanda_tipo'                          , 'sql_server_field': 'Demanda.Tipo'                       } ,
                    { 'django_field': 'demanda_data_criação'                  , 'sql_server_field': 'Demanda.Data Criação'               } ,
                    { 'django_field': 'demanda_prazo'                         , 'sql_server_field': 'Demanda.Prazo'                      } ,
                    { 'django_field': 'demanda_prazo_sugerido'                , 'sql_server_field': 'Demanda.Prazo Sugerido'             } ,
                    { 'django_field': 'demanda_data_da_resposta'              , 'sql_server_field': 'Demanda.Data da Resposta'           } ,
                    { 'django_field': 'demanda_tempo_em_aberto'               , 'sql_server_field': 'Demanda.Tempo em Aberto'            } ,
                    { 'django_field': 'demanda_tempo_em_aberto_em_minutos'    , 'sql_server_field': 'Demanda.Tempo em Aberto em Minutos' } , 
                    { 'django_field': 'demanda_tempo_de_trabalho'             , 'sql_server_field': 'Demanda.Tempo de Trabalho'          } ,
                    { 'django_field': 'demanda_titulo'                        , 'sql_server_field': 'Demanda.Titulo'                     } ,
                    { 'django_field': 'demanda_data_da_atualização'           , 'sql_server_field': 'Demanda.Data da Atualização'        } ,
                    { 'django_field': 'demanda_status'                        , 'sql_server_field': 'Demanda.Status'                     } ,
                    { 'django_field': 'demanda_forma_de_recebimento'          , 'sql_server_field': 'Demanda.Forma de Recebimento'       } ,
                    { 'django_field': 'demanda_orgão_interessado'             , 'sql_server_field': 'Demanda.Orgão Interessado'          } ,
                    { 'django_field': 'demanda_resultado_do_atendimento'      , 'sql_server_field': 'Demanda.Resultado do Atendimento'   } ,
                ],
            }
            # get_model('PrismaDemandante'),
        ]

        for model in models_list:
            target_table_name = model['model']._meta.db_table

            default_cursor.execute('ALTER TABLE public."%s" DISABLE TRIGGER ALL;' % (target_table_name,))
            default_cursor.execute('DELETE FROM public."%s"' % (target_table_name,))

            instance_list = []

            fields_list = ', '.join(['"'+field['sql_server_field']+'"' for field in model['fields']])
            table_name = model['table_name']
            order_field = model['order_field']

            num_rows = prisma_cursor.execute(f'SELECT COUNT(*) FROM '+model['table_name']).fetchone()[0]

            for i in range(1,num_rows, 50000):
                instance_list = []

                query = f"""
                SELECT {fields_list}
                FROM (
                    SELECT {fields_list}, ROW_NUMBER() OVER (ORDER BY {order_field}) AS RowNum
                    FROM {table_name}
                ) AS MyDerivedTable
                WHERE MyDerivedTable.RowNum BETWEEN {i} AND {i+50000}
                """
                rows = prisma_cursor.execute(query)

                for row in rows:
                    instance_values = {}
                    for col_number, field in enumerate(model['fields']):
                        instance_values[field['django_field']] = row[col_number]

                    instance_list.append(
                        model['model'](**instance_values)
                    )

                model.objects.using('default').bulk_create(instance_list)

            cursor.execute('ALTER TABLE public."%s" ENABLE TRIGGER ALL;' % (target_table_name,))

            print('Loaded %s' % (target_table_name,))

