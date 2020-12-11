from collections import defaultdict

import datetime

from django.db import connections, transaction

from .common import *

@transaction.atomic
def preprocess():
    with connections['default'].cursor() as cursor:  
        cursor.execute('ALTER TABLE app_proposicaoaggregated DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_proposicaoaggregated')

        initial_date = datetime.date(year=2019, month=1, day=1)
        daterange = [datetime.date.today() - datetime.timedelta(days=i) for i in range(1, (datetime.date.today() - initial_date).days + 1)]
        for date in daterange:

            pa = defaultdict(lambda:{
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
                pa[row.proposicao_id]['ficha_pageviews'] = row.pageviews

            noticia_pageviews_qs = get_model('NoticiaPageviews').objects \
                .filter(date=date) \
                .values('date', 'pageviews', 'noticia__proposicoes__pk')

            for row in noticia_pageviews_qs:
                proposicao_id = row['noticia__proposicoes__pk']
                pageviews = row['pageviews']

                if proposicao_id:
                    # Operator += is super important here
                    # (since each proposicao has more than one noticia)
                    pa[proposicao_id]['noticia_pageviews'] += pageviews

            # Poll votes
            votes_qs = get_model('Resposta').objects \
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

                pa[proposicao_id]['poll_votes'] = poll_votes

            # Poll comments
            comment_status_mappings = [
                ({}, 'poll_comments'),
                ({'cod_autorizado': 0}, 'poll_comments_unchecked'),
                ({'cod_autorizado__in': [1, 2]}, 'poll_comments_checked'),
                ({'cod_autorizado': 1}, 'poll_comments_authorized'),
                ({'cod_autorizado': 2}, 'poll_comments_unauthorized')
            ]

            for filter_args, target_field in comment_status_mappings:
                comments_qs = get_model('Posicionamento').objects \
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

                    pa[proposicao_id][target_field] = poll_comments


            pa_list = [get_model('ProposicaoAggregated')(
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
                ) for k, v in pa.items()]
            get_model('ProposicaoAggregated').objects.bulk_create(pa_list)

        cursor.execute('ALTER TABLE app_proposicaoaggregated ENABLE TRIGGER ALL;')

        print('Finished preprocess')
