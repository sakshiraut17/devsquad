"""Security Policy Engine for DevSquad AI Security Guardian."""

from typing import List, Tuple
from app.schemas.security import (
    SecurityCategory,
    SecurityFindingSchema,
    SecurityGateStatus,
    SecuritySeverity,
    SecuritySummary,
)


class SecurityPolicyEngine:
    """Evaluates security findings against the mandatory blocking policy."""

    def __init__(self, policy_version: str = "1.0.0"):
        self.policy_version = policy_version

    def evaluate(
        self,
        findings: List[SecurityFindingSchema],
    ) -> Tuple[SecurityGateStatus, bool, List[str], SecuritySummary]:
        """Evaluate a list of findings to produce a deterministic gate decision.

        Returns:
            (status, can_approve, block_reasons, summary)
        """
        summary = SecuritySummary()
        block_reasons: List[str] = []

        for f in findings:
            sev = f.severity.upper()
            if sev == SecuritySeverity.CRITICAL.value:
                summary.critical += 1
            elif sev == SecuritySeverity.HIGH.value:
                summary.high += 1
            elif sev == SecuritySeverity.MEDIUM.value:
                summary.medium += 1
            elif sev == SecuritySeverity.LOW.value:
                summary.low += 1
            else:
                summary.info += 1
            summary.total += 1

            # Determine whether this finding blocks human approval
            is_blocker = False
            if sev == SecuritySeverity.CRITICAL.value:
                is_blocker = True
                block_reasons.append(f"[CRITICAL] {f.title}: {f.description}")
            elif sev == SecuritySeverity.HIGH.value and f.is_blocking:
                is_blocker = True
                block_reasons.append(f"[HIGH] {f.title}: {f.description}")
            elif f.category in (
                SecurityCategory.SECRET_EXPOSURE.value,
                SecurityCategory.SECURITY_REGRESSION.value,
                SecurityCategory.PATCH_SCOPE.value,
            ) and f.is_blocking:
                is_blocker = True
                block_reasons.append(f"[{sev}] {f.title}: {f.description}")

            f.is_blocking = is_blocker

        if block_reasons:
            status = SecurityGateStatus.BLOCKED
            can_approve = False
        else:
            status = SecurityGateStatus.PASSED
            can_approve = True

        return status, can_approve, block_reasons, summary
