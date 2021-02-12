from django.core.cache import cache
from django.conf import settings
from django.urls import reverse

import pandas as pd

from . import plots
from .models import *

def api_top_proposicoes(initial_date, final_date, save_cache=False):
    cache_name = 'api_top_proposicoes-{}-{}'.format(initial_date.toordinal(), final_date.toordinal())
    stats = cache.get(cache_name, None)

    if not stats or save_cache:
        stats = {}

        stats['rows'] = ProposicaoAggregated.objects.top_proposicoes(initial_date, final_date)
        if save_cache:
            print("Saving cache for {} {}-{}".format(cache_name, initial_date, final_date))
            cache.set(cache_name, stats, 172800)

    return stats

def api_top_noticias(initial_date, final_date, save_cache=False):
    cache_name = 'api_top_noticias-{}-{}'.format(initial_date.toordinal(), final_date.toordinal())
    stats = cache.get(cache_name, None)

    if not stats or save_cache:
        stats = {}

        stats['rows'] = NoticiaAggregated.objects.top_noticias(initial_date, final_date)
        if save_cache:
            print("Saving cache for {} {}-{}".format(cache_name, initial_date, final_date))
            cache.set(cache_name, stats, 172800)

    return stats

def enquetes_temas(initial_date, final_date, save_cache=False):
    stats = {}

    cache_name = 'enquetes_temas-{}-{}'.format(initial_date.toordinal(), final_date.toordinal())
    stats = cache.get(cache_name, None)

    if not stats or save_cache:
        stats = {}
        
        stats['graph'] = plots.enquetes_temas(initial_date, final_date)
        
        if save_cache:
            print("Saving cache for {} {}-{}".format(cache_name, initial_date, final_date))
            cache.set(cache_name, stats, 172800)

    return stats

def proposicoes_temas(initial_date, final_date, save_cache=False):
    stats = {}

    cache_name = 'proposicoes_temas-{}-{}'.format(initial_date.toordinal(), final_date.toordinal())
    stats = cache.get(cache_name, None)

    if not stats or save_cache:
        stats = {}
        
        stats['graph'] = plots.proposicoes_temas(initial_date, final_date)

        if save_cache:
            print("Saving cache for {} {}-{}".format(cache_name, initial_date, final_date))
            cache.set(cache_name, stats, 172800)

    return stats

def noticias_temas(initial_date, final_date, save_cache=False):
    stats = {}

    cache_name = 'noticias_temas-{}-{}'.format(initial_date.toordinal(), final_date.toordinal())
    stats = cache.get(cache_name, None)

    if not stats or save_cache:
        stats = {}
        
        stats['graph'] = plots.noticias_temas(initial_date, final_date)

        if save_cache:
            print("Saving cache for {} {}-{}".format(cache_name, initial_date, final_date))
            cache.set(cache_name, stats, 172800)

    return stats

def noticias_tags(initial_date, final_date, save_cache=False):
    stats = {}

    cache_name = 'noticias_tags-{}-{}'.format(initial_date.toordinal(), final_date.toordinal())
    stats = cache.get(cache_name, None)

    if not stats or save_cache:
        stats = {}
        
        stats['graph'] = plots.noticias_tags(initial_date, final_date)

        if save_cache:
            print("Saving cache for {} {}-{}".format(cache_name, initial_date, final_date))
            cache.set(cache_name, stats, 172800)

    return stats

def relatorio_consolidado(initial_date, final_date, save_cache=False):
    stats = {}
    if not (initial_date and final_date):
        return stats

    cache_name = 'relatorio_consolidado-{}-{}'.format(initial_date.toordinal(), final_date.toordinal())
    stats = cache.get(cache_name, None)

    if not stats or save_cache:

        stats = {}

        # summary plots
        stats['ficha_enquete_summary_plot'] = plots.summary_plot(group_by='day', height=360, initial_date=initial_date, final_date=final_date, subplots=['ficha', 'enquete'], show_legend=True)
        stats['prisma_summary_plot'] = plots.summary_plot(group_by='day', height=200, initial_date=initial_date, final_date=final_date, subplots=['prisma'], show_legend=True)
        stats['noticia_summary_plot'] = plots.summary_plot(group_by='day', height=300, initial_date=initial_date, final_date=final_date, subplots=['noticia'], show_legend=True)

        # enquetes votes and comments
        qs = ProposicaoAggregated.objects.get_aggregated(initial_date, final_date)

        stats.update({
            'poll_votes': qs['poll_votes'],
            'poll_comments': qs['poll_comments'],
            'poll_comments_unchecked': qs['poll_comments_unchecked'],
            'poll_comments_authorized': qs['poll_comments_authorized'],
            'poll_comments_unauthorized': qs['poll_comments_unauthorized'],
        })

        # portal comments
        comentarios_camara_count = PortalComentario.objects.get_comentarios_camara_count(initial_date, final_date)
        qs = NoticiaAggregated.objects.get_aggregated(initial_date, final_date)
        stats.update({
            'noticia_pageviews': qs['pageviews'],
            'portal_comments': qs['portal_comments'],
            'portal_comments_unchecked': qs['portal_comments_unchecked'],
            'portal_comments_authorized': qs['portal_comments_authorized'],
            'portal_comments_unauthorized': qs['portal_comments_unauthorized'],
            'portal_comments_camara': comentarios_camara_count,
        })

        # prisma tickets
        qs = PrismaDemanda.objects.get_count(initial_date, final_date)

        stats.update({
            'prisma_tickets': qs['iddemanda__count'],
        })

        # prisma formas de recebimento
        qs = PrismaDemanda.objects.get_forma_de_recebimento_counts(initial_date, final_date)

        stats.update({
            'prisma_formas_de_recebimento': [row for row in qs]
        })

        # prisma tipos
        qs = PrismaDemanda.objects.get_tipo_counts(initial_date, final_date)

        stats.update({
            'prisma_tipos': [row for row in qs]
        })


        # prisma categorias
        prisma_categorias = PrismaDemanda.objects.get_categoria_counts(initial_date, final_date)

        stats.update({
            'top_prisma_categorias': [row for row in prisma_categorias]
        })

        # prisma proposições
        qs = PrismaDemanda.objects.get_proposicao_counts(initial_date, final_date)

        stats.update({
            'top_prisma_proposicoes': [row for row in qs]
        })

        # prisma sexo / sexo idade
        prisma_sexo_plot = plots.prisma_sexo(initial_date, final_date)
        stats.update({
            'prisma_sexo_plot': prisma_sexo_plot,
        })

        prisma_sexo_idade_plot = plots.prisma_sexo_idade(initial_date, final_date)
        stats.update({
            'prisma_sexo_idade_plot': prisma_sexo_idade_plot,
        })

        # proposicoes temas plot
        proposicoes_temas_plot = plots.proposicoes_temas(initial_date=initial_date, final_date=final_date)

        stats.update({
            'proposicoes_temas_plot': proposicoes_temas_plot
        })

        # enquetes temas plot
        enquetes_temas_plot = plots.enquetes_temas(initial_date=initial_date, final_date=final_date)

        stats.update({
            'enquetes_temas_plot': enquetes_temas_plot
        })

        # noticias temas plot
        noticias_temas_plot = plots.noticias_temas(initial_date=initial_date, final_date=final_date)

        stats.update({
            'noticias_temas_plot': noticias_temas_plot
        })

        if save_cache:
            print("Saving cache for {} {}-{}".format(cache_name, initial_date, final_date))
            cache.set(cache_name, stats, 172800)

    return stats