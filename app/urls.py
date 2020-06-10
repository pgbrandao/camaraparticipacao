from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('proposicao/<int:id_proposicao>/', views.proposicao_detail, name='proposicao_detail')
]