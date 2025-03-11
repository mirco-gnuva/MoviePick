from typing import Iterable, Literal, Optional

import pandas as pd
import streamlit as st
from bson import ObjectId
from loguru import logger

from models import media_factory, Media, Vote
from moviepick.models import AbstractMedia
from moviepick.settings import PEOPLE
from settings import MongoSettings
from utils import get_mongo_db, get_mongo_collection, get_medias, vote_to_label

from moviepick.utils import render_sidebar


def label_to_vote(label: str) -> Literal[-1, 0, 1, None]:
    conversion_map = {'🔴': -1,
                      '🟡': 0,
                      '🟢': 1,
                      '⬤': None}

    return conversion_map[label]


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


def save_data(data: pd.DataFrame):
    logger.debug('Saving data...')
    db = get_mongo_db(connection_string=MongoSettings().CONNECTION_STRING, db_name=MongoSettings().DATABASE)
    collection = get_mongo_collection(db=db, collection_name=MongoSettings().BACKLOG_COLLECTION)

    changes = st.session_state.edited_data

    for idx, update in changes['edited_rows'].items():
        row = dict(data.iloc[idx])

        for field, value in update.items():
            row[field] = value

        row['_id'] = row.pop('id')

        db_raw_media = collection.find_one({'_id': ObjectId(row['_id'])})

        media = media_factory(db_raw_media)
        updated_media = media.copy(update=update)

        print(media)



        updated_votes = {user: label_to_vote(row[user]) for user in PEOPLE if user in update}
        db_votes = {vote.user: vote.value for vote in media.votes}

        for user, vote in updated_votes.items():
            db_votes[user] = vote

        updated_media.votes = [Vote(user=user, value=vote) for user, vote in db_votes.items()]

        print(updated_media)

        collection.update_one(filter={'_id': ObjectId(updated_media.id)},
                              update={'$set': updated_media.model_dump(exclude={'id'}, mode='json')})

    for new_raw_media in changes['added_rows']:
        media = media_factory(new_raw_media)
        collection.insert_one(media.model_dump(exclude={'id'}))


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

st.data_editor(num_rows='dynamic',
               column_config=columns_config,
               data=data,
               on_change=save_data,
               key='edited_data',
               args=(data,),
               hide_index=True,
               column_order=columns_config.keys())
