from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Count, Sum, Q
from django.db.models.functions import Coalesce
from django.urls import reverse

import datetime

import pandas as pd
import numpy as np

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

    class Meta:
        db_table = 'Formulario_Publicado'

class EnqueteResposta(models.Model):
    ide_resposta = models.AutoField(primary_key=True)
    ide_formulario_publicado = models.ForeignKey('EnqueteFormularioPublicado', null=True, on_delete=models.SET_NULL, db_column='ide_formulario_publicado')
    ide_usuario = models.TextField()
    dat_resposta = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'Resposta'

class EnqueteItemResposta(models.Model):
    ide_item_resposta = models.AutoField(primary_key=True)
    ide_resposta = models.ForeignKey('EnqueteResposta', null=True, on_delete=models.SET_NULL, db_column='ide_resposta')
    num_indice_campo = models.IntegerField()
    num_indice_opcao = models.IntegerField(blank=True, null=True)
    num_indice_linha_tabela = models.IntegerField(blank=True, null=True)
    tex_texto_livre = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'Item_Resposta'

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

    class Meta:
        db_table = 'Posicionamento'

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
            'ficha_pageviews': qs['ficha_pageviews__sum'],
            'noticia_pageviews': qs['noticia_pageviews__sum'],
            'poll_votes': qs['poll_votes__sum'],
            'poll_comments': qs['poll_comments__sum'],
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
    tags_conteudo = models.ManyToManyField('NoticiaTag')
    tema_principal = models.ForeignKey('NoticiaTema', null=True, on_delete=models.CASCADE)

    raw_data = JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-data']

    def pageviews(self):
        return self.noticiapageviews_set.all().aggregate(Sum('pageviews'))['pageviews__sum']

    def comments_unchecked(self):
        return self.portalcomentario_set.filter(situacao='PENDENTE').aggregate(Count('id'))['id__count']
    def comments_authorized(self):
        return self.portalcomentario_set.filter(situacao='APROVADO').aggregate(Count('id'))['id__count']
    def comments_unauthorized(self):
        return self.portalcomentario_set.filter(situacao='REPROVADO').aggregate(Count('id'))['id__count']

class NoticiaTag(models.Model):
    nome = models.TextField(blank=True, null=True)
    slug = models.TextField(blank=True, null=True)

class NoticiaTema(models.Model):
    titulo = models.TextField(blank=True, null=True)

class DailySummary(models.Model):
    date = models.DateField(db_index=True, unique=True)
    atendimentos = models.IntegerField(default=0)

