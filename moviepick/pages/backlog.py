from typing import Any

import streamlit as st
from streamlit_server_state import server_state, server_state_lock

from models import Movie
from utils import render_sidebar, get_medias, get_medias_df

st.set_page_config(layout='wide')
render_sidebar()
st.title('Backlog')


def filters() -> dict[str, str]:
    col1, col2, col3 = st.columns(3)

    with col2:
        st.select_slider(label='Viewed', options=[False, None, True], key='viewed_filter')
    with col3:
        st.select_slider(label='Missing votes', options=[False, None, True], key='missing_votes_filter')

    return {'viewed': 'viewed_filter', 'missing_votes': 'missing_votes_filter'}

def movie_backlog():
    medias = get_medias(media_type='movie')

    data = get_medias_df(medias=medias, filters=filters_dict, reference_model=Movie)



_, center, _ = st.columns(3)

with center:
    st.segmented_control(options=['📽️ Film', '📺 Serie'], label='', key='media_type')

left, right = st.columns(2)

with left:
    filters_dict = filters()

    if st.session_state['media_type'] == '📽️ Film':



