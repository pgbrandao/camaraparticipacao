from django.urls import path

from . import views

urlpatterns = [
    path('bootstrap/', views.BootstrapFilterView, name='bootstrap'),
    path('index/', views.index, name='index'),
    path('<int:id_proposicao>/', views.detail, name='detail')
]