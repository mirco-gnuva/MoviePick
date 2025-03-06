from typing import Optional, Literal, Annotated, Union

from pydantic import BaseModel, Field, model_serializer


class Vote(BaseModel):
    user: str
    value: Literal[-1, 0, 1, None] = None


class AbstractMedia(BaseModel):
    id: Optional[int] = Field(default=None, alias='_id', exclude=True)
    name: str
    viewed: Optional[bool] = False
    votes: Optional[list[Vote]] = Field(default_factory=tuple)
    type: Literal['media']


class Movie(AbstractMedia):
    type: Literal['movie'] = 'movie'


class Season(BaseModel):
    order: int = Field(ge=0)
    label: Optional[str] = None


class Show(AbstractMedia):
    type: Literal['show'] = 'show'
    season: Season


Media = Annotated[Union[Movie, Show], Field(discriminator='type')]


class MediaParser(BaseModel):
    media: Media | dict


def media_factory(raw_media: dict) -> Media:
    media = MediaParser(media=raw_media).media

    return media
