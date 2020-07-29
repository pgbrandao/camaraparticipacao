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
            '--analytics-fichas',
            action='store_true',
            help='Syncs analytics (fichas)'
        )
        parser.add_argument(
            '--analytics-noticias',
            action='store_true',
            help='Syncs analytics (noticias)'
        )
        parser.add_argument(
            '--preprocess',
            action='store_true',
            help='Pre-processes data'
        )
        parser.add_argument(
            '--initial-date',
            nargs=1,
            type=str,
            help='Initial date (used exclusively for Google Analytics queries) (format: DD/MM/YYYY)'
        )

    def handle(self, *args, **options):
        if  not options['all'] and \
            not options['enquetes'] and \
            not options['dados_abertos'] and \
            not options['analytics_fichas'] and \
            not options['analytics_noticias'] and \
            not options['preprocess']:
            raise CommandError('No option specified.')

        if options['initial_date']:
            initial_date = datetime.datetime.strptime(options['initial_date'][0], '%d/%m/%Y').date()
        else:
            initial_date = None
        
        if options['all'] or options['enquetes']:
            dataloader.load_enquetes()
        if options['all'] or options['dados_abertos']:
            dataloader.load_deputados()
            dataloader.load_orgaos()
            dataloader.load_proposicoes()
            dataloader.load_proposicoes_autores()
            dataloader.load_proposicoes_temas()
        if options['all'] or options['analytics_fichas']:
            dataloader.load_analytics_fichas(initial_date=initial_date)
        if options['all'] or options['analytics_noticias']:
            dataloader.load_analytics_noticias(initial_date=initial_date)
        
        dataloader.preprocess()




