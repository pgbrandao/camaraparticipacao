# Generated by Django 3.0.3 on 2020-05-13 15:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('enquetes', '0002_auto_20200513_1524'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='proposta',
            name='formulario_publicado',
        ),
    ]
