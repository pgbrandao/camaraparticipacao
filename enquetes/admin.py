from django.contrib import admin
from .models import *

class ProposicaoAdmin(admin.ModelAdmin):
    list_display = ('sigla_tipo', 'numero', 'ano', 'data_apresentacao', 'ultimo_status_data')
    list_filter = ('sigla_tipo',)
    filter_vertical = ('tema',)
    raw_id_fields = ("orgao_numerador","formulario_publicado","autor","ultimo_status_relator","ultimo_status_orgao")
class DeputadoAdmin(admin.ModelAdmin):
    list_display = ('nome','partido', 'uf')
class OrgaoAdmin(admin.ModelAdmin):
    list_display = ('sigla', 'nome',)
class TemaAdmin(admin.ModelAdmin):
    list_display = ('nome',)

admin.site.register(Orgao, OrgaoAdmin)
admin.site.register(Proposicao, ProposicaoAdmin)
admin.site.register(Deputado, DeputadoAdmin)
admin.site.register(Tema, TemaAdmin)