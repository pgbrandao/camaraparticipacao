import boto3
import datetime
import json
import logging
import os
import re
import requests
import sys
import tenacity
import zipfile

import urllib.parse

from collections import defaultdict

from django.conf import settings
from django.db import connections, transaction, IntegrityError
from django.db.models import Count, Sum

from pathlib import Path

from oauth2client.service_account import ServiceAccountCredentials
from oauth2client.client import HttpAccessTokenRefreshError

from django.apps import apps

# Models need to be imported like this in order to avoid cyclic import issues with celery
def get_model(model_name):
    return apps.get_model(app_label='app', model_name=model_name)


logging.basicConfig(stream=sys.stderr, level=logging.ERROR)

logger = logging.getLogger(__name__)

TENACITY_ARGUMENTS = {
    'reraise': True,
    'wait': tenacity.wait_exponential(multiplier=60, max=600),
    'before_sleep': tenacity.before_sleep_log(logger, logging.ERROR, exc_info=True)
}
TENACITY_ARGUMENTS_FAST = {
    'reraise': True,
    'stop': tenacity.stop_after_attempt(5),
    'wait': tenacity.wait_exponential(multiplier=30),
    'before_sleep': tenacity.before_sleep_log(logger, logging.ERROR, exc_info=True)
}

# Google Analytics access token
access_token = None

@tenacity.retry(**TENACITY_ARGUMENTS)
@transaction.atomic
def load_deputados():
    with connections['default'].cursor() as cursor:  
        url = 'https://dadosabertos.camara.leg.br/arquivos/deputados/json/deputados.json'

        r = requests.get(url)
        j = r.json()

        count = len(j['dados'])
        field_values = []
        for row in j['dados']:
            id = int(re.search('/([0-9]*)$', row['uri']).group(1))
            nome = row['nome']
            # TODO: Puxar partido e UF para incorporar aqui.
            nome_processado = '{} (Partido/UF)'.format(nome)

            field_values.append(id)
            field_values.append(nome)
            field_values.append(nome_processado)
        
        
        cursor.execute('ALTER TABLE app_deputado DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_deputado')
        sql = 'INSERT INTO app_deputado (id, nome, nome_processado) VALUES %s' % \
            ', '.join('(%s, %s, %s)' for i in range(count))
        cursor.execute(sql, field_values)
        cursor.execute('ALTER TABLE app_deputado ENABLE TRIGGER ALL;')

        print("Loaded deputados")

@tenacity.retry(**TENACITY_ARGUMENTS)
@transaction.atomic
def load_orgaos():
    with connections['default'].cursor() as cursor:  
        url = 'https://dadosabertos.camara.leg.br/api/v2/orgaos?ordem=ASC&ordenarPor=id'

        count = 0
        field_values = []
        
        while (True):
            r = requests.get(url, headers={ 'accept': 'application/json' })
            j = r.json()

            for row in j['dados']:
                count += 1
                field_values.append(row['id'])
                field_values.append(row['sigla'])
                field_values.append(row['nome'])
            
            # Get URL of next page or break out of while
            is_next_link = [l['rel']=='next' for l in j['links']]
            if any(is_next_link):
                idx = next(i for i, x in enumerate(is_next_link) if x == True)
                url = j['links'][idx]['href']
            else:
                break

        cursor.execute('ALTER TABLE app_orgao DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_orgao')
        sql = 'INSERT INTO app_orgao (id, sigla, nome) VALUES %s' % \
            ', '.join('(%s, %s, %s)' for i in range(count))
        cursor.execute(sql, field_values)
        cursor.execute('ALTER TABLE app_orgao ENABLE TRIGGER ALL;')

        print("Loaded orgaos")

