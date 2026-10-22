"""What the model answers, as structured output."""

from pydantic import BaseModel, Field


class FileClassification(BaseModel):
    """Whether a JSON file is a locale document of user-interface messages."""

    qualifies: bool = Field(
        description="true if the file holds user-facing messages that should be translated"
    )
    reason: str = Field(description="one short sentence saying why")
    subject: str = Field(
        description="what part of the website the messages are for, in a few words"
    )


class Translation(BaseModel):
    id: str = Field(description="the id of the message, exactly as given")
    text: str = Field(description="the translated message")


class TranslationBatch(BaseModel):
    """The translations of the messages given, one for each id."""

    translations: list[Translation]
