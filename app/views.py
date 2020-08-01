from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Sum, Q
from django.shortcuts import redirect, render
from django.http import Http404, HttpResponse

import calendar
import datetime
from . import plots

from .models import *



def index(request):
    d0 = datetime.date.today()
    dm1 = datetime.date.today()-datetime.timedelta(days=1)
    dm7 = datetime.date.today()-datetime.timedelta(days=7)
    dm8 = datetime.date.today()-datetime.timedelta(days=8)
    dm14 = datetime.date.today()-datetime.timedelta(days=14)

    if 'index_stats' in cache:
        stats = cache.get('index_stats')
    else:
        qs = ProposicaoAggregated.objects.all()

        stats = {}

        stats['votos_this_week'] = qs.filter(
            date__gte=dm7, date__lte=dm1).count()
        stats['votos_past_week'] = qs.filter(
            date__gte=dm14, date__lte=dm8).count()
        stats['votos_change'] = (
            stats['votos_this_week'] / stats['votos_past_week'] - 1) * 100 if stats['votos_past_week'] else 0

        stats['posicionamentos_this_week'] = Posicionamento.objects.filter(
            dat_posicionamento__gte=dm7, dat_posicionamento__lt=d0).count()
        stats['posicionamentos_past_week'] = Posicionamento.objects.filter(
            dat_posicionamento__gte=dm14, dat_posicionamento__lt=dm7).count()
        stats['posicionamentos_change'] = (
            stats['posicionamentos_this_week'] / stats['posicionamentos_past_week'] - 1) * 100 if stats['posicionamentos_past_week'] else 0

        stats['proposicao_ficha_pageview_this_week'] = ProposicaoFichaPageviews.objects.filter(
            date__gte=dm7, date__lt=d0).aggregate(Sum('pageviews'))['pageviews__sum'] or 0
        stats['proposicao_ficha_pageview_past_week'] = ProposicaoFichaPageviews.objects.filter(
            date__gte=dm14, date__lt=dm7).aggregate(Sum('pageviews'))['pageviews__sum'] or 0
        stats['proposicao_ficha_pageview_change'] = (stats['proposicao_ficha_pageview_this_week'] /
                                               stats['proposicao_ficha_pageview_past_week'] - 1) * 100 if stats['proposicao_ficha_pageview_past_week'] else 0

        cache.set('index_stats', stats, 3600)

    if 'index_daily_summary_global_plot' in cache:
        daily_summary_global_plot = cache.get(
            'index_daily_summary_global_plot')
    else:
        daily_summary_global_plot = plots.daily_summary_global()
        cache.set('index_daily_summary_global_plot',
                  daily_summary_global_plot, 3600)

    if 'index_proposicoes' in cache:
        proposicoes = cache.get('index_proposicoes')
    else:
        qs = ProposicaoAggregated.objects.values('proposicao') \
            .annotate(poll_votes_total=Sum('poll_votes'), poll_votes_period=Sum('poll_votes', filter=Q(date__gte=dm7, date__lt=d0)),
                    poll_comments_total=Sum('poll_comments'), poll_comments_period=Sum('poll_comments', filter=Q(date__gte=dm7, date__lt=d0)),
                    ficha_pageviews_period=Sum('ficha_pageviews', filter=Q(date__gte=dm7, date__lt=d0)))
        fields_list = {'proposicao__id', 'proposicao__sigla_tipo', 'proposicao__numero', 'proposicao__ano',
                       'poll_votes_total', 'poll_votes_period', 'poll_comments_total', 'poll_comments_period', 'ficha_pageviews_period'}
        non_count = {'proposicao__id', 'proposicao__sigla_tipo',
                     'proposicao__numero', 'proposicao__ano'}
        records = list(qs.values(*fields_list))
        for record in records:
            for k, v in record.items():
                if v is None and k in fields_list - non_count:
                    record[k] = 0

        proposicoes = pd.DataFrame.from_records(records)

        if not proposicoes.empty:
            proposicoes['p_score'] = proposicoes['poll_votes_period'] + \
                proposicoes['poll_comments_period'] + \
                proposicoes['ficha_pageviews_period']
            proposicoes.sort_values(
                by=['p_score'], ascending=False, inplace=True)
            proposicoes = proposicoes[:50]
        
        cache.set('index_proposicoes', proposicoes, 3600)
    
    return render(request, 'pages/index.html', locals())



