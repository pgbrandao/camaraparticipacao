import django_tables2 as tables
from .models import Proposicao

class ProposicaoTable(tables.Table):
    class Meta:
        model = Proposicao
        template_name = "django_tables2/bootstrap.html"
        fields = ('sigla_tipo', 'numero', 'ano', 'data_apresentacao', 'orgao_numerador', 'autor', 'tema')
