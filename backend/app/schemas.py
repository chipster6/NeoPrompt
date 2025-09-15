"""Pydantic schemas for API request/response contracts."""
from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import uuid


# Request schemas
class ChooseRequest(BaseModel):
    assistant: str = Field(..., description="Target assistant (chatgpt, claude, gemini, deepseek)")
    category: str = Field(..., description="Domain category (coding, science, psychology, law, politics)")
    raw_input: str = Field(..., description="Raw user input to be engineered")
    options: Dict[str, Any] = Field(default_factory=dict, description="Optional settings")
    context_features: Dict[str, Any] = Field(default_factory=dict, description="Input analysis features")


class FeedbackRequest(BaseModel):
    decision_id: str = Field(..., description="UUID of the decision to provide feedback for")
    reward_components: Dict[str, float] = Field(..., description="Individual reward signals")
    reward: float = Field(..., ge=0.0, le=1.0, description="Aggregate reward score [0,1]")
    safety_flags: List[str] = Field(default_factory=list, description="Safety/quality concerns")


class StatsItem(BaseModel):
    assistant: str
    category: str
    recipe_id: str
    mean_reward: float
    count: int


class StatsResponse(BaseModel):
    epsilon: float
    items: List[StatsItem]


# Response schemas
class ChooseResponse(BaseModel):
    decision_id: str = Field(..., description="Unique identifier for this decision")
    recipe_id: str = Field(..., description="Selected recipe identifier")
    engineered_prompt: str = Field(..., description="Final engineered prompt")
    operators: List[str] = Field(..., description="Applied prompt operators")
    hparams: Dict[str, Any] = Field(..., description="Hyperparameters used")
    propensity: float = Field(..., ge=0.0, le=1.0, description="Selection confidence")
    notes: List[str] = Field(default_factory=list, description="Processing notes")


class FeedbackResponse(BaseModel):
    ok: bool = Field(True, description="Success indicator")
    message: Optional[str] = Field(None, description="Optional status message")


class HistoryItem(BaseModel):
    id: str
    timestamp: datetime
    assistant: str
    category: str
    recipe_id: str
    propensity: float
    reward: Optional[float] = None
    operators: List[str]
    raw_input: Optional[str] = None
    engineered_prompt: Optional[str] = None


class HistoryResponse(BaseModel):
    items: List[HistoryItem]
    total: int
    limit: int
    offset: int


class Recipe(BaseModel):
    id: str
    assistant: str
    category: str
    operators: List[str]
    hparams: Dict[str, Any]
    guards: Dict[str, Any] = Field(default_factory=dict)
    examples: List[str] = Field(default_factory=list)


class RecipeValidationError(BaseModel):
    file_path: str
    error: str
    line_number: Optional[int] = None
    error_type: Optional[str] = None  # yaml_parse | schema_validation | semantic_validation | cross_file_validation
    severity: Optional[str] = None  # 'error' | 'warning'


class RecipesDepsById(BaseModel):
    extends: List[str] = Field(default_factory=list)
    includes: List[str] = Field(default_factory=list)


class RecipesDepsByFile(BaseModel):
    includes: List[str] = Field(default_factory=list)
    defines: List[str] = Field(default_factory=list)


class RecipesDeps(BaseModel):
    by_id: Dict[str, RecipesDepsById] = Field(default_factory=dict)
    by_file: Dict[str, RecipesDepsByFile] = Field(default_factory=dict)


class RecipesResponse(BaseModel):
    recipes: List[Recipe]
    errors: List[RecipeValidationError]
    deps: Optional[RecipesDeps] = None


# Internal data models
class DecisionContext(BaseModel):
    input_tokens: int = 0
    language: str = "en"
    enhanced: bool = False
    force_json: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RewardComponents(BaseModel):
    user_like: Optional[float] = None  # 1.0 for thumbs up, 0.0 for thumbs down
    copied: Optional[float] = None     # 1.0 if copied, 0.0 otherwise
    format_ok: Optional[float] = None  # 1.0 if format validates, 0.0 otherwise
    custom: Dict[str, float] = Field(default_factory=dict)
