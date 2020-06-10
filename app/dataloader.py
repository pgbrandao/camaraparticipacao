import boto3
import datetime
import json
import os
import re
import zipfile

from collections import defaultdict

from django.conf import settings
from django.db import connection, IntegrityError
from django.db.models import Count, Sum

from oauth2client.service_account import ServiceAccountCredentials
from oauth2client.client import HttpAccessTokenRefreshError

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

    count = len(j['dados'])
    field_values = []
    for row in j['dados']:
        id = int(re.search('/([0-9]*)$', row['uri']).group(1))
        nome = row['nome']
        field_values.append(id)
        field_values.append(nome)
    

    with connection.cursor() as cursor:  
        cursor.execute('ALTER TABLE app_deputado DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_deputado')
        sql = 'INSERT INTO app_deputado (id, nome) VALUES %s' % \
            ', '.join('(%s, %s)' for i in range(count))
        cursor.execute(sql, field_values)
        cursor.execute('ALTER TABLE app_deputado ENABLE TRIGGER ALL;')
    
    cmd.stdout.write("Loaded deputados")


def load_orgaos(cmd=None):
    url = 'https://dadosabertos.camara.leg.br/arquivos/orgaos/json/orgaos.json'

    r = get_http().get(url)
    j = r.json()

    count = len(j['dados'])
    field_values = []
    for row in j['dados']:
        field_values.append(int(re.search('/([0-9]*)$', row['uri']).group(1)))
        field_values.append(row['sigla'])
        field_values.append(row['nome'])

    with connection.cursor() as cursor:  
        cursor.execute('ALTER TABLE app_orgao DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_orgao')
        sql = 'INSERT INTO app_orgao (id, sigla, nome) VALUES %s' % \
            ', '.join('(%s, %s, %s)' for i in range(count))
        cursor.execute(sql, field_values)
        cursor.execute('ALTER TABLE app_orgao ENABLE TRIGGER ALL;')
    
    cmd.stdout.write("Loaded orgaos")

