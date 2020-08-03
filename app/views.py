from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Sum, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.http import Http404, HttpResponse, JsonResponse

import calendar
import datetime
from . import plots

from .models import *



def index(request):
    daily_summary_global_plot = plots.daily_summary_global()
    
    return render(request, 'pages/index.html', locals())

def api_top_noticias(request):
    date = datetime.datetime.strptime(request.GET['date'], "%Y-%m-%d").date()

    top_noticias = NoticiaPageviews.objects.filter(date=date).order_by('-pageviews').values('noticia__titulo', 'noticia__link', 'noticia__tipo_conteudo', 'pageviews')[:5]

    return JsonResponse({
        'noticias': [{
            'titulo': t['noticia__titulo'],
            'link': t['noticia__link'],
            'pageviews': t['pageviews'],
            'tipo_conteudo': t['noticia__tipo_conteudo']
        } for t in top_noticias]
    })

def api_top_enquetes(request):
    date = datetime.datetime.strptime(request.GET['date'], "%Y-%m-%d").date()

    top_enquetes = ProposicaoAggregated.objects.filter(date=date).order_by('-poll_votes').values('proposicao__nome_processado', 'proposicao__id', 'poll_votes', 'poll_comments')[:5]

    return JsonResponse({
        'enquetes': [{
            'nome_processado': t['proposicao__nome_processado'],
            'link': reverse('proposicao_detail', args=[t['proposicao__id']]),
            'poll_votes': t['poll_votes'],
            'poll_comments': t['poll_comments']
        } for t in top_enquetes]
    })

def api_top_proposicoes_ficha(request):
    date = datetime.datetime.strptime(request.GET['date'], "%Y-%m-%d").date()

    top_proposicoes_ficha = ProposicaoAggregated.objects.filter(date=date).order_by('-ficha_pageviews').values('proposicao__nome_processado', 'proposicao__id', 'ficha_pageviews')[:5]

    return JsonResponse({
        'proposicoes_ficha': [{
            'nome_processado': t['proposicao__nome_processado'],
            'link': reverse('proposicao_detail', args=[t['proposicao__id']]),
            'ficha_pageviews': t['ficha_pageviews'],
        } for t in top_proposicoes_ficha]
    })



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

