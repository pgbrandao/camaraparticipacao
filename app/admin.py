from django.contrib import admin
from django.db.models.functions import Length
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
class FormularioPublicadoAdmin(admin.ModelAdmin):
    list_display = ('tex_url_formulario_publicado', 'nom_titulo_formulario_publicado', 'dat_inicio_vigencia', 'dat_fim_vigencia')
class RespostaAdmin(admin.ModelAdmin):
    list_display = ('ide_formulario_publicado','ide_usuario','dat_resposta')
    raw_id_fields = ('ide_formulario_publicado',)
class PosicionamentoAdmin(admin.ModelAdmin):
    list_display = ('indicador_positivo', 'des_conteudo', 'classification')
    raw_id_fields = ('ide_formulario_publicado', 'ide_resposta')
    actions = ['make_insightful', 'make_not_insightful', 'make_unrated']
    def make_insightful(self, request, queryset):
        self.set_classification(request, queryset, PosicionamentoExtra.ClassificationTypes.INSIGHTFUL)
    make_insightful.short_description = "Mark selected as insightful"

    def make_not_insightful(self, request, queryset):
        self.set_classification(request, queryset, PosicionamentoExtra.ClassificationTypes.NOT_INSIGHTFUL)
    make_not_insightful.short_description = "Mark selected as not insightful"

    def make_unrated(self, request, queryset):
        self.set_classification(request, queryset, PosicionamentoExtra.ClassificationTypes.UNRATED)
    make_unrated.short_description = "Mark selected as unrated"

    def set_classification(self, request, queryset, classification):
        for q in queryset:
            try:
                q.posicionamentoextra.update(classification=classification)
            except PosicionamentoExtra.DoesNotExist:
                PosicionamentoExtra.objects.create(
                    posicionamento=q,
                    classification=classification
                )
    make_insightful.short_description = "Mark selected as insightful"

    def indicador_positivo(self,posicionamento):
        if posicionamento.ind_positivo == 1:
            return 'Positivo'
        elif posicionamento.ind_positivo == 0:
            return 'Negativo'
        else:
            return ''
    indicador_positivo.admin_order_field = 'ind_positivo'

    def classification(self,posicionamento):
        try:
            return PosicionamentoExtra.ClassificationTypes(posicionamento.posicionamentoextra.classification).label
        except:
            return ''
    classification.admin_order_field = 'posicionamentoextra__classification'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(text_len=Length('des_conteudo'))
        # if request.GET.get('min_length', None):
        #     qs = qs.filter(text_len__gte=int(request.GET['min_length']))
        # if request.GET.get('max_length', None):
        #     qs = qs.filter(text_len__lte=int(request.GET['max_length']))
        qs = qs.order_by('?')
        return qs

    
class ItemRespostaAdmin(admin.ModelAdmin):
    list_display = ('ide_resposta','num_indice_opcao')
    raw_id_fields = ('ide_resposta',)
class ProposicaoFichaPageviewsAdmin(admin.ModelAdmin):
    list_display = ('proposicao', 'date', 'pageviews')

admin.site.register(Orgao, OrgaoAdmin)
admin.site.register(Proposicao, ProposicaoAdmin)
admin.site.register(Deputado, DeputadoAdmin)
admin.site.register(Tema, TemaAdmin)
admin.site.register(FormularioPublicado, FormularioPublicadoAdmin)
admin.site.register(Resposta, RespostaAdmin)
admin.site.register(ItemResposta, ItemRespostaAdmin)
admin.site.register(Posicionamento, PosicionamentoAdmin)
admin.site.register(ProposicaoFichaPageviews, ProposicaoFichaPageviewsAdmin)
