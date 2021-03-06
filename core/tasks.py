from app import dataloader
from app import cache
from celery import shared_task

@shared_task
def dataloader_task():
    dataloader.load_comentarios_portal()
    dataloader.load_prisma()
    dataloader.load_enquetes()
    dataloader.load_deputados()
    dataloader.load_orgaos()
    dataloader.load_proposicoes()
    dataloader.load_proposicoes_autores()
    dataloader.load_proposicoes_temas()
    dataloader.load_analytics_fichas()
    dataloader.load_analytics_noticias()
    dataloader.preprocess_daily_summary()
    dataloader.preprocess_proposicoes()
    dataloader.preprocess_noticias()
    cache.rebuild_caches()
