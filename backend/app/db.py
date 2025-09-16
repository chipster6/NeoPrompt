"""SQLAlchemy models and database initialization."""
import os
import json
from datetime import datetime, UTC
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, Column, String, DateTime, Float, Text, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON


# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./console.sqlite")
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Decision(Base):
    """Stores prompt engineering decisions."""
    __tablename__ = "decisions"

    id = Column(String, primary_key=True)
    ts = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    assistant = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    context = Column(Text, nullable=False)  # JSON string
    recipe_id = Column(String, nullable=False, index=True)
    hparams = Column(Text, nullable=False)  # JSON string
    propensity = Column(Float, nullable=False)
    raw_input = Column(Text, nullable=True)  # Optional for privacy
    engineered_prompt = Column(Text, nullable=True)  # Optional for privacy
    operators = Column(Text, nullable=False)  # JSON list of applied operators

    # Relationship
    feedback_record = relationship("Feedback", back_populates="decision", uselist=False)

    def get_context_dict(self) -> Dict[str, Any]:
        """Parse context JSON string."""
        return json.loads(self.context) if self.context else {}

    def set_context_dict(self, context_dict: Dict[str, Any]):
        """Set context from dictionary."""
        self.context = json.dumps(context_dict)

    def get_hparams_dict(self) -> Dict[str, Any]:
        """Parse hyperparameters JSON string."""
        return json.loads(self.hparams) if self.hparams else {}

    def set_hparams_dict(self, hparams_dict: Dict[str, Any]):
        """Set hyperparameters from dictionary."""
        self.hparams = json.dumps(hparams_dict)

    def get_operators_list(self) -> list:
        """Parse operators JSON list."""
        return json.loads(self.operators) if self.operators else []

    def set_operators_list(self, operators_list: list):
        """Set operators from list."""
        self.operators = json.dumps(operators_list)


class Feedback(Base):
    """Stores feedback for decisions."""
    __tablename__ = "feedback"

    decision_id = Column(String, ForeignKey("decisions.id"), primary_key=True)
    ts = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    reward = Column(Float, nullable=False)
    components = Column(Text, nullable=False)  # JSON string of reward components
    safety_flags = Column(Text, nullable=False)  # JSON list of safety flags

    # Relationship
    decision = relationship("Decision", back_populates="feedback_record")

    def get_components_dict(self) -> Dict[str, float]:
        """Parse components JSON string."""
        return json.loads(self.components) if self.components else {}

    def set_components_dict(self, components_dict: Dict[str, float]):
        """Set components from dictionary."""
        self.components = json.dumps(components_dict)

    def get_safety_flags_list(self) -> list:
        """Parse safety flags JSON list."""
        return json.loads(self.safety_flags) if self.safety_flags else []

    def set_safety_flags_list(self, flags_list: list):
        """Set safety flags from list."""
        self.safety_flags = json.dumps(flags_list)


class BanditStats(Base):
    """Persistent sufficient statistics per (assistant, category, recipe_id)."""
    __tablename__ = "bandit_stats"

    __table_args__ = (
        UniqueConstraint("assistant", "category", "recipe_id", name="uq_bandit_stats_group_recipe"),
        Index("ix_bandit_stats_group", "assistant", "category"),
    )

    # Composite key via unique constraint; use integer surrogate PK for simplicity
    id = Column(Integer, primary_key=True, autoincrement=True)
    assistant = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    recipe_id = Column(String, nullable=False, index=True)

    sample_count = Column(Integer, nullable=False, default=0)
    reward_sum = Column(Float, nullable=False, default=0.0)
    explore_count = Column(Integer, nullable=False, default=0)
    exploit_count = Column(Integer, nullable=False, default=0)

    first_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


# Simple helper to enforce uniqueness via (assistant, category, recipe_id)
# SQLite will not enforce this unless we create the index during migration; for v1 we rely on app logic.


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")


if __name__ == "__main__":
    init_db()
