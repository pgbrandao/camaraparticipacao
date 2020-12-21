from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Sum

import datetime

import altair as alt
import pandas as pd

from bs4 import BeautifulSoup

class AppSettings(models.Model):
    # Single-row model just to store some settings
    last_updated = models.DateTimeField(blank=True, null=True)

    def get_instance():
        return AppSettings.objects.get_or_create(pk=1)[0]

class EnqueteFormularioPublicado(models.Model):
    ide_formulario_publicado = models.AutoField(primary_key=True)
    ide_usuario = models.TextField()  # This field type is a guess.
    tex_url_formulario_publicado = models.TextField(db_index=True)  # This field type is a guess.
    nom_titulo_formulario_publicado = models.TextField()  # This field type is a guess.
    des_formulario_publicado = models.TextField(blank=True, null=True)  # This field type is a guess.
    cod_tipo = models.TextField()  # This field type is a guess.
    cod_divulgacao = models.TextField()  # This field type is a guess.
    dat_publicacao = models.DateTimeField()
    dat_inicio_vigencia = models.DateTimeField()
    dat_fim_vigencia = models.DateTimeField(blank=True, null=True)
    ind_permite_varias_respostas = models.TextField(blank=True, null=True)  # This field type is a guess.
    des_conteudo = models.TextField()  # This field type is a guess.
    des_informacao_adicional_1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    des_informacao_adicional_2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    des_informacao_adicional_3 = models.TextField(blank=True, null=True)  # This field type is a guess.
    des_url_post = models.TextField(blank=True, null=True)  # This field type is a guess.
    ind_enquete_automatica = models.TextField(blank=True, null=True)  # This field type is a guess.
    ind_enquete_com_posicionamentos = models.TextField(blank=True, null=True)  # This field type is a guess.
    tex_url_link_externo = models.TextField(blank=True, null=True)  # This field type is a guess.
    tex_label_link_externo = models.TextField(blank=True, null=True)  # This field type is a guess.

class EnqueteResposta(models.Model):
    ide_resposta = models.AutoField(primary_key=True)
    ide_formulario_publicado = models.ForeignKey('EnqueteFormularioPublicado', null=True, on_delete=models.SET_NULL, db_column='ide_formulario_publicado')
    ide_usuario = models.TextField()
    dat_resposta = models.DateTimeField(blank=True, null=True)

class EnqueteItemResposta(models.Model):
    ide_item_resposta = models.AutoField(primary_key=True)
    ide_resposta = models.ForeignKey('EnqueteResposta', null=True, on_delete=models.SET_NULL, db_column='ide_resposta')
    num_indice_campo = models.IntegerField()
    num_indice_opcao = models.IntegerField(blank=True, null=True)
    num_indice_linha_tabela = models.IntegerField(blank=True, null=True)
    tex_texto_livre = models.TextField(blank=True, null=True)

class EnquetePosicionamento(models.Model):
    ide_posicionamento = models.AutoField(primary_key=True)
    ide_formulario_publicado = models.ForeignKey('EnqueteFormularioPublicado', null=True, on_delete=models.SET_NULL, db_column='ide_formulario_publicado')
    ide_resposta = models.ForeignKey('EnqueteResposta', null=True, on_delete=models.SET_NULL, db_column='ide_resposta')
    ide_usuario = models.TextField(blank=True, null=True)
    nom_usuario = models.TextField(blank=True, null=True)
    ind_positivo = models.IntegerField()
    qtd_curtidas = models.IntegerField()
    des_conteudo = models.TextField(blank=True, null=True)
    dat_posicionamento = models.DateTimeField(blank=True, null=True)
    cod_autorizado = models.IntegerField(null=True)
    qtd_descurtidas = models.IntegerField(null=True)

class EnquetePosicionamentoExtra(models.Model):
    class ClassificationTypes(models.IntegerChoices):
        UNRATED = (0, 'Unrated')
        INSIGHTFUL = (1, 'Insightful')
        NOT_INSIGHTFUL = (-1, 'Not insightful')
    posicionamento = models.OneToOneField('EnquetePosicionamento', on_delete=models.DO_NOTHING)
    classification = models.IntegerField(
        choices=ClassificationTypes.choices,
        default=ClassificationTypes.UNRATED)

