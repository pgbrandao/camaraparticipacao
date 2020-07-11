import boto3
import datetime
import json
import os
import re
import zipfile

from collections import defaultdict

from django.conf import settings
from django.db import connections, IntegrityError
from django.db.models import Count, Sum

from oauth2client.service_account import ServiceAccountCredentials
from oauth2client.client import HttpAccessTokenRefreshError

import requests

from django.apps import apps

# Models need to be imported like this in order to avoid cyclic import issues with celery
def get_model(model_name):
    return apps.get_model(app_label='app', model_name=model_name)

def get_http():
    retry_strategy = requests.packages.urllib3.util.retry.Retry(
        total=8,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "POST", "OPTIONS"],
        backoff_factor=2
    )
    adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("https://", adapter)
    http.mount("http://", adapter)
    return http

def load_deputados():
    url = 'https://dadosabertos.camara.leg.br/arquivos/deputados/json/deputados.json'

    r = get_http().get(url)
    j = r.json()

    count = len(j['dados'])
    field_values = []
    for row in j['dados']:
        id = int(re.search('/([0-9]*)$', row['uri']).group(1))
        nome = row['nome']
        field_values.append(id)
        field_values.append(nome)
    

    with connections['default'].cursor() as cursor:  
        cursor.execute('ALTER TABLE app_deputado DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_deputado')
        sql = 'INSERT INTO app_deputado (id, nome) VALUES %s' % \
            ', '.join('(%s, %s)' for i in range(count))
        cursor.execute(sql, field_values)
        cursor.execute('ALTER TABLE app_deputado ENABLE TRIGGER ALL;')
    
    print("Loaded deputados")


def load_orgaos():
    url = 'https://dadosabertos.camara.leg.br/arquivos/orgaos/json/orgaos.json'

    r = get_http().get(url)
    j = r.json()

    count = len(j['dados'])
    field_values = []
    for row in j['dados']:
        field_values.append(int(re.search('/([0-9]*)$', row['uri']).group(1)))
        field_values.append(row['sigla'])
        field_values.append(row['nome'])

    with connections['default'].cursor() as cursor:  
        cursor.execute('ALTER TABLE app_orgao DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_orgao')
        sql = 'INSERT INTO app_orgao (id, sigla, nome) VALUES %s' % \
            ', '.join('(%s, %s, %s)' for i in range(count))
        cursor.execute(sql, field_values)
        cursor.execute('ALTER TABLE app_orgao ENABLE TRIGGER ALL;')
    
    print("Loaded orgaos")

