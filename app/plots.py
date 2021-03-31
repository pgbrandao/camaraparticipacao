from django.conf import settings
from django.db.models import Count, Sum

import pandas as pd 
import plotly
import plotly.express as px
import plotly.graph_objs as go
from plotly.graph_objs import Layout

import datetime

from .models import *
from . import helpers


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

    # if initial_date and final_date:
    # df = df[(df['date'] >= pd.to_datetime(initial_date)) & (df['date'] <= pd.to_datetime(final_date))]

    df.sort_values('date', inplace=True)
    
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
        df['api_params'] = df.apply(lambda x: helpers.get_api_params(
                x['date'].replace(day=1).replace(month=1),
                x['date']
        ), axis=1)

        df['date'] = df['date'].dt.strftime('%Y')
    elif group_by == 'month':
        df['api_params'] = df.apply(lambda x: helpers.get_api_params(
                x['date'].replace(day=1),
                x['date']
        ), axis=1)

        df['date'] = df['date'].dt.strftime('%B %Y')
    elif group_by == 'day':
        df['api_params'] = df.apply(lambda x: helpers.get_api_params(
                x['date'],
                x['date']
        ), axis=1)


    subplots_list = []
    if subplots == 'all' or 'ficha' in subplots:
        ficha_pageviews_trace = go.Scatter(
            x=df.date,
            y=df.ficha_pageviews_total,
            customdata=df.api_params,
            name='Visualizações das fichas de tramitação',
            fill='tozeroy',
            )
        subplots_list.append({
            'traces': [ficha_pageviews_trace],
            'title': 'Visualizações das fichas de tramitação',
        })
    if subplots == 'all' or 'enquete' in subplots:
        poll_votes_trace = go.Scatter(
            x=df.date,
            y=df.poll_votes_total,
            customdata=df.api_params,
            name='Votos nas enquetes',
            fill='tozeroy',
            )
        subplots_list.append({
            'traces': [poll_votes_trace],
            'title': 'Votos nas enquetes',
        })
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
            'traces': [poll_comments_authorized_trace, poll_comments_unchecked_trace],
            'title': 'Comentários nas enquetes',
        })
    if subplots == 'all' or 'noticia' in subplots:
        noticia_pageviews_trace = go.Scatter(
            x=df.date,
            y=df.noticia_pageviews_total,
            customdata=df.api_params,
            name='Visualizações das notícias',
            fill='tozeroy',
            )
        subplots_list.append({
            'traces': [noticia_pageviews_trace],
            'title': 'Visualizações das notícias',
        })
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
                'traces': [portal_comments_authorized_trace, portal_comments_unchecked_trace],
                'title': 'Comentários nas notícias',
            })
    if (subplots == 'all' or 'prisma' in subplots) and not proposicao:
        atendimentos_trace = go.Scatter(
            x=df.date,
            y=df.atendimentos_total,
            customdata=df.api_params,
            name='Atendimentos',
            fill='tozeroy',
            )
        subplots_list.append({
            'traces': [atendimentos_trace],
            'title': 'Atendimentos',
        })


    fig = plotly.subplots.make_subplots(
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
        dragmode=False if initial_date and final_date else 'pan',
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
        return None

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

    if df is None:
        return None

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name='Masculino',
            x=[df[df['sexo'] == 'Masculino'].iloc[0,1]],
            y=[''],
            orientation='h'
        )
    )
    fig.add_trace(
        go.Bar(
            name='Feminino',
            x=[df[df['sexo'] == 'Feminino'].iloc[0,1]],
            y=[''],
            orientation='h'
        )
    )
    fig.update_traces(
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
    plot_json = plotly.io.to_json(fig)
    return plot_json


def prisma_sexo_idade(initial_date, final_date):
    df = PrismaDemanda.objects.get_sexo_idade_counts(initial_date, final_date)

    if df is None:
        return None

    fig = go.Figure(data=[
        go.Bar(
            x=df['idade_demanda'],
            y=df.get('Masculino', []),
            name='Masculino'
        ),
        go.Bar(
            x=df['idade_demanda'],
            y=df.get('Feminino', []),
            name='Feminino'
        )
    ])

    fig.update_layout(
        barmode='stack',
        xaxis_title='Idade',
        yaxis_title='Número de demandantes',
        hovermode="x unified",
        title=False
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

def enquetes_temas(initial_date, final_date):
    metric_field = 'poll_votes'
    dimension_field = 'proposicao__tema__nome'

    # First step: prepare df_dimension
    df_dimension = ProposicaoAggregated.objects.get_metric_date_dimension_df(initial_date, final_date, metric_field, dimension_field)

    # Second step: prepare df_sum
    df_sum = ProposicaoAggregated.objects.get_metric_date_df(initial_date, final_date, metric_field)

    if df_dimension is not None and df_sum is not None:
        return raiox_anual_plot(initial_date, final_date, df_dimension, df_sum, dimension_field, metric_field, "Votos nas enquetes")
    else:
        return None

def proposicoes_temas(initial_date, final_date):
    metric_field = 'ficha_pageviews'
    dimension_field = 'proposicao__tema__nome'

    # First step: prepare df_dimension
    df_dimension = ProposicaoAggregated.objects.get_metric_date_dimension_df(initial_date, final_date, metric_field, dimension_field)

    # Second step: prepare df_sum
    df_sum = ProposicaoAggregated.objects.get_metric_date_df(initial_date, final_date, metric_field)

    if df_dimension is not None and df_sum is not None:
        return raiox_anual_plot(initial_date, final_date, df_dimension, df_sum, dimension_field, metric_field, "Visualizações das proposições")
    else:
        return None


def noticias_temas(initial_date, final_date):
    metric_field = 'pageviews'
    dimension_field = 'noticia__tema_principal__titulo'

    # First step: prepare df_dimension
    df_dimension = NoticiaAggregated.objects.get_metric_date_dimension_df(initial_date, final_date, metric_field, dimension_field)

    # Second step: prepare df_sum
    df_sum = NoticiaAggregated.objects.get_metric_date_df(initial_date, final_date, metric_field)

    if df_dimension is not None and df_sum is not None:
        return raiox_anual_plot(initial_date, final_date, df_dimension, df_sum, dimension_field, metric_field, "Visualizações das notícias")
    else:
        return None

def noticias_tags(initial_date, final_date):
    metric_field = 'pageviews'
    dimension_field = 'noticia__tags_conteudo__nome'

    # First step: prepare df_dimension
    df_dimension = NoticiaAggregated.objects.get_metric_date_dimension_df(initial_date, final_date, metric_field, dimension_field)

    # Second step: prepare df_sum
    df_sum = NoticiaAggregated.objects.get_metric_date_df(initial_date, final_date, metric_field)

    if df_dimension is not None and df_sum is not None:
        return raiox_anual_plot(initial_date, final_date, df_dimension, df_sum, dimension_field, metric_field, "Visualizações das notícias")
    else:
        return None

def raiox_anual_plot(initial_date, final_date, df_dimension, df_sum, dimension_field, metric_field, metric_label):
    """
    df_dimension: columns: ['date', 'date_formatted', dimension_field, metric_field]
    df_sum: columns: ['date', 'date_formatted', metric_field]
    """
    # Calculate normalized metrics
    metric_normalized_field = '{}_normalized'.format(metric_field)
    df_dimension[metric_normalized_field] = df_dimension.groupby('date')[metric_field].transform(lambda x: 100*x/x.sum())
    # df_dimension[metric_normalized_field] = df_dimension[metric_normalized_field].map('{:.2f} %'.format)


    # To calculate top dimensions, the metric is summed over the entire period and inversely sorted
    top_dimensions = df_dimension \
        .groupby(dimension_field)[metric_normalized_field] \
        .sum() \
        .reset_index() \
        .sort_values(metric_normalized_field, ascending=False) \
        .reset_index(drop=True)

    traces_dimensions = []
    dimension_colors = {}
    for i, row in top_dimensions.iterrows():
        dimension_value = row[dimension_field]
        most_important = i < len(px.colors.qualitative.T10) - 1

        if most_important:
            color = px.colors.qualitative.T10[i]
            dimension_colors[dimension_value] = color
        else:
            color = px.colors.qualitative.T10[-1]
            default_color = color

        df_this_dimension = df_dimension[df_dimension[dimension_field] == dimension_value]

        # Create missing dates
        for date in (set(pd.date_range(initial_date, final_date, freq='M')) - set(df_this_dimension['date'].to_list())):
            df_this_dimension = df_this_dimension \
                .append(
                    {
                        'date': date,
                        'date_formatted': date.strftime('%B %Y'),
                        dimension_field: dimension_value,
                        metric_field: 0,
                        metric_normalized_field: '0.00 %'
                    },
                    ignore_index=True
                ) \
                .sort_values(by='date') \
                .reset_index(drop=True)
        
        traces_dimensions.append(
            go.Bar(
                x=df_this_dimension['date_formatted'],
                y=df_this_dimension[metric_normalized_field],
                name=dimension_value,
                marker_color=color,
                showlegend=most_important,
            )
        )

    t2 = go.Bar(
        x=df_sum['date_formatted'],
        y=df_sum[metric_field],
        name=metric_label,
        marker_color='#f5365c',
    )

    # Now we can finally start plotting
    fig = plotly.subplots.make_subplots(
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
        legend=dict(
            orientation="v",
            xanchor="left",
            yanchor="top",
            x=1.01,
            y=1,
        ),
    )
    for trace in traces_dimensions:
        fig.append_trace(trace, 1, 1)
    fig.append_trace(t2, 2, 1)
    fig.update_traces(
        xaxis='x2',
        hovertemplate='%{y:,.2f} %',
    )

    # for date_formatted in df_sum['date_formatted']:

    plot_json = plotly.io.to_json(fig)

    return {
        'json': plot_json,
        'dimension_colors': dimension_colors,
        'default_color': default_color,
    }
    
