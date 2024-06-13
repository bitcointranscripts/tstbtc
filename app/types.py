from typing import (
    Literal,
    TypedDict,
    Optional
)


GitHubMode = Literal["remote", "local", "none"]


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

# format required by
# https://github.com/pietrop/slate-transcript-editor


class DigitalPaperEditWord(TypedDict):
    id: int
    start: float
    end: float
    text: str


class DigitalPaperEditParagraph(TypedDict):
    id: int
    start: float
    end: float
    speaker: str
    # custom addition to the dpe format
    chapter: Optional[str]


class DigitalPaperEditFormat(TypedDict):
    words: list[DigitalPaperEditWord]
    paragraphs: list[DigitalPaperEditParagraph]