@tenacity.retry(**TENACITY_ARGUMENTS)
@transaction.atomic
def load_proposicoes():
    with connections['default'].cursor() as cursor:  
        cursor.execute('ALTER TABLE app_proposicao DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_proposicao')

        # Dict to store {tex_url_formulario_publicado => ide_formulario_publicado}
        # tex_url_formulario_publicado: ID proposição
        formulario_publicado_dict = {}
        for r in get_model('FormularioPublicado').objects.values_list('ide_formulario_publicado', 'tex_url_formulario_publicado'):
            try:
                formulario_publicado_dict[int(r[1])] = r[0]
            except ValueError:
                pass

        for i in range(2001, datetime.datetime.now().year+1):
            url = 'https://dadosabertos.camara.leg.br/arquivos/proposicoes/json/proposicoes-%s.json' % (i,)

            r = requests.get(url)
            j = r.json()
            
            proposicoes = []

            for p in j['dados']:
                try:
                    orgao_numerador_id = int(re.search('/([0-9]*)$', p['uriOrgaoNumerador']).group(1))
                except AttributeError:
                    orgao_numerador_id = None

                try:
                    ultimo_status_orgao_id = int(re.search('/([0-9]*)$', p['ultimoStatus']['uriOrgao']).group(1))
                except AttributeError:
                    ultimo_status_orgao_id = None

                try:
                    ultimo_status_relator_id = int(re.search('/([0-9]*)$', p['ultimoStatus']['uriRelator']).group(1))
                except AttributeError:
                    ultimo_status_relator_id = None
                
                try:
                    formulario_publicado_id = formulario_publicado_dict[p['id']]
                except KeyError:
                    formulario_publicado_id = None

                # TODO: Improve this for edgier cases
                nome_processado = '{} {}/{}'.format(p['siglaTipo'], p['numero'], p['ano'])

                proposicao = get_model('Proposicao')(
                    id = p['id'],
                    nome_processado = nome_processado,
                    sigla_tipo = p['siglaTipo'],
                    numero = p['numero'],
                    ano = p['ano'],
                    ementa = p['ementa'],
                    ementa_detalhada = p['ementaDetalhada'],
                    keywords = p['keywords'],
                    data_apresentacao = datetime.datetime.strptime(p['dataApresentacao'], "%Y-%m-%dT%H:%M:%S").date(),
                    orgao_numerador_id = orgao_numerador_id,
                    uri_prop_anterior = p['uriPropAnterior'],
                    uri_prop_principal = p['uriPropPrincipal'],
                    uri_prop_posterior = p['uriPropPosterior'],
                    url_inteiro_teor = p['urlInteiroTeor'],
                    formulario_publicado_id = formulario_publicado_id,
                    ultimo_status_situacao_descricao = p['ultimoStatus']['descricaoSituacao'],
                    ultimo_status_data = datetime.datetime.strptime(p['ultimoStatus']['data'], "%Y-%m-%dT%H:%M:%S").date(),
                    ultimo_status_relator_id = ultimo_status_relator_id,
                    ultimo_status_orgao_id = ultimo_status_orgao_id,
                )
                proposicoes.append(proposicao)

            get_model('Proposicao').objects.bulk_create(proposicoes)

            print("Loaded proposicoes %d" % (i,))

        cursor.execute('ALTER TABLE app_proposicao ENABLE TRIGGER ALL;')

