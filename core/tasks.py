from app import dataloader
from celery import shared_task

@shared_task
def dataloader_task():
    dataloader.load_enquetes()
    dataloader.load_deputados()
    dataloader.load_orgaos()
    dataloader.load_proposicoes()
    dataloader.load_proposicoes_autores()
    dataloader.load_proposicoes_temas()
    dataloader.load_analytics_fichas()
    dataloader.load_analytics_noticias()
    dataloader.preprocess()
    dataloader.db_dump()
