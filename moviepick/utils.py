from pymongo import MongoClient
from pymongo.synchronous.collection import Collection
from pymongo.synchronous.database import Database


def get_mongo_db(connection_string: str, db_name: str) -> Database:
    client = MongoClient(connection_string)

    database = client.get_database(name=db_name)

    return database


def get_mongo_collection(db: Database, collection_name: str) -> Collection:
    collection = db[collection_name]

    return collection

