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
            { 'model': get_model('PrismaAssunto'),
              'table_name': '"SqlProPrisma"."dbo"."vwAssunto"',
              'order_field': '"Assunto.IdDemanda"',
              'fields':
                [ \
                    { 'django_field': 'assunto_iddemanda'                     , 'sql_server_field': 'Assunto.IdDemanda'                  } ,
                    { 'django_field': 'assunto_nome'                          , 'sql_server_field': 'Assunto.Nome'                       } ,
                ],
            },
            { 'model': get_model('PrismaCategoria'),
              'table_name': '"SqlProPrisma"."dbo"."vwCategoria"',
              'order_field': '"IdDemanda"',
              'fields':
                [ \
                    { 'django_field': 'iddemanda'                             , 'sql_server_field': 'IdDemanda'                          } ,
                    { 'django_field': 'macrotema'                             , 'sql_server_field': 'Macrotema'                          } ,
                    { 'django_field': 'tema'                                  , 'sql_server_field': 'Tema'                               } ,
                    { 'django_field': 'subtema'                               , 'sql_server_field': 'Subtema'                            } ,
                    { 'django_field': 'categoria_posicionamento'              , 'sql_server_field': 'Categoria.Posicionamento'           } ,
                    { 'django_field': 'categoria_legislativo'                 , 'sql_server_field': 'Categoria.Legislativo'              } ,
                    { 'django_field': 'categoria_deputado'                    , 'sql_server_field': 'Categoria.Deputado'                 } ,
                    { 'django_field': 'categoria_legislação'                  , 'sql_server_field': 'Categoria.Legislação'               } ,
                    { 'django_field': 'categoria_debate_nacional'             , 'sql_server_field': 'Categoria.Debate Nacional'          } ,
                    { 'django_field': 'categoria_orcamento'                   , 'sql_server_field': 'Categoria.Orçamento'                } ,
                    { 'django_field': 'categoria_tema_proposição'             , 'sql_server_field': 'Categoria.Tema Proposição'          } ,
                ],
            },
            { 'model': get_model('PrismaDemanda'),
              'table_name': '"SqlProPrisma"."dbo"."vwDemanda"',
              'order_field': '"IdDemanda"',
              'fields':
                [ \
                    { 'django_field': 'iddemanda'                             , 'sql_server_field': 'IdDemanda'                          } ,
                    { 'django_field': 'iddemandante'                          , 'sql_server_field': 'IdDemandante'                       } ,
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
            },
            { 'model': get_model('PrismaDemandante'),
              'table_name': '"SqlProPrisma"."dbo"."vwDemandante"',
              'order_field': '"IdDemandante"',
              'fields':
                [ \
                    { 'django_field': 'iddemandante'                          , 'sql_server_field': 'IdDemandante'                       } ,
                    { 'django_field': 'demandante_data_cadastro'              , 'sql_server_field': 'Demandante.Data Cadastro'           } ,
                    { 'django_field': 'demandante_grau_de_instrução'          , 'sql_server_field': 'Demandante.Grau de Instrução'       } ,
                    { 'django_field': 'demandante_sexo'                       , 'sql_server_field': 'Demandante.Sexo'                    } ,
                    { 'django_field': 'demandante_categoria'                  , 'sql_server_field': 'Demandante.Categoria'               } ,
                    { 'django_field': 'demandante_data_de_nascimento'         , 'sql_server_field': 'Demandante.Data de Nascimento'      } ,
                    { 'django_field': 'demandante_profissão_externa'          , 'sql_server_field': 'Demandante.Profissão Externa'       } ,
                ],
            },
        ]

        for m in models_list:
            target_table_name = model._meta.db_table

            default_cursor.execute('ALTER TABLE public."%s" DISABLE TRIGGER ALL;' % (target_table_name,))
            default_cursor.execute('DELETE FROM public."%s"' % (target_table_name,))

            instance_list = []

            fields_list = ', '.join(['"'+field['sql_server_field']+'"' for field in m['fields']])
            table_name = m['table_name']
            order_field = m['order_field']

            num_rows = prisma_cursor.execute('SELECT COUNT(*) FROM {m.table_name};').fetchone()[0]

            for i in range(1,num_rows, 50000):
                instance_list = []

                query = f'SELECT {fields_list} ' + \
                        f'FROM (' + \
                            f'SELECT {fields_list}, ROW_NUMBER() OVER (ORDER BY {order_field}) AS RowNum' + \
                        f'FROM {table_name}' + \
                        f') AS MyDerivedTable' + \
                        f'WHERE MyDerivedTable.RowNum BETWEEN {i} AND {i+50000}'
                rows = prisma_cursor.execute(query)

                for row in rows:
                    instance_values = {}
                    for col_number, field in enumerate(m['fields']):
                        instance_values[field['django_field']] = row[col_number]

                    instance_list.append(
                        model(**instance_values)
                    )

                model.objects.using('default').bulk_create(instance_list)

            cursor.execute('ALTER TABLE public."%s" ENABLE TRIGGER ALL;' % (target_table_name,))

            print('Loaded %s' % (target_table_name,))

