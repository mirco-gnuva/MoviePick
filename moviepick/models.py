from datetime import date
from typing import Optional, Literal, Annotated, Union, Any

from bson import ObjectId
from pydantic import BaseModel, Field, model_serializer, parse_obj_as, AfterValidator, PlainSerializer, WithJsonSchema, \
    PositiveFloat, field_validator
from pydantic import TypeAdapter, PositiveInt
from pydantic_extra_types.language_code import LanguageAlpha2

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
    type: Literal['']
    notes: Optional[str] = None
    reporter: Literal[*PEOPLE]
    scheduled_on: Optional[date] = None
    viewed_on: Optional[date] = None
    subtype: Literal['']

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
    saga: str
    subtype: Literal['Film', 'Film anime']



class Show(AbstractMedia):
    type: Literal['show'] = 'show'
    season: Season
    subtype: Literal['Serie', 'Serie anime']


Media = Annotated[Union[Movie, Show], Field(discriminator='type')]



def media_factory(raw_media: dict) -> Media:
    media = TypeAdapter(Media).validate_python(raw_media)

    return media


class TMDBMedia(BaseModel):
    adult: bool
    backdrop_path: Optional[str]
    genre_ids: list[int]
    id: int
    original_language: LanguageAlpha2
    overview: str
    popularity: PositiveFloat
    poster_path: Optional[str]
    vote_average: float = Field(ge=0.0)
    vote_count: int = Field(ge=0)


class TMDBMovie(TMDBMedia):
    original_name: str = Field(validation_alias='original_title')
    release_date: Optional[date]
    name: str = Field(validation_alias='title')
    video: bool

    @field_validator('release_date', mode='before')
    @classmethod
    def validate_release_date(cls, v: str):
        if len(v) == 0:
            return None

        return v


class TMDBShow(TMDBMedia):
    origin_country: list[str]
    original_name: str
    first_air_date: date
    name: str


class TMDBSearchResult(BaseModel):
    page: int = Field(ge=0)
    results: list[Union[TMDBMovie | TMDBShow]]
    total_pages: int = Field(ge=1)
    total_results: PositiveInt

    # @field_validator('results', mode='before')
    # @classmethod
    # def validate results
