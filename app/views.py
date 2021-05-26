from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Sum, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.http import Http404, HttpResponse, JsonResponse, FileResponse
from django.views.decorators.clickjacking import xframe_options_exempt

import calendar
import datetime
from . import helpers
from . import plots
from . import reports

from pathlib import Path

from .models import *



def index(request):
    group_by = request.GET.get('group_by') or 'day'
    if group_by not in ('day', 'month', 'year'):
        return Http404

    summary_plot = plots.summary_plot(group_by=group_by, height=600)

    # last_updated = AppSettings.get_instance().last_updated

    return render(request, 'pages/index.html', locals())


def api_relatorio_consolidado(request):
    year = request.GET.get('year')
    month_year = request.GET.get('month_year')
    period_type = request.GET.get('period_type') or 'year'

    initial_date = None
    final_date = None

    if period_type == 'month' and month_year:
        dt = datetime.datetime.strptime(month_year, '%m-%Y')
        _, num_days = calendar.monthrange(
            int(dt.strftime('%Y')), int(dt.strftime('%m')))

        initial_date = dt
        final_date = dt.replace(day=num_days)

        period_humanized = datetime.datetime.strftime(initial_date, '%B/%Y')

    elif period_type == 'year' and year:
        initial_date = datetime.date(year=int(year), month=1, day=1)
        final_date = datetime.date(year=int(year), month=12, day=31)

        period_humanized = datetime.datetime.strftime(initial_date, '%Y')

    if initial_date and final_date:
        stats = reports.relatorio_consolidado(initial_date, final_date)

        response = JsonResponse(stats)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Max-Age"] = "1000"
        response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type"
        return response

def api_top_noticias(request, initial_date, final_date=None):
    initial_date = datetime.datetime.strptime(initial_date, settings.STRFTIME_SHORT_DATE_FORMAT_URL).date()

    params = {}
    if final_date:
        final_date = datetime.datetime.strptime(final_date, settings.STRFTIME_SHORT_DATE_FORMAT_URL).date()
        params['date__gte'] = initial_date
        params['date__lte'] = final_date
        params['period_humanized'] = helpers.period_humanized(initial_date, final_date)
    else:
        final_date = initial_date
        params['date'] = initial_date
        params['period_humanized'] = initial_date

    stats = reports.api_top_noticias(initial_date, final_date)

    response = JsonResponse({
        **params,
        'rows': stats['rows']
    })
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response["Access-Control-Max-Age"] = "1000"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type"
    return response


def api_top_proposicoes(request, initial_date, final_date=None):
    initial_date = datetime.datetime.strptime(initial_date, settings.STRFTIME_SHORT_DATE_FORMAT_URL).date()

    params = {}
    if final_date:
        final_date = datetime.datetime.strptime(final_date, settings.STRFTIME_SHORT_DATE_FORMAT_URL).date()
        params['date__gte'] = initial_date
        params['date__lte'] = final_date
        params['period_humanized'] = helpers.period_humanized(initial_date, final_date)
    else:
        final_date = initial_date
        params['date'] = initial_date
        params['period_humanized'] = initial_date


    stats = reports.api_top_proposicoes(initial_date, final_date)

    response = JsonResponse({
        **params,
        'rows': stats['rows']
    })
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response["Access-Control-Max-Age"] = "1000"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type"
    return response

def enquetes_temas(request, year=None):
    if not year:
        return redirect('enquetes_temas', year=datetime.date.today().year)

    year_choices = [
        (x.strftime('%Y'), x.strftime('%Y'))
        for x in pd.date_range('2019-01-01', datetime.date.today(), freq='YS').to_series()
    ]

    initial_date = datetime.date(year=int(year), month=1, day=1)
    final_date = datetime.date(year=int(year), month=12, day=31)

    # [(value, text)]
    sidebar_api_params = [
        (helpers.get_api_params(initial_date, final_date),
        '{}-{}'.format(initial_date.strftime('%B %Y'), final_date.strftime('%B %Y')))
    ] + [
        (
            helpers.get_api_params(initial_date, final_date), 
            initial_date.strftime('%B %Y')
        ) 
        for initial_date, final_date
        in zip(pd.date_range(initial_date, final_date, freq='MS'), pd.date_range(initial_date, final_date, freq='M'))
    ]

    stats = reports.enquetes_temas(initial_date, final_date)

    view_name = 'enquetes_temas'
    return render(request, 'pages/enquetes_temas.html', locals())

def proposicoes_temas(request, year=None):
    if not year:
        return redirect('proposicoes_temas', year=datetime.date.today().year)

    year_choices = [
        (x.strftime('%Y'), x.strftime('%Y'))
        for x in pd.date_range('2019-01-01', datetime.date.today(), freq='YS').to_series()
    ]

    initial_date = datetime.date(year=int(year), month=1, day=1)
    final_date = datetime.date(year=int(year), month=12, day=31)

    sidebar_api_params = [
        (helpers.get_api_params(initial_date, final_date),
        '{}-{}'.format(initial_date.strftime('%B %Y'), final_date.strftime('%B %Y')))
    ] + [
        (
            helpers.get_api_params(initial_date, final_date), 
            initial_date.strftime('%B %Y')
        ) 
        for initial_date, final_date
        in zip(pd.date_range(initial_date, final_date, freq='MS'), pd.date_range(initial_date, final_date, freq='M'))
    ]

    stats = reports.proposicoes_temas(initial_date, final_date)

    view_name = 'proposicoes_temas'
    return render(request, 'pages/proposicoes_temas.html', locals())

