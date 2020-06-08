# Generated by Django 3.0.6 on 2020-06-06 21:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0004_posicionamentoextra'),
    ]

    operations = [
        migrations.AlterField(
            model_name='posicionamentoextra',
            name='posicionamento',
            field=models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, to='app.Posicionamento'),
        ),
        migrations.CreateModel(
            name='ProposicaoAggregated',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('pageviews', models.IntegerField(default=0)),
                ('poll_votes', models.IntegerField(default=0)),
                ('poll_comments', models.IntegerField(default=0)),
                ('proposicao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.Proposicao')),
            ],
            options={
                'unique_together': {('proposicao', 'date')},
            },
        ),
    ]