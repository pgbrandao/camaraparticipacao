# Generated by Django 3.0.6 on 2021-01-04 12:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0021_auto_20201223_1445'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='enqueteformulariopublicado',
            table='Formulario_Publicado',
        ),
        migrations.AlterModelTable(
            name='enqueteitemresposta',
            table='Item_Resposta',
        ),
        migrations.AlterModelTable(
            name='enqueteposicionamento',
            table='Posicionamento',
        ),
        migrations.AlterModelTable(
            name='enqueteresposta',
            table='Resposta',
        ),
        migrations.AlterModelTable(
            name='portalcomentario',
            table='COMENTARIO',
        ),
        migrations.AlterModelTable(
            name='portalcomentarioposicionamento',
            table='POSICIONAMENTO',
        ),
        migrations.AlterModelTable(
            name='prismaassunto',
            table='vwAssunto',
        ),
        migrations.AlterModelTable(
            name='prismacategoria',
            table='vwCategoria',
        ),
        migrations.AlterModelTable(
            name='prismademanda',
            table='vwDemanda',
        ),
        migrations.AlterModelTable(
            name='prismademandante',
            table='vwDemandante',
        ),
    ]
