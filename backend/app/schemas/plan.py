"""Pydantic V2 schemas for StructuredPlan, PlanStep, and grounded EvidenceReference."""
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.evidence import EvidencePurpose, EvidenceReference


class PlanStep(BaseModel):
    """An individual atomic step in an engineering implementation plan."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique step identifier, e.g. 'step-1'")
    description: str = Field(..., description="Actionable description of the code modification or test")
    target_files: list[str] = Field(default_factory=list, description="Target repository relative file paths")
    dependencies: list[str] = Field(default_factory=list, description="IDs of prior steps that must complete first")
    rationale: str = Field(..., description="Technical justification for this specific step")


class StructuredPlan(BaseModel):
    """
    Evidence-grounded structured implementation plan produced by PlannerAgent.
    Every factual claim or target file modification must be grounded in verified
    repository evidence citations.
    """
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(..., description="High-level engineering objective")
    problem_summary: str = Field(..., description="Concise diagnosis of the issue")
    problem_interpretation: Optional[str] = Field(default=None, description="Detailed analysis and interpretation of the issue")
    root_cause_hypothesis: Optional[str] = Field(default=None, description="Hypothesis explaining the root cause of the bug or requirement")
    evidence_citations: List[EvidenceReference] = Field(default_factory=list, description="Cryptographically bound citations to source code evidence")
    target_files: List[str] = Field(default_factory=list, description="Target repository relative file paths to be modified or created")
    steps: List[PlanStep] = Field(..., min_length=1, description="Ordered atomic implementation steps")
    acceptance_criteria: List[str] = Field(..., min_length=1, description="Explicit conditions for considering the fix complete")
    required_tests: List[str] = Field(..., description="Test files or commands that must pass")
    regression_test_strategy: List[str] = Field(default_factory=list, description="Explicit test strategy to prevent regressions")
    risks: List[str] = Field(default_factory=list, description="Potential regressions, security concerns, or compatibility risks")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions made about repository context")
    uncertainties: List[str] = Field(default_factory=list, description="Unresolved uncertainties, missing information, or ambiguities")
    needs_additional_context: bool = Field(default=False, description="Flag indicating more context is required before code generation")
    additional_context_request: Optional[str] = Field(default=None, description="Specific files, symbols, or queries requested if context was insufficient")
    declined_reason: Optional[str] = Field(default=None, description="Explicit reason if the planner declines to proceed with implementation")
    is_verified: bool = Field(default=False, description="Whether plan evidence citations were validated against verified repository context")

    @model_validator(mode="before")
    @classmethod
    def sync_backward_compatible_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Sync problem_interpretation and problem_summary
            if "problem_summary" in data and not data.get("problem_interpretation"):
                data["problem_interpretation"] = data["problem_summary"]
            elif "problem_interpretation" in data and not data.get("problem_summary"):
                data["problem_summary"] = data["problem_interpretation"]

            # Populate target_files from steps if not explicitly passed
            if not data.get("target_files") and "steps" in data and isinstance(data["steps"], list):
                collected_targets: list[str] = []
                for step in data["steps"]:
                    if isinstance(step, dict) and "target_files" in step and isinstance(step["target_files"], list):
                        for tf in step["target_files"]:
                            if tf not in collected_targets:
                                collected_targets.append(tf)
                if collected_targets:
                    data["target_files"] = collected_targets

        return data
