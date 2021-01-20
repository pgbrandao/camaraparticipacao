from django.core.management.base import BaseCommand, CommandError

from app import cache

class Command(BaseCommand):
    help = 'Rebuilds cache'

    def handle(self, *args, **options):
        cache.rebuild_caches()