def load_proposicoes(cmd=None):
    # Dict to store {tex_url_formulario_publicado => ide_formulario_publicado}
    # tex_url_formulario_publicado: ID proposição
    formulario_publicado_dict = {}
    for r in FormularioPublicado.objects.values_list('ide_formulario_publicado', 'tex_url_formulario_publicado'):
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

            proposicao = Proposicao(
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

        with connection.cursor() as cursor:  
            cursor.execute('ALTER TABLE app_proposicao DISABLE TRIGGER ALL;')
            cursor.execute('DELETE FROM app_proposicao')
            Proposicao.objects.bulk_create(proposicoes)
            cursor.execute('ALTER TABLE app_proposicao ENABLE TRIGGER ALL;')

        cmd.stdout.write("Loaded proposicoes %d" % (i,))

        
def load_proposicoes_autores(cmd=None):
    with connection.cursor() as cursor:  
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
        with connection.cursor() as cursor:  
            sql = 'INSERT INTO app_proposicao_autor (proposicao_id, deputado_id) VALUES %s ON CONFLICT DO NOTHING' % \
                ', '.join('(%s, %s)' for i in range(count))
            cursor.execute(sql, field_values)
        
        cmd.stdout.write("Loaded proposicoes autores %d" % (i,))
    with connection.cursor() as cursor:
        cursor.execute('ALTER TABLE app_proposicao_autor ENABLE TRIGGER ALL;')


def load_proposicoes_temas(cmd=None):
    with connection.cursor() as cursor:  
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
            except Proposicao.DoesNotExist:
                proposicao_id = None
            
            tema_id = row['codTema']
            if tema_id not in temas_id_set:
                tema = Tema.objects.create(
                    id = row['codTema'],
                    nome = row['tema']
                )
                temas_id_set.add(row['codTema'])

            if proposicao_id and tema_id:
                count += 1
                field_values.append(proposicao_id)
                field_values.append(tema_id)

        with connection.cursor() as cursor:  
            sql = 'INSERT INTO app_proposicao_tema (proposicao_id, tema_id) VALUES %s ON CONFLICT DO NOTHING' % \
                ', '.join('(%s, %s)' for i in range(count))
            cursor.execute(sql, field_values)
        
        cmd.stdout.write("Loaded proposicoes temas %d" % (i,))

    with connection.cursor() as cursor:
        cursor.execute('ALTER TABLE app_proposicao_tema ENABLE TRIGGER ALL;')
        cursor.execute('ALTER TABLE app_tema ENABLE TRIGGER ALL;')

def load_enquetes(cmd=None):
    process_tables_list = ['Formulario_Publicado', 'Resposta', 'Item_Resposta', 'Posicionamento', 'Curtida']
    with connection.cursor() as cursor:
        for table in process_tables_list:
            cursor.execute('ALTER TABLE public."%s" DISABLE TRIGGER ALL;' % (table,))
            cursor.execute('DELETE FROM public."%s"' % (table,))

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
            last_table_name = None
            last_field_names = None
            field_values_list = []
            with open(sql_dump, 'r') as f:
                data = f.read()
                queries = re.findall(r'\n(INSERT INTO[\s\S]*?;)(?=\n(?:INSERT|COMMIT|CREATE))', data)
                for q in queries:
                    query_segments = re.search(r'^INSERT INTO \[(\S*?)\] \(([\s\S]*?)\) VALUES \(([\s\S]*?)\);$', q)

                    table_name = query_segments.group(1)
                    field_names = ','.join(re.findall('\[([\s\S]*?)\]',query_segments.group(2)))
                    field_values = query_segments.group(3)

                    # Ignore all tables not in list
                    if table_name not in process_tables_list:
                        continue

                    # If this query refers to the same table as the last iteration, save the values for commiting later
                    if table_name == last_table_name:
                        field_values_list.append(field_values)
                    elif table_name != last_table_name:
                        # This query refers to another table! So we must commit everything that has been collected
                        if last_table_name:
                            postgres_query = 'INSERT INTO public."%s" (%s) VALUES %s ON CONFLICT DO NOTHING' % (last_table_name, last_field_names,
                                ', '.join('('+f+')' for f in field_values_list)
                            )
                            try:
                                cursor.execute(postgres_query)
                            except IntegrityError:
                                cmd.stderr.write(cmd.style.NOTICE("Error running query %s" % (postgres_query,)))
                        

                        last_table_name = table_name
                        last_field_names = field_names
                        field_values_list = [field_values]

            # Commit any data that's been left behind
            if last_table_name:
                postgres_query = 'INSERT INTO public."%s" (%s) VALUES %s ON CONFLICT DO NOTHING' % (last_table_name, last_field_names,
                    ', '.join('('+f+')' for f in field_values_list)
                )
                try:
                    cursor.execute(postgres_query)
                except IntegrityError:
                    cmd.stderr.write(cmd.style.NOTICE("Error running query %s" % (postgres_query,)))
            
            cmd.stdout.write('Loaded %s' % (sql_dump,))
    
    # Reenable triggers
    with connection.cursor() as cursor:
        for table in process_tables_list:
            cursor.execute('ALTER TABLE public."%s" ENABLE TRIGGER ALL;' % (table,))



def load_analytics_proposicoes(cmd=None):
    proposicao_ids = set(Proposicao.objects.values_list('id'))

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

            for row in data['rows']:
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
        proposicao_pageview_list = []
        for proposicao_id, pageviews in pageviews_dict.items():
            if proposicao_id in proposicao_ids:
                proposicao_pageview_list.append(ProposicaoPageview(
                    proposicao_id=proposicao_id,
                    pageviews=pageviews,
                    date=date
                ))
        
        ProposicaoPageview.objects.bulk_create(proposicao_pageview_list)

        cmd.stdout.write('Loaded analytics %s' % (date,))

def preprocess(cmd=None):
    pa = defaultdict(lambda:{'pageviews': 0, 'poll_votes': 0, 'poll_comments': 0})

    pageviews_qs = ProposicaoPageview.objects.all()

    for row in pageviews_qs:
        proposicao_id = row.proposicao_id
        date = row.date
        pageviews = row.pageviews

        pa[(proposicao_id,date)]['pageviews'] = pageviews

    votes_qs = Resposta.objects \
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


    comments_qs = Posicionamento.objects \
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

    with connection.cursor() as cursor:  
        cursor.execute('ALTER TABLE app_proposicaoaggregated DISABLE TRIGGER ALL;')
        cursor.execute('DELETE FROM app_proposicaoaggregated')
        pa_list = [ProposicaoAggregated(proposicao_id=k[0], date=k[1], pageviews=v['pageviews'], poll_votes=v['poll_votes'], poll_comments=v['poll_comments']) for k, v in pa.items()]
        ProposicaoAggregated.objects.bulk_create(pa_list)
        cursor.execute('ALTER TABLE app_proposicaoaggregated ENABLE TRIGGER ALL;')

    cmd.stdout.write('Finished preprocess')
