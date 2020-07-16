from django.db.models import Count, Sum

import pandas as pd 
import plotly.express as px
import plotly.graph_objs as go
from plotly.graph_objs import Layout
from plotly.offline import plot

import datetime

from .models import *

def daily_summary_global():
    """[summary] Plots daily votes, comments and daily proposal pageviews as stacked bar
    Reference: https://plotly.com/python/bar-charts/
    
    Returns:
        [plotly.graph_objs] -- [plot_div compatible with Django]
    """
    qs = ProposicaoPageview.objects.values('date').annotate(pageviews_total=Sum('pageviews')).order_by('date').values('date', 'pageviews_total')
    daily_pageviews = pd.DataFrame(qs)
    qs = Resposta.objects.extra(select={'date':'date(dat_resposta)'}).values('date').annotate(votes_total=Count('ide_resposta')).order_by('date').values('date', 'votes_total')
    daily_poll_votes = pd.DataFrame(qs)
    qs = Posicionamento.objects.extra(select={'date':'date(dat_posicionamento)'}).values('date').annotate(comments_total=Count('ide_posicionamento')).order_by('date').values('date', 'comments_total')
    daily_poll_comments = pd.DataFrame(qs)

    layout = Layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(x=0.025, y=1), height=310, margin=dict(t=0, l=15, r=10, b=0), barmode='stack')
    fig = go.Figure(layout=layout)
    daily_pageviews_trace = go.Bar(
        x=daily_pageviews.date if not daily_pageviews.empty else [None],
        y=daily_pageviews.pageviews_total if not daily_pageviews.empty else [None],
        name='Visualizações (ficha de tramitação)',
        marker_color='#f5365c')
    daily_poll_votes_trace = go.Bar(
        x=daily_poll_votes.date if not daily_poll_votes.empty else [None],
        y=daily_poll_votes.votes_total if not daily_poll_votes.empty else [None],
        name='Votos na enquete',
        marker_color='#6236FF')
    daily_poll_comments_trace = go.Bar(
        x=daily_poll_comments.date if not daily_poll_comments.empty else [None],
        y=daily_poll_comments.comments_total if not daily_poll_comments.empty else [None],
        name='Comentários na enquete',
        marker_color='#2dce89',)
    
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=7, label='W', step='day', stepmode='backward'),
                dict(count=1, label='M', step='month', stepmode='backward'),
                dict(count=3, label='3M', step='month', stepmode='backward', ),
                # dict(label='T', step='all')
            ]))
        )
    
    d0 = datetime.date.today()
    dm30 = d0 - datetime.timedelta(days=31)

    fig.update_xaxes(range=[dm30, d0])
    fig.update_yaxes(gridcolor='#fff')
    fig.add_traces([daily_pageviews_trace, daily_poll_votes_trace, daily_poll_comments_trace])
    plot_div = plot(fig, output_type='div', config={'displayModeBar': False})
    
    return plot_div
    
def daily_summary_proposicao(proposicao):
    """[summary] Plots daily votes, comments and daily proposal pageviews as stacked bar
    Reference: https://plotly.com/python/bar-charts/
    
    Returns:
        [plotly.graph_objs] -- [plot_div compatible with Django]
    """
    qs = ProposicaoAggregated.objects.filter(proposicao=proposicao).order_by('date').values()
    daily_data = pd.DataFrame(qs)

    layout = Layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(x=0.025, y=1), height=310, margin=dict(t=0, l=15, r=10, b=0), barmode='stack')
    fig = go.Figure(layout=layout)
    daily_pageviews_trace = go.Bar(
        x=daily_data.date,
        y=daily_data.pageviews,
        name='Visualizações (ficha de tramitação)',
        marker_color='#f5365c')
    daily_poll_votes_trace = go.Bar(
        x=daily_data.date,
        y=daily_data.poll_votes,
        name='Votos na enquete',
        marker_color='#6236FF')
    daily_poll_comments_trace = go.Bar(
        x=daily_data.date,
        y=daily_data.poll_comments,
        name='Comentários na enquete',
        marker_color='#2dce89',)
    
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=7, label='W', step='day', stepmode='backward'),
                dict(count=1, label='M', step='month', stepmode='backward'),
                dict(count=3, label='3M', step='month', stepmode='backward', ),
                dict(label='T', step='all')
            ]))
        )
    
    # d0 = datetime.date.today()
    # dm30 = d0 - datetime.timedelta(days=31)

    # fig.update_xaxes(range=[dm30, d0])
    fig.update_yaxes(gridcolor='#fff')
    fig.add_traces([daily_pageviews_trace, daily_poll_votes_trace, daily_poll_comments_trace])
    plot_div = plot(fig, output_type='div', config={'displayModeBar': False})
    
    return plot_div

def sunburst_proposicao_tema(date_min, date_max, metric_field):
    qs = ProposicaoAggregated.objects \
        .filter(date__gte=date_min, date__lte=date_max, poll_votes__gt=0) \
        .annotate(metric_total=Sum(metric_field)) \
        .values('proposicao__pk', 'proposicao__sigla_tipo', 'proposicao__numero', 'proposicao__ano', 'metric_total', 'proposicao__tema__nome')
    df = pd.DataFrame.from_records(qs)

    # g = df.groupby(['proposicao__pk', 'proposicao__sigla_tipo', 'proposicao__numero', 'proposicao__ano', 'poll_votes_total'])

    # def f(group):
    #     if len(group) > 1:
    #         return 'Múltiplos temas'
    #     elif len(group) == 1:
    #         if group.iloc[0] is None:
    #             return 'Não classificado'
    #         else:
    #             return group.iloc[0]

    # df = g['proposicao__tema__nome'].apply(f).reset_index()

    df['proposicao_nome'] = df['proposicao__sigla_tipo'] + ' ' + df['proposicao__numero'].astype(str) + '/' + df['proposicao__ano'].astype(str)
    df['proposicao__tema__nome'] = df['proposicao__tema__nome'].fillna('Não classificado')
    fig = px.sunburst(df, path=['proposicao__tema__nome', 'proposicao_nome'], values='metric_total')
    fig.update_layout(
        width=700,
        height=700
    )
    plot_div = plot(fig, output_type='div', config={})
    return plot_div