def load_proposicoes():
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

        r = get_http().get(url)
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

            proposicao = get_model('Proposicao')(
                id = p['id'],
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

        with connections['default'].cursor() as cursor:  
            cursor.execute('ALTER TABLE app_proposicao DISABLE TRIGGER ALL;')
            cursor.execute('DELETE FROM app_proposicao')
            get_model('Proposicao').objects.bulk_create(proposicoes)
            cursor.execute('ALTER TABLE app_proposicao ENABLE TRIGGER ALL;')

        print("Loaded proposicoes %d" % (i,))

        
def load_proposicoes_autores():
    with connections['default'].cursor() as cursor:  
        cursor.execute('ALTER TABLE app_proposicao_autor DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_proposicao_autor')

    for i in range(2001, datetime.datetime.now().year+1):
        url = 'https://dadosabertos.camara.leg.br/arquivos/proposicoesAutores/json/proposicoesAutores-%s.json' % (i,)

        r = get_http().get(url)
        j = r.json()

        count = 0
        field_values = []
        for row in j['dados']:
            try:
                deputado_id = row['idDeputadoAutor']
            except KeyError:
                deputado_id = None

            try:
                proposicao_id = row['idProposicao']
            except KeyError:
                proposicao_id = None

            if deputado_id and proposicao_id:
                count += 1
                field_values.append(proposicao_id)
                field_values.append(deputado_id)
        with connections['default'].cursor() as cursor:  
            sql = 'INSERT INTO app_proposicao_autor (proposicao_id, deputado_id) VALUES %s ON CONFLICT DO NOTHING' % \
                ', '.join('(%s, %s)' for i in range(count))
            cursor.execute(sql, field_values)
        
        print("Loaded proposicoes autores %d" % (i,))
    with connections['default'].cursor() as cursor:
        cursor.execute('ALTER TABLE app_proposicao_autor ENABLE TRIGGER ALL;')


def load_proposicoes_temas():
    with connections['default'].cursor() as cursor:  
        cursor.execute('ALTER TABLE app_proposicao_tema DISABLE TRIGGER ALL;')
        cursor.execute('ALTER TABLE app_tema DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_proposicao_tema')
        cursor.execute('DELETE FROM app_tema')

    temas_id_set = set()

    for i in range(2001, datetime.datetime.now().year+1):
        url = 'https://dadosabertos.camara.leg.br/arquivos/proposicoesTemas/json/proposicoesTemas-%s.json' % (i,)

        r = get_http().get(url)
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

        with connections['default'].cursor() as cursor:  
            sql = 'INSERT INTO app_proposicao_tema (proposicao_id, tema_id) VALUES %s ON CONFLICT DO NOTHING' % \
                ', '.join('(%s, %s)' for i in range(count))
            cursor.execute(sql, field_values)
        
        print("Loaded proposicoes temas %d" % (i,))

    with connections['default'].cursor() as cursor:
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

def load_enquetes():
    if 'enquetes' not in settings.DATABASES:
        print('Enquetes connection not available')
        return
 
    process_models = [get_model('FormularioPublicado'), get_model('Resposta'), get_model('ItemResposta'), get_model('Posicionamento')]

    for model in process_models:
        table_name = model._meta.db_table

        with connections['default'].cursor() as cursor:
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
                
        

        with connections['default'].cursor() as cursor:
            cursor.execute('ALTER TABLE public."%s" DISABLE TRIGGER ALL;' % (table_name,))

        print('Loaded enquetes %s' % (table_name,))


def load_analytics_proposicoes():
    proposicao_ids = set(get_model('Proposicao').objects.values_list('id', flat=True))

    token = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['ANALYTICS_CREDENTIALS']), 'https://www.googleapis.com/auth/analytics.readonly').get_access_token().access_token

    daterange = [datetime.date.today() - datetime.timedelta(days=i) for i in range(1,93)]
    for date in daterange:
        if get_model('ProposicaoPageview').objects.filter(date=date).count() > 0:
            continue

        pageviews_dict = {}
        
        i = 1
        while (True):
            url = ('https://www.googleapis.com/analytics/v3/data/ga'
                +'?ids=ga%3A35624691'
                +'&start-date='+date.strftime("%Y-%m-%d")
                +'&end-date='+date.strftime("%Y-%m-%d")
                +'&metrics=ga%3Apageviews'
                +'&dimensions=ga%3ApagePath%2Cga%3Adate'
                +'&sort=-ga%3Apageviews'
                +'&filters=ga%3ApagePath%3D~%5E%2FproposicoesWeb%2Ffichadetramitacao%2Cga%3ApagePath%3D~%5E%2Fpropostas-legislativas%2F'
                +'&start-index='+str(i)
                +'&max-results=10000'
                +'&access_token='+token)

            r = requests.get(url)
            data = r.json()

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
        proposicao_pageview_list = []
        for proposicao_id, pageviews in pageviews_dict.items():
            if proposicao_id in proposicao_ids:
                proposicao_pageview_list.append(get_model('ProposicaoPageview')(
                    proposicao_id=proposicao_id,
                    pageviews=pageviews,
                    date=date
                ))
        

        print('Loaded analytics %s' % (date,))

def preprocess():
    pa = defaultdict(lambda:{'pageviews': 0, 'poll_votes': 0, 'poll_comments': 0})

    pageviews_qs = get_model('ProposicaoPageview').objects.all()

    for row in pageviews_qs:
        proposicao_id = row.proposicao_id
        date = row.date
        pageviews = row.pageviews

        pa[(proposicao_id,date)]['pageviews'] = pageviews

    votes_qs = get_model('Resposta').objects \
        .extra(select={'date':'date(dat_resposta)'}) \
        .values('ide_formulario_publicado__proposicao', 'date') \
        .annotate(votes_count=Count('ide_resposta')) \
        .values('ide_formulario_publicado__proposicao','date','votes_count')

    for row in votes_qs:
        if not row['ide_formulario_publicado__proposicao'] or \
            not row['date']:
            continue

        proposicao_id = row['ide_formulario_publicado__proposicao']
        date = row['date']
        poll_votes = row['votes_count']

        pa[(proposicao_id,date)]['poll_votes'] = poll_votes


    comments_qs = get_model('Posicionamento').objects \
        .extra(select={'date':'date(dat_posicionamento)'}) \
        .values('ide_formulario_publicado__proposicao', 'date') \
        .annotate(comments_count=Count('ide_posicionamento')) \
        .values('ide_formulario_publicado__proposicao','date','comments_count')

    for row in comments_qs:
        if not row['ide_formulario_publicado__proposicao'] or \
            not row['date']:
            continue

        proposicao_id = row['ide_formulario_publicado__proposicao']
        date = row['date']
        poll_comments = row['comments_count']

        pa[(proposicao_id,date)]['poll_comments'] = poll_comments

    with connections['default'].cursor() as cursor:  
        cursor.execute('ALTER TABLE app_proposicaoaggregated DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_proposicaoaggregated')
        pa_list = [get_model('ProposicaoAggregated')(proposicao_id=k[0], date=k[1], pageviews=v['pageviews'], poll_votes=v['poll_votes'], poll_comments=v['poll_comments']) for k, v in pa.items()]
        get_model('ProposicaoAggregated').objects.bulk_create(pa_list)
        cursor.execute('ALTER TABLE app_proposicaoaggregated ENABLE TRIGGER ALL;')

    print('Finished preprocess')