class Proposicao(models.Model):
    # The following field is based on the other ones
    nome_processado = models.TextField(blank=True, null=True)

    # Original fields
    sigla_tipo = models.TextField(blank=True, null=True)
    numero = models.IntegerField(blank=True, null=True)
    ano = models.IntegerField(blank=True, null=True)
    ementa = models.TextField(blank=True, null=True)
    ementa_detalhada = models.TextField(blank=True, null=True)
    keywords = models.TextField(blank=True, null=True)
    data_apresentacao = models.DateField(blank=True, null=True)
    orgao_numerador = models.ForeignKey('Orgao', null=True, related_name='orgao_numerador', on_delete=models.SET_NULL)

    # These 3 fields can become references later on
    uri_prop_anterior = models.TextField(blank=True, null=True)
    uri_prop_principal = models.TextField(blank=True, null=True)
    uri_prop_posterior = models.TextField(blank=True, null=True)

    url_inteiro_teor = models.TextField(blank=True, null=True)

    formulario_publicado = models.OneToOneField('EnqueteFormularioPublicado', null=True, on_delete=models.SET_NULL)
    autor = models.ManyToManyField('Autor')
    tema = models.ManyToManyField('Tema')
    descricao = models.TextField(blank=True, null=True)
    ultimo_status_situacao_descricao = models.TextField(blank=True, null=True)
    ultimo_status_data = models.DateField(blank=True, null=True)
    ultimo_status_relator = models.ForeignKey('Deputado', null=True, related_name='ultimo_status_relator', on_delete=models.SET_NULL)
    ultimo_status_orgao = models.ForeignKey('Orgao', null=True, on_delete=models.SET_NULL)

    def enquete_posicionamentos(self, order_by="-dat_posicionamento"):
        queryset = EnquetePosicionamento.objects.filter(ide_formulario_publicado=self.formulario_publicado)
        if order_by:
            queryset = queryset.order_by(order_by)

        return queryset

    def stats(self):
        qs = ProposicaoAggregated.objects.filter(proposicao=self)
        qs = qs.aggregate(Sum('ficha_pageviews'), Sum('noticia_pageviews'), Sum('poll_votes'), Sum('poll_comments'))

        return {
            'ficha_pageviews_total': qs['ficha_pageviews__sum'],
            'noticia_pageviews_total': qs['noticia_pageviews__sum'],
            'poll_votes_total': qs['poll_votes__sum'],
            'poll_comments_total': qs['poll_comments__sum'],
        }
        
        

    def enquete_votos_count(self):
        return self.formulario_publicado.resposta_set.count()

class Tema(models.Model):
    nome = models.TextField(blank=True, null=True)
    def __str__(self):
        return '%s' % (self.nome,)

class Autor(models.Model):
    # Based on what it is
    nome_processado = models.TextField(blank=True, null=True)

    deputado = models.ForeignKey('Deputado', null=True, on_delete=models.CASCADE)
    orgao = models.ForeignKey('Orgao', null=True, on_delete=models.CASCADE)

class Deputado(models.Model):
    # The following field is based on the other ones
    nome_processado = models.TextField(blank=True, null=True)

    nome = models.TextField(blank=True, null=True)
    partido = models.TextField(blank=True, null=True)
    uf = models.TextField(blank=True, null=True)

    def __str__(self):
        return '%s (%s-%s)' % (self.nome, self.partido, self.uf)

class Orgao(models.Model):
    sigla = models.TextField(blank=True, null=True)
    nome = models.TextField(blank=True, null=True)

class Noticia(models.Model):
    tipo_conteudo = models.TextField(blank=True, null=True)
    link = models.TextField(blank=True, null=True)
    titulo = models.TextField(blank=True, null=True)
    conteudo = models.TextField(blank=True, null=True)
    resumo = models.TextField(blank=True, null=True)
    data = models.DateTimeField(blank=True, null=True)
    data_atualizacao = models.DateTimeField(blank=True, null=True)
    deputados = models.ManyToManyField('Deputado')
    proposicoes = models.ManyToManyField('Proposicao')

    raw_data = JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-data']

    def pageviews(self):
        return self.noticiapageviews_set.all().aggregate(Sum('pageviews'))['pageviews__sum']


class DailySummary(models.Model):
    date = models.DateField(db_index=True, unique=True)
    atendimentos_telefone = models.IntegerField(default=0)
    atendimentos_autosservico = models.IntegerField(default=0)

