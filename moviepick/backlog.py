from typing import Generator, Iterable, Literal

import pandas as pd
import streamlit as st

from models import media_factory, Media, Vote
from settings import MongoSettings
from utils import get_mongo_db, get_mongo_collection


def get_medias() -> Generator[Media, None, None]:
    db = get_mongo_db(connection_string=MongoSettings().CONNECTION_STRING, db_name=MongoSettings().DATABASE)
    collection = get_mongo_collection(db=db, collection_name=MongoSettings().BACKLOG_COLLECTION)

    raw_medias = collection.find()

    medias = (media_factory(raw_media=r_m) for r_m in raw_medias)

    yield from medias


def vote_to_label(value: int | None) -> str:
    conversion_map = {-1: '🔴',
                      0: '🟡',
                      1: '🟢',
                      None: '⬤'}

    return conversion_map[value]


def label_to_vote(label: str) -> Literal[-1, 0, 1, None]:
    conversion_map = {'🔴': -1,
                      '🟡': 0,
                      '🟢': 1,
                      '⬤': None}

    return conversion_map[label]


def get_medias_df(medias: Iterable[Media]) -> pd.DataFrame:
    serialized = []

    for media in medias:
        result = media.model_dump()

        for vote in media.votes:
            result[vote.user] = vote_to_label(vote.value)
        del result['votes']
        print(result)

        serialized.append(result)

    df = pd.DataFrame(serialized)

    if len(df) == 0:
        columns = ['name', 'type', 'viewed'] + PEOPLE

        df = pd.DataFrame(columns=columns)

    return df


def save_data(data: pd.DataFrame):
    changes = st.session_state.edited_data

    for idx, update in changes['edited_rows'].items():
        row = data.iloc[idx]

        for field, value in update.items():
            row[field] = value

        data.iloc[idx] = row

    db = get_mongo_db(connection_string=MongoSettings().CONNECTION_STRING, db_name=MongoSettings().DATABASE)
    collection = get_mongo_collection(db=db, collection_name=MongoSettings().BACKLOG_COLLECTION)


    for _, row in data.iterrows():
        print(row)
        votes = [Vote(user=user, value=label_to_vote(row[user])) for user in PEOPLE]
        row['votes'] = votes

        media = media_factory(dict(row))
        if not media.id:
            collection.insert_one(media.model_dump())
        else:
            collection.update_one(filter={'_id': media.id}, update={'$set': media.model_dump()}, upsert=True)


PEOPLE = ['eiryuu', 'jac', 'plue', 'wasp']

st.title('Backlog')

medias = get_medias()
data = get_medias_df(medias=medias)

if 'test' not in st.session_state:
    st.session_state['test'] = data

name_column = st.column_config.TextColumn(required=True,
                                          validate='\w+',
                                          label='Titolo')
episode_column = st.column_config.TextColumn(label='Episodio/Stagione')
index_column = st.column_config.NumberColumn(label='Index',
                                             required=True,
                                             min_value=1,
                                             step=1,
                                             default=1)
notes_column = st.column_config.TextColumn(label='Note')
reporter_column = st.column_config.SelectboxColumn(required=True,
                                                   options=PEOPLE,
                                                   label='Proposto da')
viewed_column = st.column_config.CheckboxColumn(required=True,
                                                default=False)
vote_column = st.column_config.SelectboxColumn(required=True,
                                               options=['🟢', '🟡', '🔴', '⬤'],
                                               default='⬤')

st.data_editor(num_rows='dynamic',
               column_config={'name': name_column,
                              'vote': vote_column},
               data=data,
               on_change=save_data,
               key='edited_data',
               args=(data,))
