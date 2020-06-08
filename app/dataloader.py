import boto3
import datetime
import json
import os
import re
import zipfile

from django.conf import settings
from django.db import connection, IntegrityError
from django.db.models import Count, Sum

from oauth2client.service_account import ServiceAccountCredentials
from oauth2client.client import HttpAccessTokenRefreshError

from tqdm import tqdm

import requests

from .models import *

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

def load_deputados(cmd=None):
    url = 'https://dadosabertos.camara.leg.br/arquivos/deputados/json/deputados.json'

    r = get_http().get(url)
    j = r.json()
    for d in tqdm(j['dados'], 'Loading deputados'):
        Deputado.objects.update_or_create(
            id = int(re.search('/([0-9]*)$', d['uri']).group(1)),
            defaults={
                'nome': d['nome']
            }
        )

def load_orgaos(cmd=None):
    url = 'https://dadosabertos.camara.leg.br/arquivos/orgaos/json/orgaos.json'

    r = get_http().get(url)
    j = r.json()

    for o in tqdm(j['dados'], 'Loading orgaos'):
        Orgao.objects.update_or_create(
            id = int(re.search('/([0-9]*)$', o['uri']).group(1)),
            defaults={
                'sigla': o['sigla'],
                'nome': o['nome']
            }
        )

def load_proposicoes(cmd=None):
    for i in range(2001, datetime.datetime.now().year+1):
        url = 'https://dadosabertos.camara.leg.br/arquivos/proposicoes/json/proposicoes-%s.json' % (i,)

        r = get_http().get(url)
        j = r.json()
        
        for p in tqdm(j['dados'], 'Loading proposicoes %d' % (i,)):
            try:
                orgao_numerador = Orgao.objects.get(id=int(re.search('/([0-9]*)$', p['uriOrgaoNumerador']).group(1)))
            except Orgao.DoesNotExist:
                orgao_numerador = None
            except AttributeError:
                orgao_numerador = None

            try:
                ultimo_status_orgao = Orgao.objects.get(id=int(re.search('/([0-9]*)$', p['ultimoStatus']['uriOrgao']).group(1)))
            except Orgao.DoesNotExist:
                ultimo_status_orgao = None
            except AttributeError:
                ultimo_status_orgao = None

            try:
                ultimo_status_relator = Deputado.objects.get(id=int(re.search('/([0-9]*)$', p['ultimoStatus']['uriRelator']).group(1)))
            except Deputado.DoesNotExist:
                ultimo_status_relator = None
            except AttributeError:
                ultimo_status_relator = None
            
            try:
                formulario_publicado = FormularioPublicado.objects.get(tex_url_formulario_publicado=str(p['id']))
            except FormularioPublicado.DoesNotExist:
                formulario_publicado = None
            except AttributeError:
                formulario_publicado = None

            proposicao = Proposicao.objects.update_or_create(
                id = p['id'],
                defaults={
                    'sigla_tipo': p['siglaTipo'],
                    'numero': p['numero'],
                    'ano': p['ano'],
                    'ementa': p['ementa'],
                    'ementa_detalhada': p['ementaDetalhada'],
                    'keywords': p['keywords'],
                    'data_apresentacao': datetime.datetime.strptime(p['dataApresentacao'], "%Y-%m-%dT%H:%M:%S").date(),
                    'orgao_numerador': orgao_numerador,
                    'uri_prop_anterior': p['uriPropAnterior'],
                    'uri_prop_principal': p['uriPropPrincipal'],
                    'uri_prop_posterior': p['uriPropPosterior'],
                    'url_inteiro_teor': p['urlInteiroTeor'],
                    'formulario_publicado': formulario_publicado,
                    # descricao
                    'ultimo_status_situacao_descricao': p['ultimoStatus']['descricaoSituacao'],
                    'ultimo_status_data': datetime.datetime.strptime(p['ultimoStatus']['data'], "%Y-%m-%dT%H:%M:%S").date(),
                    'ultimo_status_relator': ultimo_status_relator,
                    'ultimo_status_orgao': ultimo_status_orgao,
                }
            )
        
def load_proposicoes_autores(cmd=None):
    for i in range(2001, datetime.datetime.now().year+1):
        url = 'https://dadosabertos.camara.leg.br/arquivos/proposicoesAutores/json/proposicoesAutores-%s.json' % (i,)

        r = get_http().get(url)
        j = r.json()

        for p in tqdm(j['dados'], 'Loading proposicoes autores %d' % (i,)):
            try:
                deputado = Deputado.objects.get(id=p['idDeputadoAutor'])
            except Deputado.DoesNotExist:
                deputado = None
            except KeyError:
                deputado = None
            
            try:
                proposicao = Proposicao.objects.get(id=p['idProposicao'])
            except Proposicao.DoesNotExist:
                proposicao = None
                
            if deputado and proposicao:
                proposicao.autor.add(deputado)

def load_proposicoes_temas(cmd=None):
    for i in range(2001, datetime.datetime.now().year+1):
        url = 'https://dadosabertos.camara.leg.br/arquivos/proposicoesTemas/json/proposicoesTemas-%s.json' % (i,)

        r = get_http().get(url)
        j = r.json()

        for p in tqdm(j['dados'], 'Loading proposicoes temas %d' % (i,)):
            try:
                proposicao = Proposicao.objects.get(id=int(re.search('/([0-9]*)$', p['uriProposicao']).group(1)))
            except Proposicao.DoesNotExist:
                proposicao = None
            
            tema, created = Tema.objects.update_or_create(
                id=p['codTema'],
                defaults={
                    'nome': p['tema']
                }
            )
                
            if proposicao and tema:
                proposicao.tema.add(tema)


