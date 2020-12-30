from django.conf import settings
from django.db.models import Count, Sum

import pandas as pd 
import plotly
import plotly.express as px
import plotly.graph_objs as go
from plotly.graph_objs import Layout

import datetime

from .models import *


def summary_plot(group_by, height, proposicao=None, initial_date=None, final_date=None, subplots='all', show_legend=False):
    """
    group_by: 'day', 'month' or 'year'
    proposicao: Proposicao object or None
    initial_date and final_date: if both are set, plot will be restricted to showing that period's data
    subplots: 'all' for all available subplots, or list with one or more of: ('ficha', 'enquete', 'noticia', 'prisma')
    """
    if not proposicao:
        qs1 = ProposicaoAggregated.objects.values('date') \
            .annotate(
                ficha_pageviews_total=Sum('ficha_pageviews'),
                poll_votes_total=Sum('poll_votes'),
                poll_comments_unchecked_total=Sum('poll_comments_unchecked'),
                poll_comments_authorized_total=Sum('poll_comments_authorized')
            )
        qs2 = NoticiaAggregated.objects.values('date') \
            .annotate(
                noticia_pageviews_total=Sum('pageviews'),
                portal_comments_authorized_total=Sum('portal_comments_authorized'),
                portal_comments_unchecked_total=Sum('portal_comments_unchecked')
            )
        qs3 = DailySummary.objects.values('date') \
            .annotate(
                atendimentos_total=Sum('atendimentos'),
            )
        df = pd.DataFrame(qs1).merge(pd.DataFrame(qs2), how='outer').merge(pd.DataFrame(qs3), how='outer')
    else:
        # Grouping is strictly speaking not necessary here. But we do it this way for consistency.
        qs = ProposicaoAggregated.objects.filter(proposicao=proposicao).values('date') \
            .annotate(
                ficha_pageviews_total=Sum('ficha_pageviews'),
                poll_votes_total=Sum('poll_votes'),
                poll_comments_unchecked_total=Sum('poll_comments_unchecked'),
                poll_comments_authorized_total=Sum('poll_comments_authorized'),
                noticia_pageviews_total=Sum('noticia_pageviews')
            )
        df = pd.DataFrame(qs)

    df['date'] = pd.to_datetime(df['date'])

    # Group data when showing by year or month
    freq = None
    if group_by == 'year':
        freq = 'Y'
    elif group_by == 'month':
        freq = 'M'

    if freq:
        df = df.groupby(pd.Grouper(key='date', freq=freq)) \
            .agg({
                'ficha_pageviews_total': 'sum',
                'poll_votes_total': 'sum',
                'poll_comments_unchecked_total': 'sum',
                'poll_comments_authorized_total': 'sum',
                'portal_comments_unchecked_total': 'sum',
                'portal_comments_authorized_total': 'sum',
                'atendimentos_total': 'sum',
                'noticia_pageviews_total': 'sum'
            }) \
            .reset_index()
    
    # Set api_params (this can be moved to the client-side in the future)
    if group_by == 'year':
        df['api_params'] = df.apply(lambda x:
            'initial_date={}&final_date={}'.format(
                x['date'].replace(day=1).replace(month=1).strftime(settings.STRFTIME_SHORT_DATE_FORMAT),
                x['date'].strftime(settings.STRFTIME_SHORT_DATE_FORMAT)
            ),
            axis=1)

        df['date'] = df['date'].dt.strftime('%Y')
    elif group_by == 'month':
        df['api_params'] = df.apply(lambda x:
            'initial_date={}&final_date={}'.format(
                x['date'].replace(day=1).strftime(settings.STRFTIME_SHORT_DATE_FORMAT),
                x['date'].strftime(settings.STRFTIME_SHORT_DATE_FORMAT)
            ),
            axis=1)

        df['date'] = df['date'].dt.strftime('%B %Y')
    elif group_by == 'day':
        df['api_params'] = df.apply(lambda x:
            'date={}'.format(
                x['date'].strftime(settings.STRFTIME_SHORT_DATE_FORMAT)
            ),
            axis=1)

    subplots_list = []
    if subplots == 'all' or 'ficha' in subplots:
        ficha_pageviews_trace = go.Scatter(
            x=df.date,
            y=df.ficha_pageviews_total,
            customdata=df.api_params,
            name='Visualizações (fichas de tramitação)',
            fill='tozeroy',
            )
        subplots_list.append({
            'traces': [ficha_pageviews_trace],
            'title': 'Visualizações (fichas de tramitação)',
        })
    if subplots == 'all' or 'enquete' in subplots:
        poll_votes_trace = go.Scatter(
            x=df.date,
            y=df.poll_votes_total,
            customdata=df.api_params,
            name='Votos nas enquetes',
            fill='tozeroy',
            )
        poll_comments_authorized_trace = go.Scatter(
            x=df.date,
            y=df.poll_comments_authorized_total,
            customdata=df.api_params,
            name='Comentários aprovados nas enquetes',
            fill='tozeroy',
            )
        poll_comments_unchecked_trace = go.Scatter(
            x=df.date,
            y=df.poll_comments_unchecked_total,
            customdata=df.api_params,
            name='Comentários não moderados nas enquetes',
            fill='tozeroy',
            )
        subplots_list.append({
            'traces': [poll_votes_trace, poll_comments_authorized_trace, poll_comments_unchecked_trace],
            'title': 'Votos e comentários nas enquetes',
        })
    if subplots == 'all' or 'noticia' in subplots:
        noticia_pageviews_trace = go.Scatter(
            x=df.date,
            y=df.noticia_pageviews_total,
            customdata=df.api_params,
            name='Visualizações (notícias)',
            fill='tozeroy',
            )
        if not proposicao:
            portal_comments_authorized_trace = go.Scatter(
                x=df.date,
                y=df.portal_comments_authorized_total,
                customdata=df.api_params,
                name='Comentários aprovados nas notícias',
                fill='tozeroy',
                )
            portal_comments_unchecked_trace = go.Scatter(
                x=df.date,
                y=df.portal_comments_unchecked_total,
                customdata=df.api_params,
                name='Comentários não moderados nas notícias',
                fill='tozeroy',
                )
            subplots_list.append({
                'traces': [noticia_pageviews_trace, portal_comments_authorized_trace, portal_comments_unchecked_trace],
                'title': 'Notícias',
            })
        else:
            subplots_list.append({
                'traces': [noticia_pageviews_trace],
                'title': 'Notícias',
            })
    if subplots == 'all' or 'prisma' in subplots:
        atendimentos_trace = go.Scatter(
            x=df.date,
            y=df.atendimentos_total,
            customdata=df.api_params,
            name='Atendimentos no Prisma',
            fill='tozeroy',
            )
        subplots_list.append({
            'traces': [atendimentos_trace],
            'title': 'Atendimentos no Prisma',
        })


    fig = plotly.tools.make_subplots(
        rows=len(subplots_list),
        cols=1,
        shared_xaxes=True,
        subplot_titles=list(map(lambda x: x['title'], subplots_list)),
        x_title='Data',
        vertical_spacing=0.08
    )
    i = 0
    for subplot in subplots_list:
        i += 1
        for trace in subplot['traces']:
            fig.append_trace(trace, i, 1)
    fig.update_traces(xaxis='x{}'.format(i))

    if initial_date and final_date:
        range_param = [initial_date, final_date]
    else:
        range_param = [datetime.date.today() - datetime.timedelta(days=180), datetime.date.today()]

    fig.update_xaxes(
        range=range_param,
        showspikes=True,
        spikethickness=2,
        spikedash="dot",
        spikecolor="#999999",
        spikemode="across+marker",
        spikesnap="data",
        type='category' if group_by in ('month', 'year') else 'date',
        tickformat='%d/%m/%Y',
    )
    fig.update_yaxes(
        gridcolor='#fff',
        fixedrange=True,
        rangemode='tozero',
        hoverformat=',d'
    )
    fig.update_layout(
        dragmode='pan',
        hovermode='x unified',
        hoverdistance=1000,
        spikedistance=-1,
        margin={
            'l': 50,
            'r': 50,
            'b': 50,
            't': 50,
        },
        height=height,
        hoverlabel=dict(
            namelength=-1,
        ),
        barmode='stack',
        showlegend=show_legend
    )

    # config={'displayModeBar': False}, 
    plot_json = plotly.io.to_json(fig)
    
    return plot_json