def raiox(request, dimension):
    if dimension not in ('tema', 'autor', 'relator', 'situacao', 'indexacao', 'proposicao'):
        return Http404

    metric_field = request.GET.get('metric_field')
    month_year = request.GET.get('month_year')
    plot_type = request.GET.get('plot_type')

    if metric_field and month_year:
        dt = datetime.datetime.strptime(month_year, '%m-%Y')
        _, num_days = calendar.monthrange(
            int(dt.strftime('%Y')), int(dt.strftime('%m')))

        date_min = dt
        date_max = dt.replace(day=num_days)

        plot_div, total, total_plot = plots.raiox(
            date_min, date_max, metric_field, plot_type, dimension)

        percent_plot = total_plot / total * 100 if total else 0

    month_year_choices = [
        (x.strftime('%m-%Y'), x.strftime('%B-%Y'))
        for x in pd.date_range('2019-01-01', datetime.date.today(), freq='MS').to_series()
    ]
    month_year_choices = month_year_choices[::-1]
    
    metric_field_choices = [
        ('poll_votes', 'Votos nas enquetes'),
        ('ficha_pageviews', 'Visualizações na ficha de tramitação'),
    ]
    plot_type_choices = [
        ('sunburst', 'Circular (sunburst)'),
        ('treemap', 'Retangular (treemap)'),
    ]

    return render(request, 'pages/raiox.html', locals())


def enquetes_busca_data(request):
    date_min = None
    try:
        date_min = datetime.datetime.strptime(
            request.GET.get('date_min'), '%d/%m/%Y')
    except (ValueError, TypeError) as e:
        date_min = datetime.date.today()-datetime.timedelta(days=14)
    
    date_max = None
    try:
        date_max = datetime.datetime.strptime(
            request.GET.get('date_max'), '%d/%m/%Y')
    except (ValueError, TypeError) as e:
        date_max = datetime.date.today()-datetime.timedelta(days=1)

    qs = ProposicaoAggregated.objects.filter(date__gte=date_min, date__lte=date_max) \
        .values('proposicao') \
        .annotate(poll_votes_total=Sum('poll_votes'), poll_comments_total=Sum('poll_comments')) \
        .values('proposicao__id', 'proposicao__sigla_tipo', 'proposicao__numero', 'proposicao__ano', 'poll_votes_total', 'poll_comments_total')
    
    proposicoes = pd.DataFrame.from_records(qs)
    if not proposicoes.empty:
        proposicoes['p_score'] = proposicoes['poll_votes_total'] + \
            proposicoes['poll_comments_total']
        proposicoes.sort_values(by=['p_score'], ascending=False, inplace=True)
        proposicoes = proposicoes[:50]

    return render(request, 'pages/enquetes_busca_data.html', locals())


def busca_proposicao(request,):
    if request.method == "POST":
        sigla_tipo = request.POST.get('sigla_tipo')
        numero = request.POST.get('numero')
        ano = request.POST.get('ano')

        try:
            proposicao = Proposicao.objects.get(
                sigla_tipo=sigla_tipo, numero=int(numero), ano=int(ano))
            return redirect('proposicao_detail', id_proposicao=proposicao.pk)
        except ObjectDoesNotExist:
            pass

    sigla_tipos = Proposicao.objects.values_list(
        'sigla_tipo', flat=True).distinct('sigla_tipo')

    return render(request, 'pages/busca_proposicao.html', locals())


def proposicao_detail(request, id_proposicao):
    proposicao = Proposicao.objects.get(pk=id_proposicao)

    daily_summary_proposicao_plot = plots.daily_summary_proposicao(proposicao)

    return render(request, 'pages/proposicao_details.html', locals())

def proposicao_comentarios_enquete(request, id_proposicao):
    proposicao = Proposicao.objects.get(pk=id_proposicao)

    return render(request, 'pages/proposicao_comentarios_enquete.html', locals())

