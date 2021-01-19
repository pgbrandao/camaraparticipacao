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
from . import plots

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
            'date': date
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
        .values('proposicao__id') \
        .annotate(ficha_pageviews=Sum('ficha_pageviews'), noticia_pageviews=Sum('noticia_pageviews'), poll_votes=Sum('poll_votes'), poll_comments=Sum('poll_comments')) \
        .values('proposicao__nome_processado', 'proposicao__id', 'ficha_pageviews', 'noticia_pageviews', 'poll_votes', 'poll_comments')

    df = pd.DataFrame(qs)
    
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

@xframe_options_exempt
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


    if initial_date and final_date:
        cache_name = 'relatorio_consolidado-{}-{}'.format(initial_date.toordinal(), final_date.toordinal())
        stats = cache.get(cache_name, None)

        if not stats or not settings.USE_CACHE:

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

            # prisma sexo
            prisma_sexo_idade_plot = plots.prisma_sexo_idade(initial_date, final_date)
            stats.update({
                'prisma_sexo_idade_plot': prisma_sexo_idade_plot,
            })


            # top polls
            qs = ProposicaoAggregated.objects.top_proposicoes(initial_date, final_date)[:500]
            stats.update({
                'top_proposicoes': [{
                    'proposicao_nome_processado': row['proposicao__nome_processado'],
                    'link': reverse('proposicao_detail', args=[row['proposicao__id']]),
                    'poll_votes': row['poll_votes'],
                    'poll_comments': row['poll_comments'],
                    'ficha_pageviews': row['ficha_pageviews'],
                } for row in qs]
            })

            # top news
            qs = PortalComentario.objects.get_top_news(initial_date, final_date)[:500]

            stats.update({
                'top_news': [{
                    'title': row['url__titulo'] or '',
                    'link': row['url__link'] or '',
                    'comments': row['comments'],
                } for row in qs]
            })

            cache.set(cache_name, stats, 86400)


    if not custom:
        return render(request, 'pages/relatorio/index.html', locals())
    else:
        if initial_date and final_date:
            try:
                if period_type == 'year':
                    return render(request, 'pages/relatorio/custom/{}.html'.format(year), locals())
                elif period_type == 'month_year':
                    return render(request, 'pages/relatorio/custom/{}.html'.format(month_year), locals())
            except:
                raise Http404
        raise Http404



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

