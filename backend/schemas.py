from typing import List, Optional
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    role: str = Field(..., min_length=2, max_length=100)
    level: str = Field(..., min_length=2, max_length=50)
    question_count: int = Field(default=5, ge=1, le=10)
    focus_topic: Optional[str] = Field(default=None, max_length=400)


class AnswerSubmit(BaseModel):
    turn_id: int
    user_answer: str = Field(..., min_length=1, max_length=5000)


class TurnOut(BaseModel):
    id: int
    question_number: int
    topic_tag: str
    question_text: str
    user_answer: Optional[str] = None
    score: Optional[float] = None
    strengths: List[str] = []
    gaps: List[str] = []
    ideal_hint: Optional[str] = None
    follow_up: Optional[str] = None


class SessionDetailOut(BaseModel):
    id: int
    role: str
    level: str
    total_questions: int
    answered_count: int
    avg_score: float
    status: str
    turns: List[TurnOut]


class SessionSummaryOut(BaseModel):
    session_id: int
    role: str
    level: str
    status: str
    total_questions: int
    answered_count: int
    avg_score: float
    readiness_percent: int
    verdict: str
    strong_topics: List[str]
    weak_topics: List[str]
    action_plan: List[str]