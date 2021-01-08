# Generated by Django 3.0.6 on 2020-12-21 14:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0019_auto_20201217_1628'),
    ]

    operations = [
        migrations.DeleteModel(
            name='PortalComentario',
        ),
        migrations.CreateModel(
            name='PortalComentario',
            fields=[
                ('id', models.CharField(max_length=500, primary_key=True, serialize=False)),
                ('usuario_id', models.CharField(max_length=100)),
                ('data', models.DateTimeField()),
                ('comentario', models.TextField(blank=True, null=True)),
                ('sistema', models.CharField(blank=True, max_length=100, null=True)),
                ('situacao', models.CharField(blank=True, max_length=100, null=True)),
                ('usuario_nome', models.CharField(blank=True, max_length=100, null=True)),
                ('url', models.ForeignKey(db_column='url', blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='app.Noticia')),
            ],
        ),
    ]