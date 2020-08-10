from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('enquetes/busca_data/', views.enquetes_busca_data, name='enquetes_busca_data'),
    path('raio-x/', views.raiox, name='raiox'),
    path('proposicao/busca/', views.busca_proposicao, name='busca_proposicao'),
    path('proposicao/<int:id_proposicao>/', views.proposicao_detail, name='proposicao_detail'),
    path('proposicao/<int:id_proposicao>/comentarios_enquete/', views.proposicao_comentarios_enquete, name='proposicao_comentarios_enquete'),
    path('api/top-noticias/', views.api_top_noticias, name='api_top_noticias'),
    path('api/top-proposicoes/', views.api_top_proposicoes, name='api_top_proposicoes'),
]