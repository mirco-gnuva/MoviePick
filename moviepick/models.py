from datetime import date
from typing import Optional, Literal, Annotated, Union, Any

from bson import ObjectId
from pydantic import BaseModel, Field, model_serializer, parse_obj_as, AfterValidator, PlainSerializer, WithJsonSchema
from pydantic import TypeAdapter

from moviepick.settings import PEOPLE


class Vote(BaseModel):
    user: str
    value: Literal[-1, 0, 1, None] = None


def validate_object_id(v: Any) -> str:
    if isinstance(v, ObjectId):
        return str(v)
    if ObjectId.is_valid(v):
        return str(v)
    raise ValueError("Invalid ObjectId")


PyObjectId = Annotated[
    Union[str, ObjectId],
    AfterValidator(validate_object_id),
    PlainSerializer(lambda x: str(x), return_type=str),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]


class AbstractMedia(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias='_id')
    name: str
    viewed: Optional[bool] = False
    votes: Optional[list[Vote]] = Field(default_factory=tuple)
    type: Literal['media']
    notes: Optional[str] = None
    reporter: Literal[*PEOPLE]
    scheduled_on: Optional[date] = None
    viewed_on: Optional[date] = None

    class Config:
        arbitrary_types_allowed = True


class Season(BaseModel):
    order: int = Field(ge=0)
    label: Optional[str] = None


class Episode(Season):
    pass


class Movie(AbstractMedia):
    type: Literal['movie'] = 'movie'
    episode: Optional[Episode] = Field(default=None)


class Show(AbstractMedia):
    type: Literal['show'] = 'show'
    season: Season


Media = Annotated[Union[Movie, Show], Field(discriminator='type')]


class MediaParser(BaseModel):
    media: Media | dict


def media_factory(raw_media: dict) -> Media:
    media = TypeAdapter(Media).validate_python(raw_media)

    return media
