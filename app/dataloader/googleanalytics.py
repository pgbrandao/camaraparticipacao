import datetime
import json
import tenacity
import re
import requests
import urllib.parse

from django.conf import settings
from django.db import connections, transaction, IntegrityError

from oauth2client.service_account import ServiceAccountCredentials

from .common import *
from .noticias import load_noticia

# Google Analytics access token
access_token = None

@tenacity.retry(**TENACITY_ARGUMENTS)
def get_analytics(date, metrics, dimensions, sort, filters, start_index, max_results):
    global access_token

    if not access_token:
        access_token = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(settings.ANALYTICS_CREDENTIALS), 'https://www.googleapis.com/auth/analytics.readonly').get_access_token().access_token
    
    url = ('https://www.googleapis.com/analytics/v3/data/ga'
        +'?ids=ga%3A48889682'
        +'&start-date='+date.strftime("%Y-%m-%d")
        +'&end-date='+date.strftime("%Y-%m-%d")
        +'&metrics='+urllib.parse.quote(metrics)
        +'&dimensions='+urllib.parse.quote(dimensions)
        +'&sort='+urllib.parse.quote(sort)
        +'&filters='+urllib.parse.quote(filters)
        +'&start-index='+str(start_index)
        +'&max-results='+str(max_results)
        +'&access_token='+access_token)

    r = requests.get(url)
    data = r.json()

    # There should always be rows. Otherwise something went wrong.
    try:
        data['rows']
    except KeyError:
        print(data)

        try:
            if data['error']['code'] == 401:
                # 401: Unauthorized (most likely invalid credentials)
                access_token = None
                print('New access token probably needed. Will be tried next time.')
        except KeyError:
            pass

        raise

    return data

@tenacity.retry(**TENACITY_ARGUMENTS)
def load_analytics_fichas(initial_date=None):
    proposicao_ids = set(get_model('Proposicao').objects.values_list('id', flat=True))

    if not initial_date:
        # By default the last 3 months
        daterange = [datetime.date.today() - datetime.timedelta(days=i) for i in range(1,93)]
    else:
        daterange = [datetime.date.today() - datetime.timedelta(days=i) for i in range(1,(datetime.date.today() - initial_date).days + 1)]

    for date in daterange:
        with transaction.atomic():
            if get_model('ProposicaoFichaPageviews').objects.filter(date=date).count() > 0:
                continue

            pageviews_dict = {}
            
            i = 1
            while (True):
                data = get_analytics(
                    date=date,
                    metrics='ga:pageviews',
                    dimensions='ga:pagePath,ga:date',
                    sort='-ga:pageviews',
                    filters='ga:pagePath=~^/proposicoesWeb/fichadetramitacao,ga:pagePath=~^/propostas-legislativas/',
                    start_index=i,
                    max_results=10000
                )

                for row in data['rows']:
                    page_path = row[0]
                    date = datetime.datetime.strptime(row[1], "%Y%m%d").date()
                    pageviews = int(row[2])

                    id_proposicao = None

                    r = re.search('^/proposicoesWeb/fichadetramitacao\?.*idProposicao=([0-9]+)', page_path)
                    if r:
                        id_proposicao = int(r.group(1))

                    r = re.search('^/propostas-legislativas/([0-9]+)', page_path)
                    if r:
                        id_proposicao = int(r.group(1))
                    pageviews_dict[id_proposicao] = pageviews_dict.get(id_proposicao, 0) + pageviews

                try:
                    data['nextLink']
                    i += 10000
                except KeyError:
                    break
            proposicao_ficha_pageview_list = []
            for proposicao_id, pageviews in pageviews_dict.items():
                if proposicao_id in proposicao_ids:
                    proposicao_ficha_pageview_list.append(get_model('ProposicaoFichaPageviews')(
                        proposicao_id=proposicao_id,
                        pageviews=pageviews,
                        date=date
                    ))

            get_model('ProposicaoFichaPageviews').objects.bulk_create(proposicao_ficha_pageview_list)
            
            print('Loaded ficha analytics %s' % (date,))


@tenacity.retry(**TENACITY_ARGUMENTS)
def load_analytics_noticias(initial_date=None):
    print('Loading noticias analytics')

    if not initial_date:
        # By default the last 3 months
        daterange = [datetime.date.today() - datetime.timedelta(days=i) for i in range(1,93)]
    else:
        daterange = [datetime.date.today() - datetime.timedelta(days=i) for i in range(1,(datetime.date.today() - initial_date).days + 1)]

    updated_noticias = set()

    for date in daterange:
        with transaction.atomic():
            if get_model('NoticiaPageviews').objects.filter(date=date).count() > 0:
                continue

            pageviews_dict = {}
            
            i = 1
            while (True):
                data = get_analytics(
                    date=date,
                    metrics='ga:pageviews',
                    dimensions='ga:pagePath,ga:date',
                    sort='-ga:pageviews',
                    filters='ga:pagePath=~^/noticias/[0-9],ga:pagePath=~^/radio/programas/[0-9],ga:pagePath=~^/radio/radioagencia/[0-9],ga:pagePath=~^/tv/[0-9]',
                    start_index=i,
                    max_results=10000
                )

                for row in data['rows']:
                    page_path = row[0]
                    # date = datetime.datetime.strptime(row[1], "%Y%m%d").date()
                    pageviews = int(row[2])

                    id_noticia = None

                    r = re.search('^/noticias/([0-9]+).*', page_path)
                    if r:
                        id_noticia = int(r.group(1))

                    r = re.search('^/radio/programas/([0-9]+).*', page_path)
                    if r:
                        id_noticia = int(r.group(1))

                    r = re.search('^/radio/radioagencia/([0-9]+).*', page_path)
                    if r:
                        id_noticia = int(r.group(1))

                    r = re.search('^/tv/([0-9]+).*', page_path)
                    if r:
                        id_noticia = int(r.group(1))

                    pageviews_dict[id_noticia] = pageviews_dict.get(id_noticia, 0) + pageviews

                try:
                    data['nextLink']
                    i += 10000
                except KeyError:
                    break
            
            noticia_pageviews_list = []
            noticia_ids = set(get_model('Noticia').objects.values_list('id', flat=True))

            for noticia_id, pageviews in pageviews_dict.items():
                if noticia_id:
                    # TODO: Currently noticia is only pulled from web service the first time it's encountered
                    # It would be desirable to re-fetch every once in a while (or even every new encounter)
                    if noticia_id not in noticia_ids:
                        if not load_noticia(noticia_id):
                            continue
                        noticia_ids.add(noticia_id)
                    
                    noticia_pageviews_list.append(get_model('NoticiaPageviews')(
                        noticia_id=noticia_id,
                        pageviews=pageviews,
                        date=date
                    ))


        get_model('NoticiaPageviews').objects.bulk_create(noticia_pageviews_list)
        
        print('Loaded noticias analytics %s' % (date,))
