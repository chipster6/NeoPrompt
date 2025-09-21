from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class Quality(BaseModel):
    score: Optional[float] = None
    signals: Dict[str, Any] = Field(default_factory=dict)


class Meta(BaseModel):
    assumptions: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    rationales: List[str] = Field(default_factory=list)
    quality: Quality = Field(default_factory=Quality)


class Sections(BaseModel):
    goal: Optional[str] = None
    inputs: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    io_format: Optional[str] = None
    examples: List[Dict[str, Any]] = Field(default_factory=list)


class PromptDoc(BaseModel):
    """
    JSON-pointer friendly keys:
      /seed
      /model
      /category
      /context
      /packs_applied
      /sections/goal
      /sections/inputs
      /sections/constraints
      /sections/steps
      /sections/acceptance_criteria
      /sections/io_format
      /sections/examples
      /meta/assumptions
      /meta/open_questions
      /meta/rationales
      /meta/quality/score
      /meta/quality/signals
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    seed: Optional[int] = None
    model: Optional[str] = None
    category: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    packs_applied: List[str] = Field(default_factory=list)
    sections: Sections = Field(default_factory=Sections)
    meta: Meta = Field(default_factory=Meta)

    def to_hlep(self) -> str:
        parts: List[str] = []
        if self.sections.goal:
            parts.append(f"Goal:\n{self.sections.goal}\n")
        if self.sections.inputs:
            parts.append("Inputs:\n- " + "\n- ".join(self.sections.inputs) + "\n")
        if self.sections.constraints:
            parts.append("Constraints:\n- " + "\n- ".join(self.sections.constraints) + "\n")
        if self.sections.steps:
            parts.append("Steps:\n- " + "\n- ".join(self.sections.steps) + "\n")
        if self.sections.acceptance_criteria:
            parts.append("Acceptance Criteria:\n- " + "\n- ".join(self.sections.acceptance_criteria) + "\n")
        if self.sections.io_format:
            parts.append(f"IO Format:\n{self.sections.io_format}\n")
        if self.sections.examples:
            parts.append("Examples:\n" + "\n".join([str(e) for e in self.sections.examples]) + "\n")
        return "\n".join(parts).strip()
