import datetime
import requests
import re

from django.db import connections, transaction, IntegrityError

import tenacity

from .common import *

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
        for r in get_model('EnqueteFormularioPublicado').objects.values_list('ide_formulario_publicado', 'tex_url_formulario_publicado'):
            try:
                formulario_publicado_dict[int(r[1])] = r[0]
            except ValueError:
                pass

        for i in range(2001, datetime.datetime.now().year+1):
            url = 'https://dadosabertos.camara.leg.br/arquivos/proposicoes/json/proposicoes-%s.json' % (i,)

            r = requests.get(url)

            if r.status_code == 404:
                print("Missing proposicoes %d" % (i,))
                continue

            j = r.json()
            
            proposicoes = {}

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
                proposicoes[p['id']] = proposicao

            for id, proposicao in proposicoes.items():
                if proposicao.sigla_tipo == 'EMP':
                    try:
                        id_principal = int(re.search('/([0-9]*)$', proposicao.uri_prop_principal).group(1))
                        proposicao.nome_processado = 'EMP {} => {}'.format(proposicao.numero, proposicoes[id_principal].nome_processado)
                    except (AttributeError, KeyError):
                        pass

            get_model('Proposicao').objects.bulk_create(list(proposicoes.values()))

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

            if r.status_code == 404:
                print("Missing proposicoes autores %d" % (i,))
                continue

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

            if r.status_code == 404:
                print("Missing proposicoes temas %d" % (i,))
                continue

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
