from typing import Iterable, Optional

import pandas as pd
import streamlit as st

from models import Media
from moviepick.models import AbstractMedia
from moviepick.settings import PEOPLE
from utils import get_medias, vote_to_label, label_to_vote, save_data, search_movie, \
    search_show

from moviepick.utils import render_sidebar


def get_medias_df(medias: Iterable[Media], types_filter: Optional[list[str]], viewed_filter: Optional[bool],
                  missing_votes_filter: Optional[bool]) -> pd.DataFrame:
    serialized = []

    for media in medias:
        result = media.model_dump()

        for vote in media.votes:
            result[vote.user] = vote_to_label(vote.value)
        for user in [u for u in PEOPLE if u not in result]:
            result[user] = vote_to_label(None)
        del result['votes']

        serialized.append(result)

    df = pd.DataFrame(serialized)

    if len(df) == 0:
        columns = list(AbstractMedia.model_fields.keys())
        columns.remove('votes')
        columns.remove('id')
        columns.extend(['missing_votes', 'votes_avg', 'enabled'])

        df = pd.DataFrame(columns=columns)
    else:
        df['missing_votes'] = df.apply(lambda r: not all(label_to_vote(r[user]) is not None for user in PEOPLE), axis=1)
        df['votes_avg'] = df.apply(lambda r: sum((label_to_vote(r[user]) for user in PEOPLE)) / len(PEOPLE)
        if not r['missing_votes'] else None, axis=1)
        df['enabled'] = df.apply(lambda r: not (r['missing_votes'] or r['viewed']), axis=1)

    if types_filter:
        df = df[df['type'].isin(types_filter)]
    if viewed_filter is not None:
        df = df[df['viewed'] == viewed_filter]
    if missing_votes_filter is not None:
        df = df[df['missing_votes'] == missing_votes_filter]

    return df


st.set_page_config(layout='wide')
render_sidebar()
st.title('Backlog')

col1, col2, col3 = st.columns(3)

with col1:
    type_filter = st.pills(label='Type', options=['movie', 'show'], selection_mode="multi")
with col2:
    viewed_filter = st.select_slider(label='Viewed', options=[False, None, True])
with col3:
    missing_votes_filter = st.select_slider(label='Missing votes', options=[False, None, True])

medias = get_medias()
data = get_medias_df(medias=medias, types_filter=type_filter, viewed_filter=viewed_filter,
                     missing_votes_filter=missing_votes_filter)

name_column = st.column_config.TextColumn(required=True,
                                          validate='\\w+',
                                          label='Titolo')

episode = st.column_config.TextColumn(label='Episodio/Stagione')

episode_index = st.column_config.NumberColumn(label='Index',
                                              min_value=0,
                                              step=1,
                                              default=1)

notes = st.column_config.TextColumn(label='Note')

reporter_column = st.column_config.SelectboxColumn(required=True,
                                                   options=PEOPLE,
                                                   label='Proposto da')
viewed_column = st.column_config.CheckboxColumn(required=True,
                                                default=False,
                                                label='Visto')
vote_column = st.column_config.SelectboxColumn(required=True,
                                               options=['🟢', '🟡', '🔴', '⬤'],
                                               default='⬤')

schedule_column = st.column_config.DateColumn(label='Pianificato il')

viewed_on_column = st.column_config.DateColumn(label='Visto il')

type_column = st.column_config.SelectboxColumn(required=True,
                                               options=['movie', 'show'],
                                               label='Tipo',
                                               default='movie')
votes_avg_column = st.column_config.NumberColumn(disabled=True,
                                                 label='Media voti')
enabled_column = st.column_config.CheckboxColumn(disabled=True,
                                                 label='Votabile')

columns_config = {'name': name_column,
                  'vote': vote_column,
                  'episode_label': episode,
                  'episode_order': episode_index,
                  'notes': notes,
                  'reporter': reporter_column,
                  'viewed': viewed_column,
                  'scheduled_on': schedule_column,
                  'viewed_on': viewed_on_column,
                  'type': type_column,
                  'votes_avg': votes_avg_column,
                  'enabled': enabled_column,
                  } | {user: vote_column for user in PEOPLE}

col_1, col_2 = st.columns(2)

with col_1:
    st.data_editor(num_rows='static',
                   column_config=columns_config,
                   data=data,
                   on_change=save_data,
                   key='edited_data',
                   args=(data,),
                   hide_index=True,
                   column_order=columns_config.keys())
with col_2:
    col_2_1, col_2_2, col_2_3 = st.columns(3)

    with col_2_1:
        query = st.text_input('Cerca')
        media_type = st.radio(label='Tipo', options=['Film', 'Serie'], horizontal=True)
    with col_2_2:
        if st.button('Search'):
            if media_type == 'Film':
                st.session_state['matching_medias'] = search_movie(query=query)
            elif media_type == 'Serie':
                st.session_state['matching_medias'] = search_show(query=query)
            else:
                raise ValueError('Media type not supported')

            with col_2_3:
                st.session_state['selected_media'] = st.selectbox(label='Scegli un risultato se lo desideri',
                                                                  options=[m.name for m in
                                                                           st.session_state['matching_medias']],
                                                                  )
        with col_2_3:
            if st.button('Reset'):
                st.session_state['selected_media_obj'] = None
                if 'matching_medias' in st.session_state:
                    del st.session_state['matching_medias']
                if 'selected_media' in st.session_state:
                    del st.session_state['selected_media']

    with st.form('add_media'):
        col_1, col_2, col_3 = st.columns(3)

        with col_1:
            try:
                st.session_state['selected_media_obj'] = None

                if 'matching_medias' in st.session_state and 'selected_media' in st.session_state:
                    st.session_state['selected_media_obj'] = next(
                        (media for media in st.session_state['matching_medias']
                         if media.name == st.session_state['selected_media']), None)

                name = st.text_input(label='Titolo',
                                     value=st.session_state['selected_media_obj'].name
                                     if st.session_state['selected_media_obj'] else '')
                poster_link = st.text_input(label='Link copertina custom')

                if poster_link or st.session_state['selected_media_obj']:
                    st.image(
                        poster_link or f'http://image.tmdb.org/t/p/w500{st.session_state['selected_media_obj'].poster_path}')
            except NameError:
                pass
        st.form_submit_button()
