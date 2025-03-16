import time
import urllib.parse
from typing import Generator, Literal, Iterable, Any, Type, Optional

import pandas as pd
import requests
from bson import ObjectId
from loguru import logger
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.synchronous.collection import Collection
from pymongo.synchronous.database import Database
import streamlit as st

from models import Media, media_factory, AbstractMedia, Vote, TMDBSearchResult, TMDBMovie, TMDBShow
from settings import MongoSettings, PEOPLE, TMDBSettings


def get_mongo_db(connection_string: str, db_name: str) -> Database:
    client = MongoClient(connection_string)

    database = client.get_database(name=db_name)

    return database


def get_mongo_collection(db: Database, collection_name: str) -> Collection:
    collection = db[collection_name]

    return collection


def render_sidebar():
    with st.sidebar:
        st.page_link(page='voting.py', label='Vota')
        st.page_link(page='pages/backlog.py', label='Backlog')


def get_medias(media_type: Literal['movie', 'show']) -> Generator[Media, None, None]:
    db = get_mongo_db(connection_string=MongoSettings().CONNECTION_STRING, db_name=MongoSettings().DATABASE)
    collection = get_mongo_collection(db=db, collection_name=MongoSettings().BACKLOG_COLLECTION)

    raw_medias = collection.find({'type': media_type})

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


def get_medias_df(medias: Iterable[Media], filters: dict[str, str], reference_model: Type[BaseModel]) -> pd.DataFrame:
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

        columns = list(reference_model.model_fields.keys())
        columns.remove('votes')
        columns.remove('id')
        columns.extend(['missing_votes', 'votes_avg', 'enabled'])

        df = pd.DataFrame(columns=columns)
    else:
        df['missing_votes'] = df.apply(lambda r: not all(label_to_vote(r[user]) is not None for user in PEOPLE), axis=1)
        df['votes_avg'] = df.apply(lambda r: sum((label_to_vote(r[user]) for user in PEOPLE)) / len(PEOPLE)
        if not r['missing_votes'] else None, axis=1)
        df['enabled'] = df.apply(lambda r: not (r['missing_votes'] or r['viewed']), axis=1)

    for field, session_state_key in filters.items():
        filter_value = st.session_state[session_state_key]
        if isinstance(filter_value, Iterable):
            df = df[df[field].isin(filter_value)]
        else:
            df = df[df[field] == filter_value]

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


        updated_votes = {user: label_to_vote(row[user]) for user in PEOPLE if user in update}
        db_votes = {vote.user: vote.value for vote in media.votes}

        for user, vote in updated_votes.items():
            db_votes[user] = vote

        updated_media.votes = [Vote(user=user, value=vote) for user, vote in db_votes.items()]

        collection.update_one(filter={'_id': ObjectId(updated_media.id)},
                              update={'$set': updated_media.model_dump(exclude={'id'}, mode='json')})

    for new_raw_media in changes['added_rows']:
        media = media_factory(new_raw_media)
        collection.insert_one(media.model_dump(exclude={'id'}))


def search_media_paged(query: str, page: int, type: Literal['movie', 'tv']) -> TMDBSearchResult:
    assert page >= 1
    url = f"https://api.themoviedb.org/3/search/{type}?query={urllib.parse.quote_plus(query)}&include_adult=false&language=it-IT&page={page}"

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {TMDBSettings().TOKEN}"}

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    search_result = TMDBSearchResult(**response.json())

    return search_result


def search_media(query: str, type: Literal['movie', 'tv']) -> list[TMDBMovie | TMDBShow]:
    result = search_media_paged(query=query, page=1, type=type)
    medias = result.results

    for page in range(2, result.total_pages + 1):
        page_result = search_media_paged(query=query, page=1, type=type)
        medias.extend(page_result.results)

        time.sleep(0.1)

    return medias


def search_movie(query: str) -> list[TMDBMovie]:
    return search_media(query=query, type='movie')


def search_show(query: str) -> list[TMDBShow]:
    return search_media(query=query, type='tv')
