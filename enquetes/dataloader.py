import boto3
import datetime
import os
import re
import zipfile

from django.conf import settings
from django.db import connection

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from .models import *

def get_http():
    retry_strategy = Retry(
        total=8,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "POST", "OPTIONS"],
        backoff_factor=2
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("https://", adapter)
    http.mount("http://", adapter)
    return http

def load_deputados(cmd=None):
    url = 'https://dadosabertos.camara.leg.br/arquivos/deputados/json/deputados.json'

    r = get_http().get(url)
    j = r.json()
    for d in j['dados']:
        Deputado.objects.update_or_create(
            id = int(re.search('/([0-9]*)$', d['uri']).group(1)),
            defaults={
                'nome': d['nome']
            }
        )

    if cmd:
        cmd.stdout.write(cmd.style.SUCCESS("Loaded %s" % (url,)))

def load_orgaos(cmd=None):
    url = 'https://dadosabertos.camara.leg.br/arquivos/orgaos/json/orgaos.json'

    r = get_http().get(url)
    j = r.json()

    for o in j['dados']:
        Orgao.objects.update_or_create(
            id = int(re.search('/([0-9]*)$', o['uri']).group(1)),
            defaults={
                'sigla': o['sigla'],
                'nome': o['nome']
            }
        )

    if cmd:
        cmd.stdout.write(cmd.style.SUCCESS("Loaded %s" % (url,)))

def load_proposicoes(cmd=None):
    for i in range(2001, datetime.datetime.now().year+1):
        url = 'https://dadosabertos.camara.leg.br/arquivos/proposicoes/json/proposicoes-%s.json' % (i,)

        r = get_http().get(url)
        j = r.json()

        for p in j['dados']:
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
        
        if cmd:
            cmd.stdout.write(cmd.style.SUCCESS("Loaded %s" % (url,)))

def load_proposicoes_autores(cmd=None):
    for i in range(2001, datetime.datetime.now().year+1):
        url = 'https://dadosabertos.camara.leg.br/arquivos/proposicoesAutores/json/proposicoesAutores-%s.json' % (i,)

        r = get_http().get(url)
        j = r.json()

        for p in j['dados']:
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

        if cmd:
            cmd.stdout.write(cmd.style.SUCCESS("Loaded %s" % (url,)))

def load_proposicoes_temas(cmd=None):
    for i in range(2001, datetime.datetime.now().year+1):
        url = 'https://dadosabertos.camara.leg.br/arquivos/proposicoesTemas/json/proposicoesTemas-%s.json' % (i,)

        r = get_http().get(url)
        j = r.json()

        for p in j['dados']:
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

        if cmd:
            cmd.stdout.write(cmd.style.SUCCESS("Loaded %s" % (url,)))


def load_enquetes(cmd=None, initial=False):
    os.system("rm SqlProFormsVotacao.gpg.zip")
    session = boto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    s3 = session.resource('s3')
    s3.Bucket(settings.AWS_BUCKET_NAME).download_file(Key="SqlProFormsVotacao.gpg.zip", Filename="SqlProFormsVotacao.gpg.zip")

    os.system("rm SqlProFormsVotacao.zip")
    os.system("gpg --batch --passphrase cppsemidcamara --output SqlProFormsVotacao.zip --decrypt SqlProFormsVotacao.gpg.zip")

    os.system("rm -rf SqlProFormsVotacao")
    with zipfile.ZipFile("SqlProFormsVotacao.zip", 'r') as zip_ref:
        zip_ref.extractall(".")
    os.system("rm SqlProFormsVotacao.zip")

    mypath = "SqlProFormsVotacao"
    sql_dumps = [os.path.join(mypath,f) for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]
    sql_dumps.sort()

    with connection.cursor() as cursor:        
        for sql_dump in sql_dumps:
            with open(sql_dump, 'r') as f:
                data = f.read()

                # TODO: Change to "INSERT OR UPDATE INTO"
                if not initial:
                    data = re.sub(r'(CREATE TABLE[\s\S]*?;)', r'', data)
                    data = re.sub(r'(CREATE INDEX[\s\S]*?;)', r'', data)
                    data = re.sub(r'(CREATE UNIQUE[\s\S]*?;)', r'', data)
                    data = re.sub(r'(INSERT INTO)', r'INSERT OR IGNORE INTO', data)
                
                cursor.executescript(data)

    if cmd:
        cmd.stdout.write(cmd.style.SUCCESS("Loaded enquetes"))
