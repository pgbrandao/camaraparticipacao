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
        marker_color='#f5365c',)
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
    
    fig = plotly.tools.make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
    )
    fig.update_xaxes(
        range=[datetime.date.today() - datetime.timedelta(days=90), datetime.date.today()],
        showspikes=True,
        spikethickness=2,
        spikedash="dot",
        spikecolor="#999999",
        spikemode="across+marker",
        spikesnap="data"
    )
    fig.update_yaxes(gridcolor='#fff', fixedrange=True)
    fig.update_layout(
        dragmode='pan',
        hovermode='x unified',
        hoverdistance=1000,
        spikedistance=-1,
        margin={
            'l': 0,
            'r': 0,
            'b': 0,
            't': 0,
        },
        hoverlabel=dict(
            namelength=-1,
         )
    )
    fig.append_trace(daily_ficha_pageviews_trace, 1, 1)
    fig.append_trace(daily_noticia_pageviews_trace, 2, 1)
    fig.append_trace(daily_poll_votes_trace, 3, 1)
    fig.append_trace(daily_poll_comments_trace, 4, 1)
    fig.update_traces(xaxis='x4')

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

def raiox_anual(year, metric_field, dimension):
    if dimension == 'tema':
        dimension_field = 'proposicao__tema__nome'
    elif dimension == 'autor':
        dimension_field = 'proposicao__autor__nome_processado'
    elif dimension == 'relator':
        dimension_field = 'proposicao__ultimo_status_relator__nome'
    elif dimension == 'indexacao':
        return 'Não disponível'

        # Muiitos problemas a serem corrigidos nessa visualização.
        # dimension_field = 'proposicao__keywords'
    elif dimension == 'situacao':
        dimension_field = 'proposicao__ultimo_status_situacao_descricao'
    else:
        return 'Não disponível'


    initial = datetime.date(year=int(year), month=1, day=1)
    final = datetime.date(year=int(year), month=12, day=31)

    qs = ProposicaoAggregated.objects.filter(date__gte=initial, date__lte=final, **{metric_field+'__gt': 0}).values(metric_field, 'date', dimension_field)
    df = pd.DataFrame.from_records(qs)

    # if dimension == 'indexacao':
    #     def comma_split(x):
    #         x = x.split(',')
    #         x = [y for y in x if not y.isspace()]
    #         if not any(x):
    #             x = ['Sem indexação']
    #         return x
    #     df['proposicao__keywords'] = df['proposicao__keywords'].apply(comma_split)
    #     df = df.explode('proposicao__keywords')

    df = df.rename(columns={metric_field: 'metric'})

    df['date'] = pd.to_datetime(df['date'])
    dfg = df.groupby([pd.Grouper(key='date', freq='M'), dimension_field]).metric.agg('sum')
    dfg = dfg.reset_index()

    dfg['metric_normalized'] = dfg.groupby('date')['metric'].transform(lambda x: 100*x/x.sum())
    dfg['metric_normalized'] = dfg['metric_normalized'].map('{:.2f} %'.format)
    # dfg = dfg.sort_values('metric_normalized', ascending=False)

    # To calculate top dimensions, the metric is summed over the entire period and inversely sorted
    top_dimensions = dfg \
        .groupby(dimension_field)['metric'] \
        .sum() \
        .reset_index() \
        .sort_values('metric', ascending=False) \
        .reset_index(drop=True)
    
    if dimension == 'indexacao':
        top_dimensions = top_dimensions[:500]

    traces_dimensions = []
    for i, row in top_dimensions.iterrows():
        dimension_value = row[dimension_field]
        most_important = i < len(px.colors.qualitative.T10) - 1

        if most_important:
            color = px.colors.qualitative.T10[i]
        else:
            color = px.colors.qualitative.T10[-1]

        dfg_dimension = dfg[dfg[dimension_field] == dimension_value]

        dfg_dimension['date_formatted'] = dfg_dimension['date'].dt.strftime('%B %Y')

        traces_dimensions.append(
            go.Bar(
                x=dfg_dimension.date_formatted,
                y=dfg_dimension.metric_normalized,
                name=dimension_value,
                marker_color=color,
                showlegend=most_important,
            )
        )

    # Sums have to be calculated separately, since proposicoes repeat amongst various categories
    # The same process as above is repeated, but without the categorical dimension
    qs = ProposicaoAggregated.objects.filter(date__gte=initial, date__lte=final, **{metric_field+'__gt': 0}).values(metric_field, 'date')
    df = pd.DataFrame.from_records(qs)

    df = df.rename(columns={metric_field: 'metric'})

    df['date'] = pd.to_datetime(df['date'])
    dfg = df.groupby(pd.Grouper(key='date', freq='M')).metric.agg('sum')
    dfg = dfg.reset_index()
    dfg['date_formatted'] = dfg['date'].dt.strftime('%B %Y')

    t2 = go.Scatter(
        x=dfg.date_formatted,
        y=dfg.metric,
        name='Total da métrica',
        marker_color='#f5365c',
        mode='lines+markers',
    )

    # Now we can finally start plotting
    fig = plotly.tools.make_subplots(
        rows=2,
        cols=1,
        row_heights=[0.9,0.1],
        vertical_spacing=0.02,
        shared_xaxes=True
    )

    fig.update_xaxes(
        fixedrange=True,
        type='category',
        tickformat='%b/%Y',
    )
    fig.update_yaxes(
        fixedrange=True,
        rangemode='tozero',
    )
    fig.update_layout(
        width=1200,
        height=750,
        hovermode='closest',
        hoverdistance=1000,
        margin={
            'l': 0,
            'r': 0,
            'b': 0,
            't': 0,
        },
        hoverlabel=dict(
            namelength=-1,
        ),
        barmode='stack',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        dragmode=False,
    )
    for trace in traces_dimensions:
        fig.append_trace(trace, 1, 1)
    fig.append_trace(t2, 2, 1)
    fig.update_traces(xaxis='x2')

    plot_div = plotly.io.to_html(fig, include_plotlyjs='cdn', full_html=False)

    return plot_div
    

