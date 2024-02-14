from typing import (
    Literal,
    TypedDict,
    Optional
)

from app.transcript import Transcript

GitHubMode = Literal["remote", "local", "none"]

class PostprocessOutput(TypedDict):
    transcript: Transcript
    markdown: Optional[str]
    json: Optional[str]

class Word(TypedDict):
    word: str
    start: float
    end: float
    confidence: float
    speaker: int
    speaker_confidence: float
    punctuated_word: str

class SpeakerSegment(TypedDict):
    speaker: int
    transcript: str
    start: float
    end: float
    words: list[Word]

class Sentence(TypedDict):
    transcript: str
    start: float
    end: float
    words: list[Word]

class SpeakerSegmentWithSentences(TypedDict):
    speaker: int
    transcript: str
    start: float
    end: float
    sentences: list[Sentence]