class NoticiaAggregatedManager(models.Manager):
    def get_aggregated(self, initial_date, final_date):
        return super().get_queryset() \
            .filter(date__gte=initial_date, date__lte=final_date) \
            .aggregate(
                    pageviews=Coalesce(Sum('pageviews'), 0),
                    portal_comments=Coalesce(Sum('portal_comments'), 0),
                    portal_comments_unchecked=Coalesce(Sum('portal_comments_unchecked'), 0),
                    portal_comments_authorized=Coalesce(Sum('portal_comments_authorized'), 0),
                    portal_comments_unauthorized=Coalesce(Sum('portal_comments_unauthorized'), 0),
                   )

    def get_metric_date_dimension_df(self, initial_date, final_date, metric_field, dimension_field):
        """
        Groups date periods by month
        Outputs DataFrame[metric_field, 'date', 'date_formatted', dimension_field]
        """
        qs = self.get_queryset() \
            .filter(date__gte=initial_date, date__lte=final_date, **{metric_field+'__gt': 0}) \
            .values(metric_field, 'date', dimension_field)
        df = pd.DataFrame.from_records(qs)

        if df.empty:
            return None
        
        df['date'] = pd.to_datetime(df['date'])
        df[dimension_field] = df[dimension_field].astype('category')

        df = df.groupby([pd.Grouper(key='date', freq='M'), dimension_field], observed=True)[metric_field].agg('sum')
        df = df.reset_index()
        df['date_formatted'] = df['date'].dt.strftime('%B %Y')

        return df

    def get_metric_date_df(self, initial_date, final_date, metric_field):
        """
        Groups date periods by month
        Outputs DataFrame[metric_field, 'date', 'date_formatted']
        """
        qs = self.get_queryset() \
            .filter(date__gte=initial_date, date__lte=final_date, **{metric_field+'__gt': 0}) \
            .values(metric_field, 'date')
        df = pd.DataFrame.from_records(qs)

        if df.empty:
            return None
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.groupby([pd.Grouper(key='date', freq='M')], observed=True)[metric_field].agg('sum')
        df = df.reset_index()
        df['date_formatted'] = df['date'].dt.strftime('%B %Y')

        return df


    def top_noticias(self, initial_date, final_date):
        qs = NoticiaAggregated.objects \
            .filter(date__gte=initial_date, date__lte=final_date) \
            .values('noticia__id') \
            .annotate(pageviews=Sum('pageviews'), portal_comments=Sum('portal_comments'), portal_comments_unchecked=Sum('portal_comments_unchecked'), portal_comments_authorized=Sum('portal_comments_authorized'), portal_comments_unauthorized=Sum('portal_comments_unauthorized')) \
            .order_by('-pageviews') \
            .values('noticia__id', 'noticia__titulo', 'noticia__link', 'noticia__tipo_conteudo', 'noticia__tema_principal__titulo', 'pageviews', 'portal_comments', 'portal_comments_unchecked', 'portal_comments_authorized', 'portal_comments_unauthorized')

        # Dictionary of tags for speed
        tags = {}
        for n in Noticia.objects.all().values('id', 'tags_conteudo__nome'):
            if tags.get(n['id']):
                tags[n['id']].append(n['tags_conteudo__nome'])
            else:
                tags[n['id']] = [n['tags_conteudo__nome']]

        return [{
                'titulo': q['noticia__titulo'],
                'link': q['noticia__link'],
                'tags_conteudo': tags[q['noticia__id']],
                'pageviews': q['pageviews'],
                'tema_principal': q['noticia__tema_principal__titulo'],
                'portal_comments': q['portal_comments'],
                'portal_comments_unchecked': q['portal_comments_unchecked'],
                'portal_comments_authorized': q['portal_comments_authorized'],
                'portal_comments_unauthorized': q['portal_comments_unauthorized'],
                'tipo_conteudo': q['noticia__tipo_conteudo']
            } for q in qs[:500]]




