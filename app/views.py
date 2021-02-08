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

def api_top_noticias(request):
    date = datetime.datetime.strptime(request.GET['date'], settings.STRFTIME_SHORT_DATE_FORMAT).date() if request.GET.get('date') else None
    initial_date = datetime.datetime.strptime(request.GET['initial_date'], settings.STRFTIME_SHORT_DATE_FORMAT).date() if request.GET.get('initial_date') else None
    final_date = datetime.datetime.strptime(request.GET['final_date'], settings.STRFTIME_SHORT_DATE_FORMAT).date() if request.GET.get('final_date') else None

    if date:
        filter_params = {
            'date': date
        }
        requires_grouping = False
    elif initial_date and final_date:
        filter_params = {
            'date__gte': initial_date,
            'date__lte': final_date,
        }
        requires_grouping = True

    qs = NoticiaAggregated.objects.filter(**filter_params).values('noticia__id').annotate(pageviews=Sum('pageviews'), portal_comments=Sum('portal_comments')).values('noticia__titulo', 'noticia__link', 'noticia__tipo_conteudo', 'pageviews', 'portal_comments')
    df = pd.DataFrame(qs)

    if requires_grouping:
        df = df.groupby(['noticia__titulo', 'noticia__link', 'noticia__tipo_conteudo']) \
            .agg({
                'pageviews': 'sum',
                'portal_comments': 'sum',
            }) \
            .reset_index()

    df.sort_values('pageviews', ascending=False, inplace=True)
    df = df[:100]

    return JsonResponse({
        **filter_params,
        'top_noticias': [{
            'titulo': row['noticia__titulo'],
            'link': row['noticia__link'],
            'pageviews': row['pageviews'],
            'portal_comments': row['portal_comments'],
            'tipo_conteudo': row['noticia__tipo_conteudo']
        } for _, row in df.iterrows()]
    })

def api_top_proposicoes(request):
    date = datetime.datetime.strptime(request.GET['date'], settings.STRFTIME_SHORT_DATE_FORMAT).date() if request.GET.get('date') else None
    initial_date = datetime.datetime.strptime(request.GET['initial_date'], settings.STRFTIME_SHORT_DATE_FORMAT).date() if request.GET.get('initial_date') else None
    final_date = datetime.datetime.strptime(request.GET['final_date'], settings.STRFTIME_SHORT_DATE_FORMAT).date() if request.GET.get('final_date') else None

    if date:
        filter_params = {
            'date': date,
        }
        requires_grouping = False
    elif initial_date and final_date:
        filter_params = {
            'date__gte': initial_date,
            'date__lte': final_date,
        }
        requires_grouping = True

    qs = ProposicaoAggregated.objects \
        .filter(**filter_params) \
        .prefetch_related('proposicao__tema') \
        .values('proposicao__id') \
        .annotate(ficha_pageviews=Sum('ficha_pageviews'), noticia_pageviews=Sum('noticia_pageviews'), poll_votes=Sum('poll_votes'), poll_comments=Sum('poll_comments')) \
        .values('proposicao__nome_processado', 'proposicao__id', 'ficha_pageviews', 'noticia_pageviews', 'poll_votes', 'poll_comments') \

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
        } for q in qs])
    
    df['score'] = (df.ficha_pageviews / df.ficha_pageviews.max()).fillna(0) + \
        (df.noticia_pageviews / df.noticia_pageviews.max()).fillna(0) + \
        (df.poll_votes / df.poll_votes.max()).fillna(0) + \
        (df.poll_comments / df.poll_comments.max()).fillna(0)
    df['score'] = df['score'].map('{:,.2f}'.format)

    df.sort_values('score', ascending=False, inplace=True)

    df = df[:100]

    extra_params = {}
    if date:
        extra_params['period_humanized'] = date
    elif initial_date and final_date:
        extra_params['period_humanized'] = helpers.period_humanized(initial_date, final_date)

    return JsonResponse({
        **extra_params,
        **filter_params,
        'top_proposicoes': [{
            'nome_processado': row.proposicao__nome_processado,
            'link_ficha_tramitacao': 'https://www.camara.leg.br/propostas-legislativas/{}'.format(row.proposicao__id),
            'link': reverse('proposicao_detail', args=[row.proposicao__id]),
            'temas': row.temas,
            'ficha_pageviews': row.ficha_pageviews,
            'noticia_pageviews': row.noticia_pageviews,
            'poll_votes': row.poll_votes,
            'poll_comments': row.poll_comments,
            'score': row.score,
        } for _, row in df.iterrows()]
    })

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
    dropdown_choices = [
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

    try:
        return render(request, 'pages/relatorio/custom/{}.html'.format(year), locals())
    except:
        raise Http404
    
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

