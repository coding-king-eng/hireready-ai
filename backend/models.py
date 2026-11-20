from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from .database import Base


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(100), nullable=False)          # e.g., Backend Developer, DSA / SDE-1
    level = Column(String(50), nullable=False)          # e.g., Intern, Junior, Mid-Level
    total_questions = Column(Integer, default=5)
    avg_score = Column(Float, default=0.0)
    status = Column(String(30), default="in_progress")  # in_progress | completed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    turns = relationship("InterviewTurn", back_populates="session", cascade="all, delete-orphan")


class InterviewTurn(Base):
    __tablename__ = "interview_turns"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    question_number = Column(Integer, nullable=False)
    topic_tag = Column(String(80), nullable=False)
    question_text = Column(Text, nullable=False)
    user_answer = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    strengths_json = Column(Text, default="[]")
    gaps_json = Column(Text, default="[]")
    ideal_hint = Column(Text, nullable=True)

    session = relationship("InterviewSession", back_populates="turns")