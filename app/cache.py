import datetime
import json

import pandas as pd

from django.core.cache import cache

def rebuild_caches():
    from . import reports

    for year_start in pd.date_range(start='2019-01-01', end=datetime.date.today(), freq='YS').sort_values(ascending=False):
        year_end = year_start.replace(month=12, day=31)
        year_start = year_start.to_pydatetime().date()
        year_end = year_end.to_pydatetime().date()

        reports.api_top_noticias(initial_date=year_start, final_date=year_end, save_cache=True)
        reports.api_top_proposicoes(initial_date=year_start, final_date=year_end, save_cache=True)
        reports.enquetes_temas(initial_date=year_start, final_date=year_end, save_cache=True)
        reports.proposicoes_temas(initial_date=year_start, final_date=year_end, save_cache=True)
        reports.noticias_temas(initial_date=year_start, final_date=year_end, save_cache=True)
        reports.noticias_tags(initial_date=year_start, final_date=year_end, save_cache=True)
        reports.api_relatorio_consolidado(initial_date=year_start, final_date=year_end, save_cache=True)
        reports.relatorio_consolidado(initial_date=year_start, final_date=year_end, save_cache=True)

    for month_start in pd.date_range(start='2019-01-01', end=datetime.date.today(), freq='MS').sort_values(ascending=False):
        month_end = month_start.replace(day=month_start.days_in_month)

        month_start = month_start.to_pydatetime().date()
        month_end = month_end.to_pydatetime().date()

        reports.api_top_noticias(initial_date=month_start, final_date=month_end, save_cache=True)
        reports.api_top_proposicoes(initial_date=month_start, final_date=month_end, save_cache=True)
        reports.relatorio_consolidado(initial_date=month_start, final_date=month_end, save_cache=True)

    for day in pd.date_range(start='2019-01-01', end=datetime.date.today()).sort_values(ascending=False):
        day = day.to_pydatetime().date()

        reports.api_top_noticias(initial_date=day, final_date=day, save_cache=True)
        reports.api_top_proposicoes(initial_date=day, final_date=day, save_cache=True)

