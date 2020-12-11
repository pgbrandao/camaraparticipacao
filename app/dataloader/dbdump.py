import os

from pathlib import Path

from django.conf import settings

def db_dump():
    dump_path = Path(settings.DB_DUMP_PATH) / Path('latest_dump.gz')
    os.system('PGPASSWORD="{}" pg_dump --host={} --username={} camaraparticipacao | gzip > {}'.format(
        settings.DATABASES['default']['PASSWORD'],
        settings.DATABASES['default']['HOST'],
        settings.DATABASES['default']['USER'],
        dump_path
    ))
