from typing import (
    TypedDict,
    Optional
)

from app.transcript import Transcript


class PostprocessOutput(TypedDict):
    transcript: Transcript
    markdown: Optional[str]
    json: Optional[str]
