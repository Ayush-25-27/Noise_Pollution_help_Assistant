from typing import Literal, Optional

from pydantic import BaseModel, Field

ZoneType = Literal["residential", "silence", "commercial", "industrial"]
TimeOfDay = Literal["day", "night"]
DurationType = Literal["brief", "sustained"]


class ReportRequest(BaseModel):
    location: str = Field(..., examples=["Near Lotus Public School, Sector 12"])
    zone: ZoneType = Field(..., examples=["residential", "silence", "commercial", "industrial"])
    db: Optional[int] = Field(None, ge=0, le=200, description="If omitted, the noise fetch tool is used")
    time_of_day: Optional[TimeOfDay] = Field(None, examples=["day", "night"])
    duration: Optional[DurationType] = Field(None, examples=["brief", "sustained"])
    question: Optional[str] = Field(None, description="Optional follow-up question")


class ReadingSubmission(BaseModel):
    location: str = Field(..., examples=["Near Lotus Public School, Sector 12"])
    db: int = Field(..., ge=0, le=200, description="Measured decibel reading")
    time_of_day: TimeOfDay = Field(..., examples=["day", "night"])
    duration: DurationType = Field(..., examples=["brief", "sustained"])


class ReportResponse(BaseModel):
    location: str
    zone: str
    zone_label: str
    db: int
    time_of_day: str
    duration: str
    data_source: str
    limit: int
    exceeds: bool
    over_by: int
    source_guess: str
    regulation_passages: list[str]
    answer: str


class ChatRequest(BaseModel):
    message: str = Field(..., description="Free-text message from the user to Xaya")


class ChatResponse(BaseModel):
    reply: str
