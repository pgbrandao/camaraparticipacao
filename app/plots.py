from django.db.models import Count, Sum

import pandas as pd 
import plotly
import plotly.express as px
import plotly.graph_objs as go
from plotly.graph_objs import Layout

import datetime

from .models import *


def daily_summary_global():
    """[summary] Plots daily votes, comments and daily proposal pageviews as stacked bar
    Reference: https://plotly.com/python/bar-charts/
    
    Returns:
        [plotly.graph_objs] -- [plot_div compatible with Django]
    """
    qs1 = ProposicaoAggregated.objects.values('date') \
        .annotate(ficha_pageviews_total=Sum('ficha_pageviews'), poll_votes_total=Sum('poll_votes'), poll_comments_total=Sum('poll_comments'))
    qs2 = NoticiaPageviews.objects.values('date') \
        .annotate(noticia_pageviews_total=Sum('pageviews'))
    df = pd.DataFrame(qs1).merge(pd.DataFrame(qs2), how='outer')

    daily_ficha_pageviews_trace = go.Bar(
        x=df.date,
        y=df.ficha_pageviews_total,
        name='Visualizações (fichas de tramitação)',
        marker_color='#f5365c')
    daily_noticia_pageviews_trace = go.Bar(
        x=df.date,
        y=df.noticia_pageviews_total,
        name='Visualizações (notícias)',
        marker_color='#fb6340')
    daily_poll_votes_trace = go.Bar(
        x=df.date,
        y=df.poll_votes_total,
        name='Votos nas enquetes',
        marker_color='#6236FF')
    daily_poll_comments_trace = go.Bar(
        x=df.date,
        y=df.poll_comments_total,
        name='Comentários nas enquetes',
        marker_color='#2dce89',)
    
    fig = plotly.tools.make_subplots(rows=4, cols=1, shared_xaxes=True)
    fig.update_xaxes(
        range=[datetime.date.today() - datetime.timedelta(days=90), datetime.date.today()],
        showspikes=True,
        spikethickness=2,
        spikedash="dot",
        spikecolor="#999999",
        spikemode="across",
    )
    fig.update_yaxes(gridcolor='#fff', fixedrange=True)
    fig.update_layout(
        dragmode='pan',
        hovermode='x',
        hoverdistance=100,
        spikedistance=1000, # Distance to show spike
        margin={
            'l': 0,
            'r': 0,
            'b': 0,
            't': 0,
        },
    )
    fig.append_trace(daily_ficha_pageviews_trace, 1, 1)
    fig.append_trace(daily_noticia_pageviews_trace, 2, 1)
    fig.append_trace(daily_poll_votes_trace, 3, 1)
    fig.append_trace(daily_poll_comments_trace, 4, 1)
    # fig.update_traces(xaxis='x1')

    post_script = """
        document.getElementById('{plot_id}').on('plotly_click', function(data){
            app.date = data.points[0]['x'];
        });
    """

    plot_div = plotly.io.to_html(fig, include_plotlyjs='cdn', config={'displayModeBar': False}, full_html=False, post_script=post_script)
    
    return plot_div

def daily_summary_proposicao(proposicao):
    qs = ProposicaoAggregated.objects.filter(proposicao=proposicao).order_by('date').values()
    daily_data = pd.DataFrame(qs)

    # layout = Layout(
    #     paper_bgcolor='rgba(0,0,0,0)',
    #     plot_bgcolor='rgba(0,0,0,0)',
    #     legend=dict(x=0.025, y=1),
    #     height=310,
    #     margin=dict(t=0, l=15, r=10, b=0),
    #     barmode='stack',
    #     dragmode="pan"
    # )
    daily_ficha_pageviews_trace = go.Bar(
        x=daily_data.date,
        y=daily_data.ficha_pageviews,
        name='Visualizações (ficha de tramitação)',
        marker_color='#f5365c')
    daily_noticia_pageviews_trace = go.Bar(
        x=daily_data.date,
        y=daily_data.noticia_pageviews,
        name='Visualizações (notícias)',
        marker_color='#fb6340')
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
    
    fig = plotly.tools.make_subplots(rows=4, cols=1, shared_xaxes=True)
    fig.update_xaxes(
        range=[datetime.date.today() - datetime.timedelta(days=90), datetime.date.today()]
    )
    fig.update_yaxes(gridcolor='#fff', fixedrange=True)
    fig.update_layout(
        dragmode='pan',
        margin={
            'l': 0,
            'r': 0,
            'b': 0,
            't': 0,
        },
    )
    fig.append_trace(daily_ficha_pageviews_trace, 1, 1)
    fig.append_trace(daily_noticia_pageviews_trace, 2, 1)
    fig.append_trace(daily_poll_votes_trace, 3, 1)
    fig.append_trace(daily_poll_comments_trace, 4, 1)
    # fig.add_traces([daily_pageviews_trace, daily_poll_votes_trace, daily_poll_comments_trace])
    plot_div = plotly.io.to_html(fig, include_plotlyjs='cdn', config={'displayModeBar': False}, full_html=False)
    
    return plot_div

