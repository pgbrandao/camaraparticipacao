from collections import defaultdict

import datetime

from django.db import connections, transaction
from django.db.models import Count

from .common import *

@transaction.atomic
def preprocess_proposicoes():
    with connections['default'].cursor() as cursor:  
        cursor.execute('ALTER TABLE app_proposicaoaggregated DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_proposicaoaggregated')

        initial_date = datetime.date(year=2019, month=1, day=1)
        daterange = [datetime.date.today() - datetime.timedelta(days=i) for i in range(1, (datetime.date.today() - initial_date).days + 1)]
        for date in daterange:

            aggregated_dict = defaultdict(lambda:{
                'ficha_pageviews': 0, 
                'noticia_pageviews': 0, 
                'poll_votes': 0, 
                'poll_comments': 0, 
                'poll_comments_unchecked': 0, 
                'poll_comments_checked': 0, 
                'poll_comments_authorized': 0, 
                'poll_comments_unauthorized': 0})

            ficha_pageviews_qs = get_model('ProposicaoFichaPageviews').objects.filter(date=date)

            for row in ficha_pageviews_qs:
                aggregated_dict[row.proposicao_id]['ficha_pageviews'] = row.pageviews

            noticia_pageviews_qs = get_model('NoticiaPageviews').objects \
                .filter(date=date) \
                .values('date', 'pageviews', 'noticia__proposicoes__pk')

            for row in noticia_pageviews_qs:
                proposicao_id = row['noticia__proposicoes__pk']
                pageviews = row['pageviews']

                if proposicao_id:
                    # Operator += is super important here
                    # (since each proposicao has more than one noticia)
                    aggregated_dict[proposicao_id]['noticia_pageviews'] += pageviews

            # Poll votes
            votes_qs = get_model('EnqueteResposta').objects \
                .filter(dat_resposta__year=date.year) \
                .filter(dat_resposta__month=date.month) \
                .filter(dat_resposta__day=date.day) \
                .values('ide_formulario_publicado__proposicao') \
                .annotate(votes_count=Count('ide_resposta')) \
                .values('ide_formulario_publicado__proposicao','votes_count')

            for row in votes_qs:
                if not row['ide_formulario_publicado__proposicao']:
                    continue

                proposicao_id = row['ide_formulario_publicado__proposicao']
                poll_votes = row['votes_count']

                aggregated_dict[proposicao_id]['poll_votes'] = poll_votes

            # Poll comments
            comment_status_mappings = [
                ({}, 'poll_comments'),
                ({'cod_autorizado': 0}, 'poll_comments_unchecked'),
                ({'cod_autorizado__in': [1, 2]}, 'poll_comments_checked'),
                ({'cod_autorizado': 1}, 'poll_comments_authorized'),
                ({'cod_autorizado': 2}, 'poll_comments_unauthorized')
            ]

            for filter_args, target_field in comment_status_mappings:
                comments_qs = get_model('EnquetePosicionamento').objects \
                    .filter(dat_posicionamento__year=date.year) \
                    .filter(dat_posicionamento__month=date.month) \
                    .filter(dat_posicionamento__day=date.day) \
                    .filter(**filter_args) \
                    .values('ide_formulario_publicado__proposicao') \
                    .annotate(comments_count=Count('ide_posicionamento')) \
                    .values('ide_formulario_publicado__proposicao','comments_count')

                for row in comments_qs:
                    if not row['ide_formulario_publicado__proposicao']:
                        continue

                    proposicao_id = row['ide_formulario_publicado__proposicao']
                    poll_comments = row['comments_count']

                    aggregated_dict[proposicao_id][target_field] = poll_comments


            aggregated_dict_list = [get_model('ProposicaoAggregated')(
                proposicao_id=k,
                date=date,
                ficha_pageviews=v['ficha_pageviews'],
                noticia_pageviews=v['noticia_pageviews'],
                poll_votes=v['poll_votes'],
                poll_comments=v['poll_comments'],
                poll_comments_unchecked=v['poll_comments_unchecked'],
                poll_comments_checked=v['poll_comments_checked'],
                poll_comments_authorized=v['poll_comments_authorized'],
                poll_comments_unauthorized=v['poll_comments_unauthorized'],
                ) for k, v in aggregated_dict.items()]
            get_model('ProposicaoAggregated').objects.bulk_create(aggregated_dict_list)

        cursor.execute('ALTER TABLE app_proposicaoaggregated ENABLE TRIGGER ALL;')

        print('Finished proposicoes preprocess')

