from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Sum, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.http import Http404, HttpResponse, JsonResponse, FileResponse

import calendar
import datetime
from . import plots

from pathlib import Path

from .models import *



def index(request):
    group_by = request.GET.get('group_by') or 'day'
    if group_by not in ('day', 'month'):
        return Http404

    summary_plot = plots.summary_plot(group_by=group_by)

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

    qs = NoticiaPageviews.objects.filter(**filter_params).values('noticia__titulo', 'noticia__link', 'noticia__tipo_conteudo', 'pageviews')
    df = pd.DataFrame(qs)

    if requires_grouping:
        df = df.groupby(['noticia__titulo', 'noticia__link', 'noticia__tipo_conteudo']) \
            .agg({
                'pageviews': 'sum',
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
            'tipo_conteudo': row['noticia__tipo_conteudo']
        } for _, row in df.iterrows()]
    })

def api_top_proposicoes(request):
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

    qs = ProposicaoAggregated.objects.filter(**filter_params).values('proposicao__nome_processado', 'proposicao__id', 'ficha_pageviews', 'noticia_pageviews', 'poll_votes', 'poll_comments')

    df = pd.DataFrame(qs)

    if requires_grouping:
        df = df.groupby(['proposicao__nome_processado', 'proposicao__id']) \
            .agg({
                'ficha_pageviews': 'sum',
                'noticia_pageviews': 'sum',
                'poll_votes': 'sum',
                'poll_comments': 'sum',
            }) \
            .reset_index()
    
    df['score'] = (df.ficha_pageviews / df.ficha_pageviews.max()).fillna(0) + \
        (df.noticia_pageviews / df.noticia_pageviews.max()).fillna(0) + \
        (df.poll_votes / df.poll_votes.max()).fillna(0) + \
        (df.poll_comments / df.poll_comments.max()).fillna(0)
    df['score'] = df['score'].map('{:,.2f}'.format)

    df.sort_values('score', ascending=False, inplace=True)

    df = df[:100]

    return JsonResponse({
        **filter_params,
        'top_proposicoes': [{
            'nome_processado': row.proposicao__nome_processado,
            'link': reverse('proposicao_detail', args=[row.proposicao__id]),
            'ficha_pageviews': row.ficha_pageviews,
            'noticia_pageviews': row.noticia_pageviews,
            'poll_votes': row.poll_votes,
            'poll_comments': row.poll_comments,
            'score': row.score,
        } for _, row in df.iterrows()]
    })

def raiox(request):
    # if dimension not in ('tema', 'autor', 'relator', 'situacao', 'indexacao', 'proposicao'):
    #     return Http404

    dimension = request.GET.get('dimension')
    metric_field = request.GET.get('metric_field')
    period_type = request.GET.get('period_type') or 'month'
    year = request.GET.get('year')
    month_year = request.GET.get('month_year')
    plot_type = request.GET.get('plot_type')

    if metric_field and period_type:
        if period_type == 'month' and month_year:
            dt = datetime.datetime.strptime(month_year, '%m-%Y')
            _, num_days = calendar.monthrange(
                int(dt.strftime('%Y')), int(dt.strftime('%m')))

            date_min = dt
            date_max = dt.replace(day=num_days)

            plot_div, total, total_plot = plots.raiox_mensal(
                date_min, date_max, metric_field, dimension, plot_type)

            percent_plot = total_plot / total * 100 if total else 0
        elif period_type == 'year' and year:
            plot_div = plots.raiox_anual(
                year, metric_field, dimension)

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

    dimension_choices = [
        ('tema', 'Tema'),
        ('autor', 'Autor'),
        ('relator', 'Relator'),
        ('situacao', 'Situação'),
        ('indexacao', 'Indexação (apenas mensal)'),
        ('proposicao', 'Proposição (apenas mensal)'),
    ]
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

def enquetes_exportar_comentarios(request,):
    posicionamentos = Posicionamento.objects \
        .filter(ide_formulario_publicado__proposicao__isnull=False, cod_autorizado__in=[1,2]) \
        .values('ide_posicionamento', 'ide_formulario_publicado__proposicao__id', 'ide_formulario_publicado__proposicao__nome_processado', 'ind_positivo', 'des_conteudo', 'dat_posicionamento', 'cod_autorizado')
    return JsonResponse({
        'posicionamentos': list(posicionamentos)
    })

@login_required
def db_dump(request,):
    dump_path = Path(settings.DB_DUMP_PATH) / Path('latest_dump.gz')
    f = open(dump_path, 'rb')
    response = FileResponse(f)
    response["Content-Disposition"] = "attachment; filename="+str('latest_dump.gz')
    return response



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

    summary_plot = plots.summary_plot(group_by='day', proposicao=proposicao)
    poll_votes_plot = plots.poll_votes(proposicao)

    return render(request, 'pages/proposicao_details.html', locals())

def proposicao_comentarios_enquete(request, id_proposicao):
    proposicao = Proposicao.objects.get(pk=id_proposicao)

    return render(request, 'pages/proposicao_comentarios_enquete.html', locals())

