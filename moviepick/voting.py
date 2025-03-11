import random
from typing import Optional, Iterable

import numpy as np
import pandas as pd
import streamlit as st
from streamlit_server_state import server_state, server_state_lock

from models import Media, AbstractMedia
from utils import render_sidebar, get_medias, vote_to_label
from settings import PEOPLE


def get_medias_df(medias: Iterable[Media], types_filter: Optional[list[str]]) -> pd.DataFrame:
    serialized = []

    for media in medias:
        result = media.model_dump()

        for vote in media.votes:
            result[vote.user] = vote.value
        del result['votes']

        serialized.append(result)

    df = pd.DataFrame(serialized)

    if len(df) == 0:
        columns = list(AbstractMedia.model_fields.keys())
        columns.remove('votes')
        columns.remove('id')

        df = pd.DataFrame(columns=columns)

    for user in PEOPLE:
        df[user] = df[user].replace(np.nan, None)

    df['missing_votes'] = df.apply(lambda r: not all(r[user] is not None for user in PEOPLE), axis=1)
    df = df[~df['missing_votes']]

    df['enabled'] = df.apply(lambda r: not r['viewed'], axis=1)
    df = df[df['enabled']]

    print(~df['scheduled_on'].astype(bool))
    df = df[~df['scheduled_on'].astype(bool)]

    df['votes_avg'] = df.apply(lambda r: sum(r[user] for user in PEOPLE) / len(PEOPLE), axis=1)

    if types_filter:
        df = df[df['type'].isin(types_filter)]

    for user in PEOPLE:
        df[user] = df[user].apply(vote_to_label)

    df.sort_values(by=['votes_avg'], inplace=True, ascending=False)

    return df


st.set_page_config(layout='wide')
render_sidebar()
st.title('Vota')

col_1_1, col_1_2, col_1_3 = st.columns(3)
with col_1_1:
    type_filter = st.pills(label='Type', options=['movie', 'show'], selection_mode="multi")

if 'restricted_data' not in server_state:
    medias = get_medias()
    data = get_medias_df(medias=medias, types_filter=type_filter)
else:
    data = server_state['restricted_data']

col1, col2 = st.columns(2)
with col1:
    if 'test' not in st.session_state:
        st.session_state['test'] = data

    name_column = st.column_config.TextColumn(disabled=True,
                                              validate='\\w+',
                                              label='Titolo')

    episode = st.column_config.TextColumn(label='Episodio/Stagione', disabled=True)

    episode_index = st.column_config.NumberColumn(label='Index',
                                                  min_value=0,
                                                  step=1,
                                                  default=1,
                                                  disabled=True)

    notes = st.column_config.TextColumn(label='Note',
                                        disabled=True)

    type_column = st.column_config.SelectboxColumn(disabled=True,
                                                   options=['movie', 'show'],
                                                   label='Tipo',
                                                   default='movie')
    votes_avg_column = st.column_config.NumberColumn(disabled=True,
                                                     label='Media voti')

    columns_config = {'name': name_column,
                      'episode_label': episode,
                      'episode_order': episode_index,
                      'notes': notes,
                      'type': type_column,
                      'votes_avg': votes_avg_column}

    st.data_editor(num_rows='fixed',
                   column_config=columns_config,
                   data=data,
                   key='edited_data',
                   args=(data,),
                   hide_index=True,
                   column_order=columns_config.keys())

with col2:
    def update_votes(votes_df: pd.DataFrame):
        with server_state_lock['edited_votes']:
            changes = st.session_state.edited_votes['edited_rows']
            votes = votes_df['vote'].to_list()

            print(changes)
            for pos, data in changes.items():
                votes[pos] = data['vote']

            votes_df['vote'] = votes

            server_state['edited_votes'] = votes_df


    if 'edited_votes' in server_state:
        votes_df = server_state['edited_votes']
    else:
        votes_df = pd.DataFrame(data=[{'user': user, 'vote': data['name'].to_list()[0]} for user in PEOPLE])

    user_column = st.column_config.TextColumn(disabled=True,
                                              label='Utente')
    vote_column = st.column_config.SelectboxColumn(options=data['name'],
                                                   label='Voto', )

    columns_config = {'user': user_column,
                      'vote': vote_column}
    votes = st.data_editor(num_rows='fixed',
                           column_config=columns_config,
                           data=votes_df,
                           hide_index=True,
                           column_order=columns_config.keys(),
                           on_change=update_votes,
                           args=(votes_df,),
                           key='edited_votes')

    votes_per_media = votes['vote'].value_counts().to_dict()

    max_votes = max(votes_per_media.values())
    if len([c for c in votes_per_media.values() if c == max_votes]) > 1:
        def pick_media() -> str:
            top_medias = [media for media, votes in votes_per_media.items() if votes == max_votes]
            choice = random.choice(top_medias)

            return choice


        def restrict_medias():
            global data
            df = data.copy(deep=True)

            top_medias = [media for media, votes in votes_per_media.items() if votes == max_votes]

            df = df[df['name'].isin(top_medias)]

            with server_state_lock['restricted_data']:
                server_state['restricted_data'] = df


        col2_1, col2_2 = st.columns(2)

        with col2_1:
            if st.button('Estrai', on_click=pick_media):
                choice_component = st.markdown(f'**Scelta:** {pick_media()}')

        with col2_2:
            st.button('Rivota', on_click=restrict_medias)

    if st.button('Termina'):
        with server_state_lock['restricted_data']:
            del server_state['restricted_data']

        with server_state_lock['edited_votes']:
            del server_state['edited_votes']
    else:
        selected_media = next(name for name, votes in votes_per_media.items() if votes == max_votes)
        choice = st.markdown(f'**Scelta:** {selected_media}')
