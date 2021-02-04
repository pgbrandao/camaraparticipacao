import datetime
import json
import requests

import tenacity

from .common import *

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

    tema_principal = None
    if j.get('tema_principal'):
        try:
            tema_id = j.get('tema_principal')['id']
            tema_titulo = j.get('tema_principal')['titulo']
        except KeyError:
            tema_id = None
    
        if tema_id:
            try:
                tema_principal = get_model('NoticiaTema').objects.get(pk=tema_id)
            except NoticiaTema.DoesNotExist:
                tema_principal = get_model('NoticiaTema').objects.create(pk=tema_id, titulo=tema_titulo)
    
    tags_conteudo_list = []
    if j.get('tags_conteudo'):
        for tag in j.get('tags_conteudo'):
            try:
                tag_id = tag['id']
                tag_nome = tag['nome']
                tag_slug = tag['slug']
            except KeyError:
                tag_id = None

            if tag_id:
                try:
                    noticia_tag = NoticiaTag.objects.get(pk=tag_id)
                except NoticiaTag.DoesNotExist:
                    noticia_tag = NoticiaTag.objects.create(pk=tag_id, nome=tag_nome, slug=tag_slug)
            tags_conteudo_list.append(noticia_tag)


    noticia = get_model('Noticia').objects.create(
        pk = noticia_id,
        tipo_conteudo = tipo_conteudo,
        link = link,
        titulo = titulo,
        data = datetime.datetime.utcfromtimestamp(data) if data else None,
        data_atualizacao = datetime.datetime.utcfromtimestamp(data_atualizacao) if data_atualizacao else None,
        conteudo = conteudo,
        resumo = resumo,
        tema_principal = tema_principal,
        raw_data = j
    )
    noticia.proposicoes.set(proposicoes_list)
    noticia.deputados.set(deputados_list)
    noticia.tags_conteudo.set(tags_conteudo_list)

    return True