class NoticiaAggregated(models.Model):
    noticia = models.ForeignKey('Noticia', on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    pageviews = models.IntegerField(default=0)
    portal_comments = models.IntegerField(default=0)
    portal_comments_unchecked = models.IntegerField(default=0)
    portal_comments_authorized = models.IntegerField(default=0)
    portal_comments_unauthorized = models.IntegerField(default=0)

    objects = NoticiaAggregatedManager()

class ProposicaoAggregatedManager(models.Manager):
    def get_aggregated(self, initial_date, final_date):
        return self.get_queryset() \
            .filter(date__gte=initial_date, date__lte=final_date) \
            .aggregate(
                    ficha_pageviews=Coalesce(Sum('ficha_pageviews'), 0),
                    noticia_pageviews=Coalesce(Sum('noticia_pageviews'), 0),
                    poll_votes=Coalesce(Sum('poll_votes'), 0),
                    poll_comments=Coalesce(Sum('poll_comments'), 0),
                    poll_comments_checked=Coalesce(Sum('poll_comments_checked'), 0),
                    poll_comments_unchecked=Coalesce(Sum('poll_comments_unchecked'), 0),
                    poll_comments_authorized=Coalesce(Sum('poll_comments_authorized'), 0),
                    poll_comments_unauthorized=Coalesce(Sum('poll_comments_unauthorized'), 0),
                   )

    def get_metric_date_dimension_df(self, initial_date, final_date, metric_field, dimension_field):
        """
        Groups date periods by month
        Outputs DataFrame[metric_field, 'date', 'date_formatted', dimension_field]
        """
        qs = self.get_queryset() \
            .filter(date__gte=initial_date, date__lte=final_date, **{metric_field+'__gt': 0}) \
            .values(metric_field, 'date', dimension_field)
        df = pd.DataFrame.from_records(qs)

        if df.empty:
            return None
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.groupby([pd.Grouper(key='date', freq='M'), dimension_field])[metric_field].agg('sum')
        df = df.reset_index()
        df['date_formatted'] = df['date'].dt.strftime('%B %Y')

        return df

    def get_metric_date_df(self, initial_date, final_date, metric_field):
        """
        Groups date periods by month
        Outputs DataFrame[metric_field, 'date', 'date_formatted']
        """
        qs = self.get_queryset() \
            .filter(date__gte=initial_date, date__lte=final_date, **{metric_field+'__gt': 0}) \
            .values(metric_field, 'date')
        df = pd.DataFrame.from_records(qs)

        if df.empty:
            return None
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.groupby([pd.Grouper(key='date', freq='M')])[metric_field].agg('sum')
        df = df.reset_index()
        df['date_formatted'] = df['date'].dt.strftime('%B %Y')

        return df
        
    def top_proposicoes(self, initial_date, final_date):
        qs = ProposicaoAggregated.objects \
            .filter(date__gte=initial_date, date__lte=final_date) \
            .values('proposicao__id') \
            .annotate(ficha_pageviews=Sum('ficha_pageviews'), noticia_pageviews=Sum('noticia_pageviews'), poll_votes=Sum('poll_votes'), poll_comments=Sum('poll_comments'), poll_comments_unchecked=Sum('poll_comments_unchecked'), poll_comments_checked=Sum('poll_comments_checked'), poll_comments_authorized=Sum('poll_comments_authorized'), poll_comments_unauthorized=Sum('poll_comments_unauthorized')) \
            .values('proposicao__nome_processado', 'proposicao__id', 'ficha_pageviews', 'noticia_pageviews', 'poll_votes', 'poll_comments', 'poll_comments_unchecked', 'poll_comments_checked', 'poll_comments_authorized', 'poll_comments_unauthorized')

        # Dictionary of temas for speed
        temas_dict = {}
        for p in Proposicao.objects.all().values('id', 'tema__nome'):
            if temas_dict.get(p['id']):
                temas_dict[p['id']].append(p['tema__nome'])
            else:
                temas_dict[p['id']] = [p['tema__nome']]

        df = pd.DataFrame([
            {
                'proposicao__nome_processado': q['proposicao__nome_processado'],
                'proposicao__id': q['proposicao__id'],
                'temas': temas_dict[q['proposicao__id']],
                'ficha_pageviews': q['ficha_pageviews'],
                'noticia_pageviews': q['noticia_pageviews'],
                'poll_votes': q['poll_votes'],
                'poll_comments': q['poll_comments'],
                'poll_comments_unchecked': q['poll_comments_unchecked'],
                'poll_comments_checked': q['poll_comments_checked'],
                'poll_comments_authorized': q['poll_comments_authorized'],
                'poll_comments_unauthorized': q['poll_comments_unauthorized'],
            } for q in qs])

        if df.empty:
            return None

        df['score'] = (df.ficha_pageviews / df.ficha_pageviews.max()).fillna(0) + \
            (df.noticia_pageviews / df.noticia_pageviews.max()).fillna(0) + \
            (df.poll_votes / df.poll_votes.max()).fillna(0) + \
            (df.poll_comments / df.poll_comments.max()).fillna(0)
        df['score'] = df['score'].map('{:,.2f}'.format)

        df.sort_values('score', ascending=False, inplace=True)

        df = df[:500]

        return [{
            'nome_processado': row.proposicao__nome_processado,
            'link_ficha_tramitacao': 'https://www.camara.leg.br/propostas-legislativas/{}'.format(row.proposicao__id),
            'link': reverse('proposicao_detail', args=[row.proposicao__id]),
            'temas': row.temas,
            'ficha_pageviews': row.ficha_pageviews,
            'noticia_pageviews': row.noticia_pageviews,
            'poll_votes': row.poll_votes,
            'poll_comments': row.poll_comments,
            'poll_comments_unchecked': row.poll_comments_unchecked,
            'poll_comments_checked': row.poll_comments_checked,
            'poll_comments_authorized': row.poll_comments_authorized,
            'poll_comments_unauthorized': row.poll_comments_unauthorized,
            'score': row.score,
        } for _, row in df.iterrows()]

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

    objects = ProposicaoAggregatedManager()

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

    class Meta:
        db_table = 'vwDemandante'

class PrismaDemandaManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset() \
            .filter(iddemandante__demandante_categoria__startswith='Externo') \
            .filter(~Q(demanda_tipo__startswith='Fora do escopo') & ~Q(demanda_tipo__startswith='Denúncia')) \
            .filter(demanda_fila__startswith='CCI')

    def get_count(self, initial_date, final_date):
        final_date += datetime.timedelta(days=1) # Final date is advanced by one day for DateTimeField
        return self.get_queryset() \
            .filter(demanda_data_criação__gte=initial_date, demanda_data_criação__lt=final_date) \
            .aggregate(
                Count('iddemanda')
            )

    def get_forma_de_recebimento_counts(self, initial_date, final_date):
        final_date += datetime.timedelta(days=1) # Final date is advanced by one day for DateTimeField
        return self.get_queryset() \
            .filter(demanda_data_criação__gte=initial_date, demanda_data_criação__lt=final_date) \
            .values('demanda_forma_de_recebimento') \
            .annotate(
                Count('iddemanda')
            ) \
            .order_by('-iddemanda__count')

    def get_tipo_counts(self, initial_date, final_date):
        final_date += datetime.timedelta(days=1) # Final date is advanced by one day for DateTimeField
        return self.get_queryset() \
            .filter(demanda_data_criação__gte=initial_date, demanda_data_criação__lt=final_date) \
            .values('demanda_tipo') \
            .annotate(
                Count('iddemanda')
            ) \
            .order_by('-iddemanda__count')
    
    def get_proposicao_counts(self,initial_date,final_date):
        final_date += datetime.timedelta(days=1) # Final date is advanced by one day for DateTimeField
        qs = self.get_queryset() \
            .filter(demanda_data_criação__gte=initial_date, demanda_data_criação__lt=final_date) \
            .filter(prismacategoria__categoria_tema_proposição__isnull=False) \
            .values('prismacategoria__categoria_tema_proposição') \
            .annotate(
                Count('iddemanda')
            ) \
            .order_by('-iddemanda__count')

        return qs

    def get_categoria_counts(self,initial_date,final_date):
        final_date += datetime.timedelta(days=1) # Final date is advanced by one day for DateTimeField
        qs = self.get_queryset() \
            .filter(demanda_data_criação__gte=initial_date, demanda_data_criação__lt=final_date) \
            .values('prismacategoria__macrotema', 'prismacategoria__tema', 'prismacategoria__subtema')
        df = pd.DataFrame(qs, columns=['prismacategoria__macrotema', 'prismacategoria__tema', 'prismacategoria__subtema'])

        df = df.fillna(value='—')

        return df \
            .fillna('') \
            .groupby(['prismacategoria__macrotema', 'prismacategoria__tema', 'prismacategoria__subtema']) \
            .size() \
            .to_frame('count') \
            .reset_index() \
            .sort_values('count', ascending=False) \
            .to_dict('records')

    def get_sexo_counts(self,initial_date,final_date):
        final_date += datetime.timedelta(days=1) # Final date is advanced by one day for DateTimeField
        qs = self.get_queryset() \
            .filter(demanda_data_criação__gte=initial_date, demanda_data_criação__lt=final_date) \
            .values('iddemandante__demandante_sexo')
        df = pd.DataFrame(qs)

        if df.empty:
            return None
        
        return df['iddemandante__demandante_sexo'] \
            .value_counts() \
            .to_frame('count') \
            .rename_axis('sexo') \
            .reset_index()

    def get_sexo_idade_counts(self,initial_date,final_date):
        final_date += datetime.timedelta(days=1) # Final date is advanced by one day for DateTimeField
        qs = self.get_queryset() \
            .filter(demanda_data_criação__gte=initial_date, demanda_data_criação__lt=final_date) \
            .values('demanda_data_criação', 'iddemandante', 'iddemandante__demandante_data_de_nascimento', 'iddemandante__demandante_sexo')

        df = pd.DataFrame(qs, columns=['demanda_data_criação', 'iddemandante', 'iddemandante__demandante_data_de_nascimento', 'iddemandante__demandante_sexo'])
        df['iddemandante__demandante_data_de_nascimento'] = pd.to_datetime(df['iddemandante__demandante_data_de_nascimento'])
        df['demanda_data_criação'] = pd.to_datetime(df['demanda_data_criação'])
        df['idade_demanda'] = df['demanda_data_criação'] - df['iddemandante__demandante_data_de_nascimento']
        df['idade_demanda'] = df['idade_demanda'].dt.days / 365.25
        df['idade_demanda'] = df['idade_demanda'].apply(np.floor)
        df.drop_duplicates(subset='iddemandante', keep='last', inplace=True)

        df = df \
            .rename({'iddemandante__demandante_sexo': 'sexo_demanda'}, axis=1) \
            .drop(['demanda_data_criação', 'iddemandante__demandante_data_de_nascimento'], axis=1) \
            .groupby(['sexo_demanda', 'idade_demanda']) \
            .size() \
            .reset_index() \
            .rename(columns={0: 'count'}) \
            .sort_values(['idade_demanda', 'sexo_demanda'])
        df = df[(df.idade_demanda >= 10) & (df.idade_demanda <= 100)]
        df = df.pivot(index='idade_demanda', columns='sexo_demanda', values='count').reset_index()

        return df

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

    objects = PrismaDemandaManager()

    class Meta:
        db_table = 'vwDemanda'

class PrismaAssunto(models.Model):
    local_id = models.AutoField(primary_key=True) # This is not in the original model, but Django requires it
    assunto_iddemanda = models.ForeignKey('PrismaDemanda', db_column='Assunto.IdDemanda', on_delete=models.DO_NOTHING)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    assunto_nome = models.TextField(db_column='Assunto.Nome', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.

    class Meta:
        db_table = 'vwAssunto'

class PrismaCategoria(models.Model):
    local_id = models.AutoField(primary_key=True) # This is not in the original model, but Django requires it
    iddemanda = models.ForeignKey('PrismaDemanda', db_column='IdDemanda', on_delete=models.DO_NOTHING)
    macrotema = models.TextField(db_column='Macrotema', blank=True, null=True)  # Field name made lowercase.
    tema = models.TextField(db_column='Tema', blank=True, null=True)  # Field name made lowercase.
    subtema = models.TextField(db_column='Subtema', blank=True, null=True)  # Field name made lowercase.
    categoria_posicionamento = models.TextField(db_column='Categoria.Posicionamento', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    categoria_tema_proposição = models.TextField(db_column='Categoria.Tema Proposição', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.

    class Meta:
        db_table = 'vwCategoria'

class PortalComentarioManager(models.Manager):
    def get_comentarios_camara_count(self,initial_date,final_date):
        final_date += datetime.timedelta(days=1) # Final date is advanced by one day for DateTimeField
        return self.get_queryset() \
            .filter(data__gte=initial_date, data__lt=final_date) \
            .filter(usuario_id='66a23639-d13f-41eb-b15e-3d9656512a4f') \
            .count()

            
class PortalComentario(models.Model):
    id = models.CharField(primary_key=True, max_length=500)
    usuario_id = models.CharField(max_length=100)
    data = models.DateTimeField()
    comentario = models.TextField(blank=True, null=True)
    sistema = models.CharField(max_length=100, blank=True, null=True)
    url = models.ForeignKey('Noticia', db_column='url', blank=True, null=True, on_delete=models.DO_NOTHING)
    situacao = models.CharField(max_length=100, blank=True, null=True)
    usuario_nome = models.CharField(max_length=100, blank=True, null=True)

    objects = PortalComentarioManager()

    class Meta:
        db_table = 'COMENTARIO'

class PortalComentarioPosicionamento(models.Model):
    local_id = models.AutoField(primary_key=True) # This is not in the original model, but Django requires it
    id_comentario = models.ForeignKey('PortalComentario', db_column='id_comentario', on_delete=models.DO_NOTHING)
    usuario_id = models.CharField(max_length=100)
    usuario_nome = models.CharField(max_length=500)
    data = models.DateTimeField()
    favor = models.SmallIntegerField()

    class Meta:
        db_table = 'POSICIONAMENTO'
        unique_together = (('id_comentario', 'usuario_id'),)
