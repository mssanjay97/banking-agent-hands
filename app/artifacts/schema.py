from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field
from app.artifacts.surface import Surface


class ArtifactInput(BaseModel):
    type: str
    required: bool = True


class ArtifactOutput(BaseModel):
    type: str


class Target(BaseModel):
    role: Optional[str] = None
    name: Optional[str] = None
    id: Optional[str] = None
    selector: Optional[str] = None


class ArtifactStep(BaseModel):
    action: str
    target: Any
    value: Optional[str] = None
    output: Optional[str] = None


class Checkpoint(BaseModel):
    type: str
    target: Target


class BusinessOutcome(BaseModel):
    """
    An expected business result that is not a successful completion.
    """

    signal: str
    status: str


class CapabilityArtifact(BaseModel):
    id: str
    version: str
    goal: Optional[str] = None
    start_url: Optional[str] = None

    surface: Surface

    inputs: Dict[str, ArtifactInput]

    steps: List[ArtifactStep]

    outputs: Dict[str, ArtifactOutput]

    checkpoint: Optional[Checkpoint] = None

    business_outcomes: List[BusinessOutcome] = Field(
        default_factory=list
    )