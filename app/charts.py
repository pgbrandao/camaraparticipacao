from django.db.models import Count

import altair

from core.models import *

def get_votes_chart(proposicao):
    EnqueteItemResposta.objects.filter(resposta__ide_formulario_publicado=proposicao.formulario_publicado.pk) \
                        .values('num_indice_opcao') \
                        .order_by('num_indice_opcao') \
                        .annotate(votos=Count('num_indice_opcao'))

    source = {
        'cats': ['Concordo totalmente', 'Concordo na maior parte', 'Estou indeciso', 'Discordo na maior parte', 'Discordo totalmente'],
        'votos': [qs.get(num_indice_opcao=4)['votos'],
                  qs.get(num_indice_opcao=3)['votos'],
                  qs.get(num_indice_opcao=2)['votos'], 
                  qs.get(num_indice_opcao=1)['votos'], 
                  qs.get(num_indice_opcao=0)['votos']]
    }

    chart = alt.Chart(source).mark_bar().encode(
        x=alt.X('cats', axis=alt.Axis(labels=False, ticks=False), title=None, type='nominal', sort=None),
        y=alt.Y('votos', axis=alt.Axis(labels=False, ticks=False), title=None),
        color=alt.Color('cats', title='Escala Likert', scale=alt.Scale(
            range=['rgb(89,162,74)', 'rgb(157,198,77)', 'rgb(102,143,205)', 'rgb(215,51,23)', 'rgb(155,37,17)']), sort=None),
        tooltip=['cats', 'votos']
    ).configure_axis(
        grid=False
    ).properties(
        width=120,
        height=80
    )
    return chart