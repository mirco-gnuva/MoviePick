from typing import Generator

from pymongo import MongoClient
from pymongo.synchronous.collection import Collection
from pymongo.synchronous.database import Database
import streamlit as st

from models import Media, media_factory
from settings import MongoSettings


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
