from django.urls import path

from . import views

from django.contrib.auth.views import LoginView

urlpatterns = [
    path('login/', LoginView.as_view(template_name='admin/login.html')),
    path('', views.index, name='index'),
    path('enquetes/busca-data/', views.enquetes_busca_data, name='enquetes_busca_data'),
    path('enquetes/exportar-comentarios/', views.enquetes_exportar_comentarios, name='enquetes_exportar_comentarios'),
    path('db-dump/', views.db_dump, name='db_dump'),
    path('raio-x/', views.raiox, name='raiox'),
    path('relatorio-consolidado/', views.relatorio_consolidado, name='relatorio_consolidado'),
    path('proposicao/busca/', views.busca_proposicao, name='busca_proposicao'),
    path('proposicao/<int:id_proposicao>/', views.proposicao_detail, name='proposicao_detail'),
    path('proposicao/<int:id_proposicao>/comentarios_enquete/', views.proposicao_comentarios_enquete, name='proposicao_comentarios_enquete'),
    path('api/top-noticias/', views.api_top_noticias, name='api_top_noticias'),
    path('api/top-proposicoes/', views.api_top_proposicoes, name='api_top_proposicoes'),
]