@tenacity.retry(**TENACITY_ARGUMENTS)
@transaction.atomic
def load_proposicoes_autores():
    with connections['default'].cursor() as cursor:  

        # Create autor instance for all deputados and orgaos
        get_model('Autor').objects.all().delete()
        get_model('Autor').objects.bulk_create(
            [ get_model('Autor')(deputado_id=d.id, nome_processado=d.nome_processado) for d in get_model('Deputado').objects.all() ]
        )
        get_model('Autor').objects.bulk_create(
            [ get_model('Autor')(orgao_id=o.id, nome_processado=o.nome) for o in get_model('Orgao').objects.all() ]
        )

        deputados_autores = { d['id']: d['autor__id'] for d in get_model('Deputado').objects.values('id', 'autor__id') }
        orgaos_autores = { o['id']: o['autor__id'] for o in get_model('Orgao').objects.values('id', 'autor__id') }

        cursor.execute('ALTER TABLE app_proposicao_autor DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_proposicao_autor')

        for i in range(2001, datetime.datetime.now().year+1):
            url = 'https://dadosabertos.camara.leg.br/arquivos/proposicoesAutores/json/proposicoesAutores-%s.json' % (i,)

            r = requests.get(url)
            j = r.json()

            count = 0
            field_values = []
            for row in j['dados']:
                deputado_id = None
                orgao_id = None
                autor_id = None

                try:
                    deputado_id = int(re.search(r'/deputados/([0-9]+)', row['uriAutor']).group(1))
                    if deputados_autores.get(deputado_id):
                        autor_id = deputados_autores[deputado_id]
                    else:
                        deputado_id = None
                except AttributeError:
                    pass

                try:
                    orgao_id = int(re.search(r'/orgaos/([0-9]+)', row['uriAutor']).group(1))
                    if orgaos_autores.get(orgao_id):
                        autor_id = orgaos_autores[orgao_id]
                    else:
                        orgao_id = None
                except AttributeError:
                    pass

                # TODO: Tratar quando o uriAutor não existir
                # (p. ex. sempre que o projeto for de autoria do Senado!!!)

                try:
                    proposicao_id = row['idProposicao']
                except KeyError:
                    proposicao_id = None

                if proposicao_id and autor_id:
                    count += 1
                    field_values.append(proposicao_id)
                    field_values.append(autor_id)
                            
            sql = 'INSERT INTO app_proposicao_autor (proposicao_id, autor_id) VALUES {} ON CONFLICT DO NOTHING' \
                .format(', '.join('(%s, %s)' for i in range(count)))
            cursor.execute(sql, field_values)
            
            print("Loaded proposicoes autores %d" % (i,))
    
        cursor.execute('ALTER TABLE app_proposicao_autor ENABLE TRIGGER ALL;')


@tenacity.retry(**TENACITY_ARGUMENTS)
@transaction.atomic
def load_proposicoes_temas():
    with connections['default'].cursor() as cursor:  
        cursor.execute('ALTER TABLE app_proposicao_tema DISABLE TRIGGER ALL;')
        cursor.execute('ALTER TABLE app_tema DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_proposicao_tema')
        cursor.execute('DELETE FROM app_tema')

        temas_id_set = set()

        for i in range(2001, datetime.datetime.now().year+1):
            url = 'https://dadosabertos.camara.leg.br/arquivos/proposicoesTemas/json/proposicoesTemas-%s.json' % (i,)

            r = requests.get(url)
            j = r.json()

            count = 0
            field_values = []
    
            for row in j['dados']:
                try:
                    proposicao_id = re.search('/([0-9]*)$', row['uriProposicao']).group(1)
                except get_model('Proposicao').DoesNotExist:
                    proposicao_id = None
                
                tema_id = row['codTema']
                if tema_id not in temas_id_set:
                    tema = get_model('Tema').objects.create(
                        id = row['codTema'],
                        nome = row['tema']
                    )
                    temas_id_set.add(row['codTema'])

                if proposicao_id and tema_id:
                    count += 1
                    field_values.append(proposicao_id)
                    field_values.append(tema_id)

            sql = 'INSERT INTO app_proposicao_tema (proposicao_id, tema_id) VALUES %s ON CONFLICT DO NOTHING' % \
                ', '.join('(%s, %s)' for i in range(count))
            cursor.execute(sql, field_values)
            
            print("Loaded proposicoes temas %d" % (i,))

        cursor.execute('ALTER TABLE app_proposicao_tema ENABLE TRIGGER ALL;')
        cursor.execute('ALTER TABLE app_tema ENABLE TRIGGER ALL;')

def batch_qs(qs, batch_size=1000):
    """
    Returns a (start, end, total, queryset) tuple for each batch in the given
    queryset. Useful when memory is an issue. Picked from djangosnippets.
    """
    total = qs.count()

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        yield (start, end, total, qs[start:end])

