# Generated by Django 3.0.6 on 2020-12-23 14:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0020_auto_20201221_1459'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dailysummary',
            name='atendimentos_autosservico',
        ),
        migrations.RemoveField(
            model_name='dailysummary',
            name='atendimentos_telefone',
        ),
        migrations.AddField(
            model_name='dailysummary',
            name='atendimentos',
            field=models.IntegerField(default=0),
        ),
    ]
