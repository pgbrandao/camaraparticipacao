from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('enquetes/busca_data/', views.enquetes_busca_data, name='enquetes_busca_data'),
    path('raio-x/<slug:dimension>/', views.raiox, name='raiox'),
    path('proposicao/busca/', views.busca_proposicao, name='busca_proposicao'),
    path('proposicao/<int:id_proposicao>/', views.proposicao_detail, name='proposicao_detail'),
]