@transaction.atomic
def preprocess_noticias():
    with connections['default'].cursor() as cursor:  
        cursor.execute('ALTER TABLE app_noticiaaggregated DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_noticiaaggregated')

        initial_date = datetime.date(year=2019, month=1, day=1)
        daterange = [datetime.date.today() - datetime.timedelta(days=i) for i in range(1, (datetime.date.today() - initial_date).days + 1)]
        for date in daterange:

            aggregated_dict = defaultdict(lambda:{
                'pageviews': 0, 
                'portal_comments': 0,
                'portal_comments_unchecked': 0,
                'portal_comments_authorized': 0,
                'portal_comments_unauthorized': 0})

            # Pageviews
            noticia_pageviews_qs = get_model('NoticiaPageviews').objects.filter(date=date)

            for row in noticia_pageviews_qs:
                aggregated_dict[row.noticia_id]['pageviews'] = row.pageviews

            # Portal comments
            comment_status_mappings = [
                ({}, 'portal_comments'),
                ({'situacao': 'PENDENTE'}, 'portal_comments_unchecked'),
                ({'situacao': 'APROVADO'}, 'portal_comments_authorized'),
                ({'situacao': 'REPROVADO'}, 'portal_comments_unauthorized')
            ]

            for filter_args, target_field in comment_status_mappings:

                comments_qs = get_model('PortalComentario').objects \
                    .filter(data__year=date.year) \
                    .filter(data__month=date.month) \
                    .filter(data__day=date.day) \
                    .filter(**filter_args) \
                    .values('url') \
                    .annotate(comments_count=Count('id')) \
                    .values('url', 'comments_count')
            
                for row in comments_qs:
                    if not row['url']:
                        continue

                    noticia_id = int(row['url'])
                    poll_comments = row['comments_count']

                    aggregated_dict[noticia_id][target_field] = poll_comments


            aggregated_dict_list = [get_model('NoticiaAggregated')(
                noticia_id=k,
                date=date,
                pageviews=v['pageviews'],
                portal_comments=v['portal_comments'],
                portal_comments_unchecked=v['portal_comments_unchecked'],
                portal_comments_authorized=v['portal_comments_authorized'],
                portal_comments_unauthorized=v['portal_comments_unauthorized'],
                ) for k, v in aggregated_dict.items()]
            get_model('NoticiaAggregated').objects.bulk_create(aggregated_dict_list)

        cursor.execute('ALTER TABLE app_noticiaaggregated ENABLE TRIGGER ALL;')

        print('Finished noticias preprocess')



@transaction.atomic
def preprocess_daily_summary():
    with connections['default'].cursor() as cursor:  
        cursor.execute('ALTER TABLE app_dailysummary DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_dailysummary')

        initial_date = datetime.date(year=2019, month=1, day=1)
        daterange = [datetime.date.today() - datetime.timedelta(days=i) for i in range(1, (datetime.date.today() - initial_date).days + 1)]
        for date in daterange:

            aggregated_dict = defaultdict(lambda:{
                'atendimentos': 0, 
            })

            # Demandas (Prisma)
            demanda_canal_mappings = [
                ({}, 'atendimentos'),
            ]

            for filter_args, target_field in demanda_canal_mappings:

                demandas_count = get_model('PrismaDemanda').objects \
                    .filter(demanda_data_criação__year=date.year) \
                    .filter(demanda_data_criação__month=date.month) \
                    .filter(demanda_data_criação__day=date.day) \
                    .filter(**filter_args) \
                    .count()
            
                aggregated_dict[target_field] = demandas_count


            daily_summary = get_model('DailySummary')(
                date=date,
                atendimentos=aggregated_dict['atendimentos'],
            )
            get_model('DailySummary').objects.bulk_create([daily_summary])

        cursor.execute('ALTER TABLE app_dailysummary ENABLE TRIGGER ALL;')

        print('Finished daily summary preprocess')
