from django.db.models import Count, Q
from django.shortcuts import render
from django.http import HttpResponse

from django_tables2 import SingleTableView

from .models import *
from .tables import *

class ProposicaoListView(SingleTableView):
    model = Proposicao
    table_class = ProposicaoTable
    template_name = 'enquetes/table.html'

def is_valid_queryparam(param):
    return param != '' and param is not None

def BootstrapFilterView(request):
    sigla_tipo = request.GET.get('sigla_tipo')
    numero = request.GET.get('numero')
    ano = request.GET.get('ano')
    deputado_autor_relator_nome = request.GET.get('deputado_autor_relator_nome')
    date_min = request.GET.get('date_min')
    date_max = request.GET.get('date_max')

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

    context = {
        'queryset': qs,
    }
    return render(request, "enquetes/bootstrap_form.html", context)

def index(request):
    # Proposições mais acessadas
    proposicoes = Proposicao.objects.annotate(num_resposta=Count('formulario_publicado__resposta')).order_by('-num_resposta')[:50]

    return render(request, 'enquetes/index.html', {'proposicoes': proposicoes})

def detail(request, id_proposicao):
    return render(request, 'enquetes/detail.html')
