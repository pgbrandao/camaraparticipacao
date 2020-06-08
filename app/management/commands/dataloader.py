from django.core.management.base import BaseCommand, CommandError

from app import dataloader

import datetime

class Command(BaseCommand):
    help = 'Syncs database with external sources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Syncs all data'
        )
        parser.add_argument(
            '--enquetes',
            action='store_true',
            help='Syncs enquetes'
        )
        parser.add_argument(
            '--dados-abertos',
            action='store_true',
            help='Syncs dados abertos'
        )
        parser.add_argument(
            '--analytics',
            action='store_true',
            help='Syncs analytics'
        )
        parser.add_argument(
            '--preprocess',
            action='store_true',
            help='Pre-processes data'
        )

    def handle(self, *args, **options):
        if  not options['all'] and \
            not options['enquetes'] and \
            not options['dados_abertos'] and \
            not options['analytics'] and \
            not options['preprocess']:
            raise CommandError('No option specified.')

        if options['all'] or options['enquetes']:
            dataloader.load_enquetes(cmd=self)
        if options['all'] or options['dados_abertos']:
            dataloader.load_deputados(cmd=self)
            dataloader.load_orgaos(cmd=self)
            dataloader.load_proposicoes(cmd=self)
            dataloader.load_proposicoes_autores(cmd=self)
            dataloader.load_proposicoes_temas(cmd=self)
        if options['all'] or options['analytics']:
            dataloader.load_analytics_proposicoes(cmd=self)
        
        dataloader.preprocess(cmd=self)




