# Generated by Django 3.0.6 on 2020-08-05 18:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0010_noticia_raw_data'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='noticia',
            options={'ordering': ['-data']},
        ),
        migrations.RemoveField(
            model_name='proposicao',
            name='autor',
        ),
        migrations.CreateModel(
            name='Autor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome_processado', models.TextField(blank=True, null=True)),
                ('deputado', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='app.Deputado')),
                ('orgao', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='app.Orgao')),
            ],
        ),
    ]