@tenacity.retry(**TENACITY_ARGUMENTS)
@transaction.atomic
def load_enquetes():
    if 'enquetes' not in settings.DATABASES:
        print('Enquetes connection not available')
        return
 
    with connections['default'].cursor() as cursor:

        process_models = [get_model('FormularioPublicado'), get_model('Resposta'), get_model('ItemResposta'), get_model('Posicionamento')]

        for model in process_models:
            table_name = model._meta.db_table

            cursor.execute('ALTER TABLE public."%s" DISABLE TRIGGER ALL;' % (table_name,))
            cursor.execute('DELETE FROM public."%s"' % (table_name,))

            field_list = []                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                
            instance_list = []

            for _, _, _, qs in batch_qs(model.objects.using('enquetes')):
                instance_list = []

                for instance_values in qs.values(*field_list):
                    instance_list.append(
                        model(**instance_values)
                    )

                model.objects.using('default').bulk_create(instance_list)

            cursor.execute('ALTER TABLE public."%s" DISABLE TRIGGER ALL;' % (table_name,))

            print('Loaded enquetes %s' % (table_name,))

@tenacity.retry(**TENACITY_ARGUMENTS)
def get_analytics(date, metrics, dimensions, sort, filters, start_index, max_results):
    global access_token

    if not access_token:
        access_token = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(os.environ['ANALYTICS_CREDENTIALS']), 'https://www.googleapis.com/auth/analytics.readonly').get_access_token().access_token
    
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

@tenacity.retry(**TENACITY_ARGUMENTS_FAST)
def load_noticia(id):
    r = requests.get("https://camaranews.camara.leg.br/wp-json/conteudo-portal/{}".format(str(id)))

    # This is a huge kludge because the \u0000 character is invalid in JSON strings.
    # requests .json() will let this slip by.
    c = r.content.replace(b'\u0000', b'')
    j = json.loads(c)

    if not id or j.get('code') == 'not_found':
        return False

    noticia_id = j.get('id')
    tipo_conteudo = j.get('tipo_conteudo')
    link = j.get('link')
    titulo = j.get('titulo')
    data = j.get('data')
    data_atualizacao = j.get('data_atualizacao')
    conteudo = j.get('conteudo')
    resumo = j.get('resumo')

    # Salvar toda proposta associada à notícia
    proposicoes_ids = set()

    proposicao_principal = j.get('proposicao_principal')
    if proposicao_principal:
        proposicoes_ids.add(int(proposicao_principal))

    projeto_lei_principal = j.get('projeto_lei_principal')
    if projeto_lei_principal:
        proposicoes_ids.add(int(projeto_lei_principal))

    proposicoes = j.get('proposicoes')
    if proposicoes:
        for p in proposicoes:
            proposicoes_ids.add(int(p))

    projetos_de_lei = j.get('projetos_de_lei')
    if projetos_de_lei:
        for p in projetos_de_lei:
            proposicoes_ids.add(int(p))

    proposicoes_list = []
    for p in proposicoes_ids:
        try:
            proposicoes_list.append(get_model('Proposicao').objects.get(pk=p))
        except get_model('Proposicao').DoesNotExist:
            pass
    
    # Salvar todo deputado associado à notícia
    deputados_list = []
    if j.get('deputados'):
        for d in j.get('deputados'):
            try:
                deputados_list.append(get_model('Deputado').objects.get(pk=d))
            except get_model('Deputado').DoesNotExist:
                pass


    noticia = get_model('Noticia').objects.create(
        pk = noticia_id,
        tipo_conteudo = tipo_conteudo,
        link = link,
        titulo = titulo,
        data = datetime.datetime.utcfromtimestamp(data) if data else None,
        data_atualizacao = datetime.datetime.utcfromtimestamp(data_atualizacao) if data_atualizacao else None,
        conteudo = conteudo,
        resumo = resumo,
        raw_data = j
    )
    noticia.proposicoes.set(proposicoes_list)
    noticia.deputados.set(deputados_list)

    return True


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

def db_dump():
    sql_path = Path(settings.DB_DUMP_PATH) / Path('latest_dump.sql')
    zip_path = Path(settings.DB_DUMP_PATH) / Path('latest_dump.zip')
    os.system('PGPASSWORD="{}" pg_dumpall -c --host={} --username={} > {}'.format(
        settings.DATABASES['default']['PASSWORD'],
        settings.DATABASES['default']['HOST'],
        settings.DATABASES['default']['USER'],
        sql_path
    ))
    zipfile.ZipFile(
        zip_path, mode='w'
    ).write(sql_path)
    os.system('rm {}'.format(
        sql_path
    ))