class NoticiaAggregated(models.Model):
    noticia = models.ForeignKey('Noticia', on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    pageviews = models.IntegerField(default=0)
    portal_comments = models.IntegerField(default=0)
    portal_comments_unchecked = models.IntegerField(default=0)
    portal_comments_authorized = models.IntegerField(default=0)
    portal_comments_unauthorized = models.IntegerField(default=0)

class ProposicaoAggregated(models.Model):
    proposicao = models.ForeignKey('Proposicao', on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    ficha_pageviews = models.IntegerField(default=0)
    noticia_pageviews = models.IntegerField(default=0)
    poll_votes = models.IntegerField(default=0)
    poll_comments = models.IntegerField(default=0)
    poll_comments_unchecked = models.IntegerField(default=0)
    poll_comments_checked = models.IntegerField(default=0)
    poll_comments_authorized = models.IntegerField(default=0)
    poll_comments_unauthorized = models.IntegerField(default=0)
    class Meta:
        unique_together = ('proposicao', 'date')

class NoticiaPageviews(models.Model):
    '''
    PRIVATE: This model is for data loader internal use only.
    '''
    noticia = models.ForeignKey('Noticia', on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    pageviews = models.IntegerField(default=0)
    class Meta:
        unique_together = ('noticia', 'date')

class ProposicaoFichaPageviews(models.Model):
    '''
    PRIVATE: This model is for data loader internal use only.
    '''
    proposicao = models.ForeignKey('Proposicao', on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    pageviews = models.IntegerField()
    class Meta:
        unique_together = ('proposicao', 'date')

class PrismaDemandante(models.Model):
    iddemandante = models.AutoField(db_column='IdDemandante', primary_key=True)
    demandante_data_cadastro = models.DateTimeField(db_column='Demandante.Data Cadastro', null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demandante_grau_de_instrução = models.TextField(db_column='Demandante.Grau de Instrução', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demandante_sexo = models.TextField(db_column='Demandante.Sexo', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demandante_categoria = models.TextField(db_column='Demandante.Categoria', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demandante_data_de_nascimento = models.DateField(db_column='Demandante.Data de Nascimento', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demandante_profissão_externa = models.TextField(db_column='Demandante.Profissão Externa', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.

class PrismaDemanda(models.Model):
    iddemanda = models.AutoField(db_column='IdDemanda', primary_key=True)
    iddemandante = models.ForeignKey('PrismaDemandante', db_column='IdDemandante', on_delete=models.DO_NOTHING, null=True)
    demanda_protocolo = models.TextField(db_column='Demanda.Protocolo', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_fila = models.TextField(db_column='Demanda.Fila', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_prioridade = models.TextField(db_column='Demanda.Prioridade', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_canal = models.TextField(db_column='Demanda.Canal', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_tipo = models.TextField(db_column='Demanda.Tipo', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_data_criação = models.DateTimeField(db_column='Demanda.Data Criação', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_prazo = models.DateTimeField(db_column='Demanda.Prazo', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_prazo_sugerido = models.DateTimeField(db_column='Demanda.Prazo Sugerido', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_data_da_resposta = models.DateTimeField(db_column='Demanda.Data da Resposta', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_tempo_em_aberto = models.IntegerField(db_column='Demanda.Tempo em Aberto', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_tempo_em_aberto_em_minutos = models.IntegerField(db_column='Demanda.Tempo em Aberto em Minutos', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_tempo_de_trabalho = models.IntegerField(db_column='Demanda.Tempo de Trabalho', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_titulo = models.TextField(db_column='Demanda.Titulo', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_data_da_atualização = models.DateTimeField(db_column='Demanda.Data da Atualização', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_status = models.TextField(db_column='Demanda.Status', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_forma_de_recebimento = models.TextField(db_column='Demanda.Forma de Recebimento', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_orgão_interessado = models.TextField(db_column='Demanda.Orgão Interessado', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    demanda_resultado_do_atendimento = models.TextField(db_column='Demanda.Resultado do Atendimento', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.

class PrismaAssunto(models.Model):
    local_id = models.AutoField(primary_key=True) # This is not in the original model, but Django requires it
    assunto_iddemanda = models.ForeignKey('PrismaDemanda', db_column='Assunto.IdDemanda', on_delete=models.DO_NOTHING)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    assunto_nome = models.TextField(db_column='Assunto.Nome', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.

class PrismaCategoria(models.Model):
    local_id = models.AutoField(primary_key=True) # This is not in the original model, but Django requires it
    iddemanda = models.ForeignKey('PrismaDemanda', db_column='IdDemanda', on_delete=models.DO_NOTHING)
    macrotema = models.TextField(db_column='Macrotema', blank=True, null=True)  # Field name made lowercase.
    tema = models.TextField(db_column='Tema', blank=True, null=True)  # Field name made lowercase.
    subtema = models.TextField(db_column='Subtema', blank=True, null=True)  # Field name made lowercase.
    categoria_posicionamento = models.TextField(db_column='Categoria.Posicionamento', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    categoria_tema_proposição = models.TextField(db_column='Categoria.Tema Proposição', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.

class PortalComentario(models.Model):
    id = models.CharField(primary_key=True, max_length=500)
    usuario_id = models.CharField(max_length=100)
    data = models.DateTimeField()
    comentario = models.TextField(blank=True, null=True)
    sistema = models.CharField(max_length=100, blank=True, null=True)
    url = models.ForeignKey('Noticia', blank=True, null=True, on_delete=models.DO_NOTHING)
    situacao = models.CharField(max_length=100, blank=True, null=True)
    usuario_nome = models.CharField(max_length=100, blank=True, null=True)

class PortalComentarioPosicionamento(models.Model):
    local_id = models.AutoField(primary_key=True) # This is not in the original model, but Django requires it
    id_comentario = models.ForeignKey('PortalComentario', db_column='id_comentario', on_delete=models.DO_NOTHING)
    usuario_id = models.CharField(max_length=100)
    usuario_nome = models.CharField(max_length=500)
    data = models.DateTimeField()
    favor = models.SmallIntegerField()

    class Meta:
        unique_together = (('id_comentario', 'usuario_id'),)
