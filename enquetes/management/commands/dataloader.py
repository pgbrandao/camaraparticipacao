from django.core.management.base import BaseCommand, CommandError

from enquetes import dataloader

import datetime

class Command(BaseCommand):
    def handle(self, *args, **options):
        # dataloader.load_enquetes(cmd=self,initial=False)
        # dataloader.load_deputados(cmd=self)
        # dataloader.load_orgaos(cmd=self)
        dataloader.load_proposicoes(cmd=self)
        # dataloader.load_proposicoes_autores(cmd=self)
        # dataloader.load_proposicoes_temas(cmd=self)