def proposicao_heatmap(proposicao):
    qs = ProposicaoAggregated.objects.filter(proposicao=proposicao).order_by('date').values()
    df = pd.DataFrame(qs)

    # The following two lines convert a string date to a UNIX timestamp... kludgy
    df['date'] = pd.to_datetime(df['date'])
    df['ts'] = (df['date'].astype(int) / 10**9).astype(int)

    records = df.to_dict('records')
    values = {}
    for record in records:
        values[record['ts']] = record['ficha_pageviews']

    return values

def raiox(date_min, date_max, metric_field, plot_type, dimension):
    qs = ProposicaoAggregated.objects \
        .filter(date__gte=date_min, date__lte=date_max, **{metric_field+'__gt': 0}) \
        .annotate(metric_total=Sum(metric_field))
    
    if dimension == 'tema':
        qs = qs.values('proposicao__pk', 'proposicao__nome_processado', 'metric_total', 'proposicao__tema__nome')
    elif dimension == 'autor':
        qs = qs.values('proposicao__pk', 'proposicao__nome_processado', 'metric_total', 'proposicao__autor__nome')
    elif dimension == 'relator':
        qs = qs.values('proposicao__pk', 'proposicao__nome_processado', 'metric_total', 'proposicao__ultimo_status_relator__nome')
    elif dimension == 'situacao':
        qs = qs.values('proposicao__pk', 'proposicao__nome_processado', 'metric_total', 'proposicao__ultimo_status_situacao_descricao')
    elif dimension == 'indexacao':
        qs = qs.values('proposicao__pk', 'proposicao__nome_processado', 'metric_total', 'proposicao__keywords')
    elif dimension == 'proposicao':
        qs = qs.values('proposicao__pk', 'proposicao__nome_processado', 'metric_total')
    
    df = pd.DataFrame.from_records(qs)

    if df.empty:
        return (' ', 0, 0)
    df['proposicao__pk'] = df['proposicao__pk'].astype(str)

    if dimension == 'tema':
        path = ['proposicao__tema__nome', 'proposicao__nome_processado']
        df['proposicao__tema__nome'] = df['proposicao__tema__nome'].fillna('Não classificado')
    elif dimension == 'autor':
        path = ['proposicao__autor__nome', 'proposicao__nome_processado']
        df['proposicao__autor__nome'] = df['proposicao__autor__nome'].fillna('Sem deputado autor')
    elif dimension == 'relator':
        path = ['proposicao__ultimo_status_relator__nome', 'proposicao__nome_processado']
        df['proposicao__ultimo_status_relator__nome'] = df['proposicao__ultimo_status_relator__nome'].fillna('Sem relator')
    elif dimension == 'situacao':
        path = ['proposicao__ultimo_status_situacao_descricao', 'proposicao__nome_processado']
        df['proposicao__ultimo_status_situacao_descricao'] = df['proposicao__ultimo_status_situacao_descricao'].replace(r'^\s*$', 'Sem situação', regex=True)
        df['proposicao__ultimo_status_situacao_descricao'] = df['proposicao__ultimo_status_situacao_descricao'].fillna('Sem situação')
    elif dimension == 'indexacao':
        path = ['proposicao__keywords', 'proposicao__nome_processado']
        # TODO: Check why this still isn't working
        def comma_split(x):
            x = x.split(',')
            x = [y for y in x if not y.isspace()]
            if not any(x):
                x = ['Sem indexação']
            return x
        df['proposicao__keywords'] = df['proposicao__keywords'].apply(comma_split)
        df = df.explode('proposicao__keywords')
        
    elif dimension == 'proposicao':
        path = ['proposicao__nome_processado']

    # Group proposicoes lower than threshold

    # TODO: Maybe this can be improved by:
    # 1. Grouping the excluded items and showing them in the graph for precision
    # 2. Considering the threshold inside each dimension item.

    total = df['metric_total'].sum()
    threshold = 0.0001 * total
    df = df[df['metric_total'] >= threshold]
    total_plot = df['metric_total'].sum()

    if plot_type=='treemap':
        fig = px.treemap(df, path=path, values='metric_total', custom_data=['proposicao__pk'])
        fig.update_layout(
            width=1200,
            height=900
        )
    else: # Sunburst is the fallback
        fig = px.sunburst(df, path=path, values='metric_total', custom_data=['proposicao__pk'])
        fig.update_layout(
            width=900,
            height=900
        )

    from django.urls import reverse
    base_url = reverse('proposicao_detail', args=[0])

    post_script = """
        document.getElementById('{plot_id}').on('plotly_click', function(data){
            if(!isNaN(data.points[0].customdata[0])) {
                window.location.href='base_url'.replace('0', data.points[0].customdata[0]);
            }
        });
    """.replace('base_url', base_url)
    plot_div = plotly.io.to_html(fig, include_plotlyjs='cdn', full_html=False, post_script=post_script)

    return (plot_div, total, total_plot)
