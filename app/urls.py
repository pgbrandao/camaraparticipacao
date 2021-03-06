import re

from django.conf import settings
from django.urls import include, path, re_path

from . import views

from django.contrib.auth.views import LoginView


dashboard_urls = [

    # API urls (used within Django and from camara-participacao-ui)
    path('api/relatorio-consolidado/', views.api_relatorio_consolidado, name='api_relatorio_consolidado'),
    re_path(r'api/top-proposicoes/(?:(?P<initial_date>[\d-]+)/)?(?:(?P<final_date>[\d-]+)/)?$', views.api_top_proposicoes, name='api_top_proposicoes'),
    re_path(r'api/top-noticias/(?:(?P<initial_date>[\d-]+)/)?(?:(?P<final_date>[\d-]+)/)?$', views.api_top_noticias, name='api_top_noticias'),


    # Django report pages
    path('', views.index, name='index'),

    path('relatorio-consolidado/', views.relatorio_consolidado, name='relatorio_consolidado'),

    re_path(r'enquetes/temas/(?:(?P<year>\d+)/)?$', views.enquetes_temas, name='enquetes_temas'),
    path('enquetes/busca-data/', views.enquetes_busca_data, name='enquetes_busca_data'),
    path('enquetes/exportar-comentarios/', views.enquetes_exportar_comentarios, name='enquetes_exportar_comentarios'),

    path('proposicoes/busca/', views.busca_proposicao, name='busca_proposicao'),
    re_path(r'proposicoes/temas/(?:(?P<year>\d+)/)?$', views.proposicoes_temas, name='proposicoes_temas'),
    path('proposicoes/<int:id_proposicao>/', views.proposicao_detail, name='proposicao_detail'),
    path('proposicoes/<int:id_proposicao>/comentarios_enquete/', views.proposicao_comentarios_enquete, name='proposicao_comentarios_enquete'),

    re_path(r'noticias/temas/(?:(?P<year>\d+)/)?$', views.noticias_temas, name='noticias_temas'),
    re_path(r'noticias/tags/(?:(?P<year>\d+)/)?$', views.noticias_tags, name='noticias_tags'),



    path('login/', LoginView.as_view(template_name='admin/login.html')),
]

dashboard_prefix = re.search(r'/(.*)', settings.DASHBOARD_BASE_PATH).group(1)

urlpatterns = [
    path(dashboard_prefix, include(dashboard_urls)),
]