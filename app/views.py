from django.conf import settings
from django.db.models import Count, Sum, Q
from django.shortcuts import render
from django.http import HttpResponse

import datetime
from . import plots

from .models import *

def BootstrapFilterView(request):
    sigla_tipo = request.GET.get('sigla_tipo')
    numero = request.GET.get('numero')
    ano = request.GET.get('ano')
    deputado_autor_relator_nome = request.GET.get('deputado_autor_relator_nome')

    date_min = None
    try:
        date_min = datetime.datetime.strptime('%d/%m/%Y', request.GET.get('date_min'))
    except ValueError:
        pass
    
    date_max = None
    try:
        date_max = datetime.datetime.strptime('%d/%m/%Y', request.GET.get('date_max'))
    except ValueError:
        pass

    qs = Proposicao.objects.all()
    if is_valid_queryparam(sigla_tipo):
        qs = qs.filter(sigla_tipo__icontains=sigla_tipo)
    if is_valid_queryparam(numero):
        qs = qs.filter(numero=numero)
    if is_valid_queryparam(ano):
        qs = qs.filter(ano=ano)
    if is_valid_queryparam(deputado_autor_relator_nome):
        qs = qs.filter(Q(ultimo_status_relator__nome__icontains=deputado_autor_relator_nome)
                     | Q(autor__nome__icontains=deputado_autor_relator_nome)).distinct()
    qs = qs.annotate(num_resposta=Count('formulario_publicado__resposta')).order_by('-num_resposta')[:50]
    #        .annotate(pageviews=Sum('proposicaopageview__pageviews')) \

    context = {
        'queryset': qs,
    }
    return render(request, "bootstrap_form.html", context)

def index(request):
    d0 = datetime.date.today()
    dm1 = datetime.date.today()-datetime.timedelta(days=1)
    dm7 = datetime.date.today()-datetime.timedelta(days=7)
    dm8 = datetime.date.today()-datetime.timedelta(days=8)
    dm14 = datetime.date.today()-datetime.timedelta(days=14)

    qs = ProposicaoAggregated.objects.all()

    votos_this_week = qs.filter(date__gte=dm7, date__lte=dm1).count()
    votos_past_week = qs.filter(date__gte=dm14, date__lte=dm8).count()
    votos_change = (votos_this_week / votos_past_week - 1) * 100 if votos_past_week else 0

    posicionamentos_this_week = Posicionamento.objects.filter(dat_posicionamento__gte=dm7, dat_posicionamento__lt=d0).count()
    posicionamentos_past_week = Posicionamento.objects.filter(dat_posicionamento__gte=dm14, dat_posicionamento__lt=dm7).count()
    posicionamentos_change = (posicionamentos_this_week / posicionamentos_past_week - 1) * 100 if posicionamentos_past_week else 0

    proposicao_pageview_this_week = ProposicaoPageview.objects.filter(date__gte=dm7, date__lt=d0).aggregate(Sum('pageviews'))['pageviews__sum'] or 0
    proposicao_pageview_past_week = ProposicaoPageview.objects.filter(date__gte=dm14, date__lt=dm7).aggregate(Sum('pageviews'))['pageviews__sum'] or 0  
    proposicao_pageview_change = (proposicao_pageview_this_week / proposicao_pageview_past_week - 1) * 100 if proposicao_pageview_past_week else 0

    daily_summary_global_plot = plots.daily_summary_global()

    qs = ProposicaoAggregated.objects.values('proposicao') \
        .annotate(poll_votes_total=Sum('poll_votes'), poll_votes_period=Sum('poll_votes', filter=Q(date__gte=dm7, date__lt=d0)),
                  poll_comments_total=Sum('poll_comments'), poll_comments_period=Sum('poll_comments', filter=Q(date__gte=dm7, date__lt=d0)),
                  pageviews_period=Sum('pageviews', filter=Q(date__gte=dm7, date__lt=d0)))
    fields_list = {'proposicao__id', 'proposicao__sigla_tipo', 'proposicao__numero', 'proposicao__ano', 'poll_votes_total', 'poll_votes_period', 'poll_comments_total', 'poll_comments_period', 'pageviews_period'}
    non_count = {'proposicao__id', 'proposicao__sigla_tipo', 'proposicao__numero', 'proposicao__ano'}
    records = list(qs.values(*fields_list))
    for record in records:
        for k, v in record.items():
            if v is None and k in fields_list - non_count:
                record[k] = 0
    
    import pdb;pdb.set_trace()
    # proposicoes = pd.DataFrame(, columns=fields_list, dtype=['int']*7)
    proposicoes = pd.DataFrame.from_records(records)

    if not proposicoes.empty:
        proposicoes['p_score'] = proposicoes['poll_votes_period'] + proposicoes['poll_comments_period'] + proposicoes['pageviews_period']
        proposicoes.sort_values(by=['p_score'], ascending=False, inplace=True)
        proposicoes = proposicoes[:50]

    import pdb;pdb.set_trace()

    return render(request, 'index.html', locals())

def enquetes_busca_data(request):
    date_min = None
    try:
        date_min = datetime.datetime.strptime(request.GET.get('date_min'), '%d/%m/%Y')
    except (ValueError, TypeError) as e:
        date_min = datetime.date.today()-datetime.timedelta(days=14)
    
    date_max = None
    try:
        date_max = datetime.datetime.strptime(request.GET.get('date_max'), '%d/%m/%Y')
    except (ValueError, TypeError) as e:
        date_max = datetime.date.today()-datetime.timedelta(days=1)

    qs = ProposicaoAggregated.objects.filter(date__gte=date_min, date__lte=date_max) \
        .values('proposicao') \
        .annotate(poll_votes_total=Sum('poll_votes'), poll_comments_total=Sum('poll_comments')) \
        .values('proposicao__id', 'proposicao__sigla_tipo', 'proposicao__numero', 'proposicao__ano', 'poll_votes_total', 'poll_comments_total')
    
    proposicoes = pd.DataFrame.from_records(qs)
    if not proposicoes.empty:
        proposicoes['p_score'] = proposicoes['poll_votes_total'] + proposicoes['poll_comments_total']
        proposicoes.sort_values(by=['p_score'], ascending=False, inplace=True)
        proposicoes = proposicoes[:50]

    return render(request, 'enquetes_busca_data.html', locals())

    

def proposicao_detail(request, id_proposicao):
    proposicao = Proposicao.objects.get(pk=id_proposicao)

    daily_summary_proposicao_plot = plots.daily_summary_proposicao(proposicao)

    return render(request, 'proposicao_details.html', locals())
