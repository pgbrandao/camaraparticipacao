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
    qs = ProposicaoFichaPageviews.objects.values('date').annotate(pageviews_total=Sum('pageviews')).order_by('date').values('date', 'pageviews_total')
    daily_ficha_pageviews = pd.DataFrame(qs)
    qs = Resposta.objects.extra(select={'date':'date(dat_resposta)'}).values('date').annotate(votes_total=Count('ide_resposta')).order_by('date').values('date', 'votes_total')
    daily_poll_votes = pd.DataFrame(qs)
    qs = Posicionamento.objects.extra(select={'date':'date(dat_posicionamento)'}).values('date').annotate(comments_total=Count('ide_posicionamento')).order_by('date').values('date', 'comments_total')
    daily_poll_comments = pd.DataFrame(qs)

    layout = Layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(x=0.025, y=1), height=310, margin=dict(t=0, l=15, r=10, b=0), barmode='stack')
    fig = go.Figure(layout=layout)
    daily_ficha_pageviews_trace = go.Bar(
        x=daily_ficha_pageviews.date if not daily_ficha_pageviews.empty else [None],
        y=daily_ficha_pageviews.pageviews_total if not daily_ficha_pageviews.empty else [None],
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
    fig.add_traces([daily_ficha_pageviews_trace, daily_poll_votes_trace, daily_poll_comments_trace])
    plot_div = plotly.io.to_html(fig, include_plotlyjs='cdn', config={'displayModeBar': False}, full_html=False)
    
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
        # rangeselector=dict(
        #     buttons=list([
        #         dict(count=7, label='W', step='day', stepmode='backward'),
        #         dict(count=1, label='M', step='month', stepmode='backward'),
        #         dict(count=3, label='3M', step='month', stepmode='backward', ),
        #         dict(label='T', step='all')
        #     ])
        # )
        # fixedrange=True,
        # dragmode="pan"
        # yaxis=dict(
        #     fixedrange=True
        # ),
        # display_mode_bar=False,
        # rangeslider=dict(
        #     visible = True
        # ),
        range=[datetime.date.today() - datetime.timedelta(days=90), datetime.date.today()]
    )
    fig.update_yaxes(gridcolor='#fff', fixedrange=True)
    fig.update_layout(dragmode='pan')
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