def raiox_mensal(date_min, date_max, metric_field, dimension, plot_type="sunburst"):
    """
    plot_type: "sunburst" or "treemap"
    """
    qs = ProposicaoAggregated.objects \
        .filter(date__gte=date_min, date__lte=date_max, **{metric_field+'__gt': 0}) \
        .annotate(metric_total=Sum(metric_field))
    
    if dimension == 'tema':
        qs = qs.values('proposicao__pk', 'proposicao__nome_processado', 'metric_total', 'proposicao__tema__nome')
    elif dimension == 'autor':
        qs = qs.values('proposicao__pk', 'proposicao__nome_processado', 'metric_total', 'proposicao__autor__nome_processado')
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
        path = ['proposicao__autor__nome_processado', 'proposicao__nome_processado']
        df['proposicao__autor__nome_processado'] = df['proposicao__autor__nome_processado'].fillna('Sem deputado autor')
    elif dimension == 'relator':
        path = ['proposicao__ultimo_status_relator__nome', 'proposicao__nome_processado']
        df['proposicao__ultimo_status_relator__nome'] = df['proposicao__ultimo_status_relator__nome'].fillna('Sem relator')
    elif dimension == 'situacao':
        path = ['proposicao__ultimo_status_situacao_descricao', 'proposicao__nome_processado']
        df['proposicao__ultimo_status_situacao_descricao'] = df['proposicao__ultimo_status_situacao_descricao'].replace(r'^\s*$', 'Sem situação', regex=True)
        df['proposicao__ultimo_status_situacao_descricao'] = df['proposicao__ultimo_status_situacao_descricao'].fillna('Sem situação')
    elif dimension == 'indexacao':
        path = ['proposicao__keywords', 'proposicao__nome_processado']

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