def poll_votes(proposicao):
    """
    proposicao: Proposicao object
    """
    qs = EnqueteItemResposta.objects.filter(ide_resposta__ide_formulario_publicado__proposicao=proposicao).values('num_indice_opcao')

    df = pd.DataFrame(qs)

    if df.empty:
        return (' ')

    df = df['num_indice_opcao'].value_counts().reset_index().sort_values('index')
    df = df.rename(columns={'index': 'num_indice_opcao', 'num_indice_opcao': 'votes_count'})
    df['votes_count_normalized'] = df['votes_count'] / df['votes_count'].sum()
    df.set_index('num_indice_opcao', inplace=True)

    poll_choices = [
        (0, 'Discordo totalmente', px.colors.sequential.Reds[7]),
        (1, 'Discordo na maior parte', px.colors.sequential.Reds[4]),
        (2, 'Estou indeciso', px.colors.sequential.Blues[4]),
        (3, 'Concordo na maior parte', px.colors.sequential.Greens[4]),
        (4, 'Concordo totalmente', px.colors.sequential.Greens[7])
    ]
    fig = go.Figure()
    for i, label, color in poll_choices:
        try:
            votes_count = df.loc[i, 'votes_count']
        except KeyError:
            votes_count = 0
        fig.add_trace(
            go.Bar(
                x=[votes_count],
                name=label,
                marker_color=color,
                orientation='h',
                text=[votes_count]
            )
        )
    fig.update_traces(
        texttemplate='%{text:,d}',
        textposition='auto'
    )
    fig.update_xaxes(
        showticklabels=False,
        hoverformat=',d',
    )
    fig.update_yaxes(
        showticklabels=False
    )
    fig.update_layout(
        barmode='stack',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode=None,
        margin={
            'l': 0,
            'r': 0,
            'b': 0,
            't': 0,
        },
    )
    plot_div = plotly.io.to_html(fig, include_plotlyjs='cdn', config={'displayModeBar': False}, full_html=False)
    
    return plot_div

def prisma_sexo(initial_date, final_date):
    df = PrismaDemanda.objects.get_sexo_counts(initial_date, final_date)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df['sexo'],
            y=df['count']
        )
    )

    plot_json = plotly.io.to_json(fig)
    return plot_json

def prisma_idade(initial_date, final_date):
    df = PrismaDemanda.objects.get_idade_counts(initial_date, final_date)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df['idade'],
            y=df['count']
        )
    )

    plot_json = plotly.io.to_json(fig)
    return plot_json

def proposicao_heatmap(proposicao):
    """
    NOT FULLY IMPLEMENTED
    """
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
    """
    year: int
    metric_field: any metric field in ProposicaoAggregated
    dimension: 'tema', 'autor', 'relator', 'situacao', 'indexacao' or 'proposicao'
    """

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
    date_min: date
    date_max: date
    metric_field: any metric field in ProposicaoAggregated
    dimension: 'tema', 'autor', 'relator', 'situacao', 'indexacao' or 'proposicao'
    plot_type: 'sunburst' or 'treemap'
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
