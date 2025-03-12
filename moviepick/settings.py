from pydantic_settings import BaseSettings

class MongoSettings(BaseSettings):
    CONNECTION_STRING: str
    DATABASE: str
    BACKLOG_COLLECTION: str
    VOTE_ORDER_COLLECTION: str

class TMDBSettings(BaseSettings):
    TOKEN: str


PEOPLE = ['eiryuu', 'jac', 'plue', 'wasp']
