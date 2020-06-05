from django.db.models import Count, Sum, Q
from django.shortcuts import render
from django.http import HttpResponse

import datetime
from .models import *


def is_valid_queryparam(param):
    return param != '' and param is not None

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
    # Proposições mais acessadas
    # proposicoes = Proposicao.objects.annotate(num_resposta=Count('formulario_publicado__resposta')).order_by('-num_resposta')[:50]

    return render(request, 'index.html')

def detail(request, id_proposicao):
    proposicao = Proposicao.objects.get(pk=id_proposicao)
    context = {
        'proposicao': proposicao,
    }
    return render(request, 'bootstrap_details.html', context)
