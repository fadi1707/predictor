from pydantic import BaseModel, Field
from typing import Literal

class ChatRequest(BaseModel):
    text: str = Field(min_length=1)
class QueueJobRequest(BaseModel):
    job_type: str
    target_name: str = "local"
    payload: dict = {}
class GoalRequest(BaseModel):
    goal: str
    target_name: str = "local"
class ApprovalDecision(BaseModel):
    approval_id: int
    decision: Literal["approve", "reject"]
class TargetCommandRequest(BaseModel):
    target_name: str = "local"
    command: str = Field(min_length=1)
class RestoreRollbackRequest(BaseModel):
    rollback_id: int

class KlementTeam(BaseModel):
    country: str = Field(min_length=1)
    gdp_per_capita_usd: float = Field(gt=0)
    population: int = Field(gt=0)
    football_popularity: float = Field(ge=0, le=1)
    avg_temp_c: float
    fifa_rank: int = Field(ge=1)
    fifa_points: float | None = Field(default=None, gt=0)
    is_host: bool = False

class KlementMatchRequest(BaseModel):
    team_a: KlementTeam
    team_b: KlementTeam

class KlementTournamentRequest(BaseModel):
    teams: list[KlementTeam] = Field(min_length=2)
    simulations: int = Field(default=10000, ge=1, le=100000)
    seed: int | None = None

class FWC26WinnerRequest(BaseModel):
    mode: Literal["published", "simulation"] = "published"
    simulations: int = Field(default=10000, ge=1, le=100000)
    seed: int | None = None
