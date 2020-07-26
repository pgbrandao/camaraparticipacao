from django.db import models
from django.db.models import Sum
from django.core.exceptions import ObjectDoesNotExist

import datetime

import altair as alt
import pandas as pd

from bs4 import BeautifulSoup

class FormularioPublicado(models.Model):
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

    class Meta:
        db_table = 'Formulario_Publicado'

class Resposta(models.Model):
    ide_resposta = models.AutoField(primary_key=True)
    ide_formulario_publicado = models.ForeignKey('FormularioPublicado', null=True, on_delete=models.SET_NULL, db_column='ide_formulario_publicado')
    ide_usuario = models.TextField()
    dat_resposta = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'Resposta'

class ItemResposta(models.Model):
    ide_item_resposta = models.AutoField(primary_key=True)
    ide_resposta = models.ForeignKey('Resposta', null=True, on_delete=models.SET_NULL, db_column='ide_resposta')
    num_indice_campo = models.IntegerField()
    num_indice_opcao = models.IntegerField(blank=True, null=True)
    num_indice_linha_tabela = models.IntegerField(blank=True, null=True)
    tex_texto_livre = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'Item_Resposta'

class Posicionamento(models.Model):
    ide_posicionamento = models.AutoField(primary_key=True)
    ide_formulario_publicado = models.ForeignKey('FormularioPublicado', null=True, on_delete=models.SET_NULL, db_column='ide_formulario_publicado')
    ide_resposta = models.ForeignKey('Resposta', null=True, on_delete=models.SET_NULL, db_column='ide_resposta')
    ide_usuario = models.TextField(blank=True, null=True)
    nom_usuario = models.TextField(blank=True, null=True)
    ind_positivo = models.IntegerField()
    qtd_curtidas = models.IntegerField()
    des_conteudo = models.TextField(blank=True, null=True)
    dat_posicionamento = models.DateTimeField(blank=True, null=True)
    cod_autorizado = models.IntegerField(null=True)
    qtd_descurtidas = models.IntegerField(null=True)


    class Meta:
        db_table = 'Posicionamento'

class PosicionamentoExtra(models.Model):
    class ClassificationTypes(models.IntegerChoices):
        UNRATED = (0, 'Unrated')
        INSIGHTFUL = (1, 'Insightful')
        NOT_INSIGHTFUL = (-1, 'Not insightful')
    posicionamento = models.OneToOneField('Posicionamento', on_delete=models.DO_NOTHING)
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

    formulario_publicado = models.OneToOneField('FormularioPublicado', null=True, on_delete=models.SET_NULL)
    autor = models.ManyToManyField('Deputado', related_name='autor_set')
    tema = models.ManyToManyField('Tema')
    descricao = models.TextField(blank=True, null=True)
    ultimo_status_situacao_descricao = models.TextField(blank=True, null=True)
    ultimo_status_data = models.DateField(blank=True, null=True)
    ultimo_status_relator = models.ForeignKey('Deputado', null=True, related_name='ultimo_status_relator', on_delete=models.SET_NULL)
    ultimo_status_orgao = models.ForeignKey('Orgao', null=True, on_delete=models.SET_NULL)

    def enquete_posicionamentos(self, order_by="-dat_posicionamento"):
        queryset = Posicionamento.objects.filter(ide_formulario_publicado=self.formulario_publicado)
        if order_by:
            queryset = queryset.order_by(order_by)

        return queryset

    def stats(self):
        qs = ProposicaoAggregated.objects.filter(proposicao=self)
        qs = qs.aggregate(Sum('pageviews'), Sum('poll_votes'), Sum('poll_comments'))

        return {
            'pageviews_total': qs['pageviews__sum'],
            'poll_votes_total': qs['poll_votes__sum'],
            'poll_comments_total': qs['poll_comments__sum'],
        }
        
        

    def enquete_votos_count(self):
        return self.formulario_publicado.resposta_set.count()

class Tema(models.Model):
    nome = models.TextField(blank=True, null=True)
    def __str__(self):
        return '%s' % (self.nome,)

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

class ProposicaoPageview(models.Model):
    proposicao = models.ForeignKey('Proposicao', on_delete=models.CASCADE)
    date = models.DateField()
    pageviews = models.IntegerField()

class ProposicaoAggregated(models.Model):
    proposicao = models.ForeignKey('Proposicao', on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    pageviews = models.IntegerField(default=0)
    poll_votes = models.IntegerField(default=0)
    poll_comments = models.IntegerField(default=0)
    class Meta:
        unique_together = ('proposicao', 'date')