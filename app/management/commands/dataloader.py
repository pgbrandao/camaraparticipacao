from django.core.management.base import BaseCommand, CommandError

from app import cache
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
            '--comentarios-portal',
            action='store_true',
            help='Syncs comentarios portal'
        )
        parser.add_argument(
            '--prisma',
            action='store_true',
            help='Syncs prisma'
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
            '--rebuild-cache',
            action='store_true',
            help='Rebuilds cache'
        )
        parser.add_argument(
            '--initial-date',
            nargs=1,
            type=str,
            help='Initial date (used exclusively for Google Analytics queries) (format: DD/MM/YYYY)'
        )

    def handle(self, *args, **options):
        if  not any([
            options['all'],
            options['comentarios_portal'],
            options['prisma'],
            options['enquetes'],
            options['dados_abertos'],
            options['analytics_fichas'],
            options['analytics_noticias'],
            options['preprocess'],
        ]):
            raise CommandError('No option specified.')

        if options['initial_date']:
            initial_date = datetime.datetime.strptime(options['initial_date'][0], '%d/%m/%Y').date()
        else:
            initial_date = None
        
        if options['all'] or options['comentarios_portal']:
            dataloader.load_comentarios_portal()
        if options['all'] or options['prisma']:
            dataloader.load_prisma()
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
        if options['all'] or options['preprocess']:
            dataloader.preprocess_daily_summary()
            dataloader.preprocess_noticias()
            dataloader.preprocess_proposicoes()
        if options['all'] or options['rebuild_cache']:
            cache.rebuild_caches()