def noticias_temas(request, year=None):
    if not year:
        return redirect('noticias_temas', year=datetime.date.today().year)

    year_choices = [
        (x.strftime('%Y'), x.strftime('%Y'))
        for x in pd.date_range('2019-01-01', datetime.date.today(), freq='YS').to_series()
    ]

    initial_date = datetime.date(year=int(year), month=1, day=1)
    final_date = datetime.date(year=int(year), month=12, day=31)

    sidebar_api_params = [
        (helpers.get_api_params(initial_date, final_date),
        '{}-{}'.format(initial_date.strftime('%B %Y'), final_date.strftime('%B %Y')))
    ] + [
        (
            helpers.get_api_params(initial_date, final_date), 
            initial_date.strftime('%B %Y')
        ) 
        for initial_date, final_date
        in zip(pd.date_range(initial_date, final_date, freq='MS'), pd.date_range(initial_date, final_date, freq='M'))
    ]

    stats = reports.noticias_temas(initial_date, final_date)

    view_name = 'noticias_temas'
    return render(request, 'pages/noticias_temas.html', locals())

def noticias_tags(request, year=None):
    if not year:
        return redirect('noticias_tags', year=datetime.date.today().year)

    year_choices = [
        (x.strftime('%Y'), x.strftime('%Y'))
        for x in pd.date_range('2019-01-01', datetime.date.today(), freq='YS').to_series()
    ]

    initial_date = datetime.date(year=int(year), month=1, day=1)
    final_date = datetime.date(year=int(year), month=12, day=31)

    sidebar_api_params = [
        (helpers.get_api_params(initial_date, final_date),
        '{}-{}'.format(initial_date.strftime('%B %Y'), final_date.strftime('%B %Y')))
    ] + [
        (
            helpers.get_api_params(initial_date, final_date), 
            initial_date.strftime('%B %Y')
        ) 
        for initial_date, final_date
        in zip(pd.date_range(initial_date, final_date, freq='MS'), pd.date_range(initial_date, final_date, freq='M'))
    ]

    stats = reports.noticias_tags(initial_date, final_date)

    view_name = 'noticias_tags'
    return render(request, 'pages/noticias_tags.html', locals())

def relatorios_index(request):
    return render(request, 'pages/relatorio/index.html', locals())

def relatorio_ano(request, year):
    initial_date = datetime.date(year=int(year), month=1, day=1)
    final_date = datetime.date(year=int(year), month=12, day=31)

    period_humanized = datetime.datetime.strftime(initial_date, '%Y')

    stats = reports.relatorio_consolidado(initial_date, final_date)

    return render(request, 'pages/relatorio/custom/{}.html'.format(year), locals())
    
def relatorio_consolidado(request, custom):
    year = request.GET.get('year')
    month_year = request.GET.get('month_year')
    period_type = request.GET.get('period_type') or 'year'

    month_year_choices = [
        (x.strftime('%m-%Y'), x.strftime('%B-%Y'))
        for x in pd.date_range('2019-01-01', datetime.date.today(), freq='MS').to_series()
    ]
    month_year_choices = month_year_choices[::-1]

    year_choices = [
        (x.strftime('%Y'), x.strftime('%Y'))
        for x in pd.date_range('2019-01-01', datetime.date.today(), freq='YS').to_series()
    ]
    year_choices = year_choices[::-1]

    initial_date = None
    final_date = None

    if period_type == 'month' and month_year:
        dt = datetime.datetime.strptime(month_year, '%m-%Y')
        _, num_days = calendar.monthrange(
            int(dt.strftime('%Y')), int(dt.strftime('%m')))

        initial_date = dt
        final_date = dt.replace(day=num_days)

        period_humanized = datetime.datetime.strftime(initial_date, '%B/%Y')

    elif period_type == 'year' and year:
        initial_date = datetime.date(year=int(year), month=1, day=1)
        final_date = datetime.date(year=int(year), month=12, day=31)

        period_humanized = datetime.datetime.strftime(initial_date, '%Y')

    stats = reports.relatorio_consolidado(initial_date, final_date)
    
    return render(request, 'pages/relatorio/relatorio.html', locals())


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

def enquetes_exportar_comentarios(request,):
    posicionamentos = Posicionamento.objects \
        .filter(ide_formulario_publicado__proposicao__isnull=False, cod_autorizado__in=[1,2]) \
        .values('ide_posicionamento', 'ide_formulario_publicado__proposicao__id', 'ide_formulario_publicado__proposicao__nome_processado', 'ind_positivo', 'des_conteudo', 'dat_posicionamento', 'cod_autorizado')
    return JsonResponse({
        'posicionamentos': list(posicionamentos)
    })

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

    stats = {}

    summary_plot = plots.summary_plot(group_by='day', height=500, proposicao=proposicao)
    poll_votes_plot = plots.poll_votes(proposicao)

    # Noticias
    qs = proposicao.noticia_set.order_by('data').all()
    stats.update({
        'noticias': [{
            'data': row.data.strftime(settings.STRFTIME_SHORT_DATE_FORMAT),
            'titulo': row.titulo,
            'link': row.link,
            'pageviews': row.pageviews(),
            'comments_unchecked': row.comments_unchecked(),
            'comments_authorized': row.comments_authorized(),
            'comments_unauthorized': row.comments_unauthorized(),
        } for row in qs]
    })

    return render(request, 'pages/proposicao_details.html', locals())

def proposicao_comentarios_enquete(request, id_proposicao):
    proposicao = Proposicao.objects.get(pk=id_proposicao)

    return render(request, 'pages/proposicao_comentarios_enquete.html', locals())

