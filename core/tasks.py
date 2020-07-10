from app import dataloader

from celery import shared_task

@shared_task
def dataloader():
    dataloader.load_enquetes(cmd=self)
    dataloader.load_deputados(cmd=self)
    dataloader.load_orgaos(cmd=self)
    dataloader.load_proposicoes(cmd=self)
    dataloader.load_proposicoes_autores(cmd=self)
    dataloader.load_proposicoes_temas(cmd=self)
    dataloader.load_analytics_proposicoes(cmd=self)
    dataloader.preprocess(cmd=self)