def load_enquetes(cmd=None):
    os.system("rm SqlProFormsVotacao.zip")
    session = boto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    s3 = session.resource('s3')
    s3.Bucket(settings.AWS_BUCKET_NAME).download_file(Key="SqlProFormsVotacao.zip", Filename="SqlProFormsVotacao.zip")

    # os.system("gpg --batch --passphrase cppsemidcamara --output SqlProFormsVotacao.zip --decrypt SqlProFormsVotacao.gpg.zip")

    os.system("rm -rf SqlProFormsVotacao")
    with zipfile.ZipFile("SqlProFormsVotacao.zip", 'r') as zip_ref:
        zip_ref.extractall(".")
    os.system("rm SqlProFormsVotacao.zip")

    mypath = "SqlProFormsVotacao"
    sql_dumps = [os.path.join(mypath,f) for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]
    sql_dumps = [x for x in sql_dumps if re.search('\.sql$', x)]
    sql_dumps.sort()
    with connection.cursor() as cursor:        
        for sql_dump in sql_dumps:
            with open(sql_dump, 'r') as f:
                data = f.read()
                queries = re.findall(r'\n(INSERT INTO[\s\S]*?;)(?=\n(?:INSERT|COMMIT|CREATE))', data)
                for q in tqdm(queries, 'Loading %s' % (sql_dump,)):
                    query_segments = re.search(r'^INSERT INTO \[(\S*?)\] \(([\s\S]*?)\) VALUES \(([\s\S]*?)\);$', q)
                    try:
                        table_name = query_segments.group(1)
                        field_names = ','.join(re.findall('\[([\s\S]*?)\]',query_segments.group(2)))
                        values = query_segments.group(3)
                    except AttributeError:
                        import pdb;pdb.set_trace()
                    postgres_query = 'INSERT INTO public."%s" (%s) VALUES (%s) ON CONFLICT DO NOTHING' % (table_name, field_names, values)
                    if table_name in ['Formulario_Publicado', 'Resposta', 'Item_Resposta', 'Posicionamento', 'Curtida']:
                        try:
                            cursor.execute(postgres_query)
                        except IntegrityError:
                            cmd.stderr.write(cmd.style.NOTICE("Error running query %s" % (postgres_query,)))

def load_analytics_proposicoes(cmd=None):
    token = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['ANALYTICS_CREDENTIALS']), 'https://www.googleapis.com/auth/analytics.readonly').get_access_token().access_token

    daterange = [datetime.date.today() - datetime.timedelta(days=i) for i in range(1,93)]
    for date in daterange:
        if ProposicaoPageview.objects.filter(date=date).count() > 0:
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

            for row in tqdm(data['rows'], 'Loading analytics proposicoes %s' % (date,)):
                page_path = row[0]
                date = datetime.datetime.strptime(row[1], "%Y%m%d").date()
                pageviews = int(row[2])

                id_proposicao = None

                r = re.search('^/proposicoesWeb/fichadetramitacao\?.*idProposicao=([0-9]+)', page_path)
                if r:
                    id_proposicao = r.group(1)

                r = re.search('^/propostas-legislativas/([0-9]+)', page_path)
                if r:
                    id_proposicao = r.group(1)
                pageviews_dict[id_proposicao] = pageviews_dict.get(id_proposicao, 0) + pageviews

            try:
                data['nextLink']
                i += 10000
            except KeyError:
                break
        
        for proposicao_id, pageviews in pageviews_dict.items():
            try:
                proposicao = Proposicao.objects.get(id=proposicao_id)
            except Proposicao.DoesNotExist:
                continue
            ProposicaoPageview.objects.create(
                proposicao=proposicao,
                pageviews=pageviews,
                date=date
            )

def preprocess(cmd=None):
    pageviews_qs = ProposicaoPageview.objects.all()
    
    for row in tqdm(pageviews_qs, 'Updating pageviews totals'):
        ProposicaoAggregated.objects.update_or_create(
            proposicao=row.proposicao,
            date=row.date,
            defaults={'pageviews': row.pageviews}
        )

    votes_qs = Resposta.objects \
        .extra(select={'date':'date(dat_resposta)'}) \
        .values('ide_formulario_publicado__proposicao', 'date') \
        .annotate(votes_count=Count('ide_resposta')) \
        .values('ide_formulario_publicado__proposicao','date','votes_count')

    for row in tqdm(votes_qs, 'Updating poll votes counts'):
        if not row['ide_formulario_publicado__proposicao'] or \
            not row['date']:
            continue

        ProposicaoAggregated.objects.update_or_create(
            proposicao_id=row['ide_formulario_publicado__proposicao'],
            date=row['date'],
            defaults={'poll_votes': row['votes_count']},
        )

    comments_qs = Posicionamento.objects \
        .extra(select={'date':'date(dat_posicionamento)'}) \
        .values('ide_formulario_publicado__proposicao', 'date') \
        .annotate(comments_count=Count('ide_posicionamento')) \
        .values('ide_formulario_publicado__proposicao','date','comments_count')

    for row in tqdm(comments_qs, 'Updating poll comments counts'):
        if not row['ide_formulario_publicado__proposicao'] or \
            not row['date']:
            continue

        ProposicaoAggregated.objects.update_or_create(
            proposicao_id=row['ide_formulario_publicado__proposicao'],
            date=row['date'],
            defaults={'poll_comments': row['comments_count']},
        )
    
    
    