"""
CyberEval - Audit & Evaluation Report Generation API Endpoints
Generates auditable, executive and technical reports in Markdown, JSON, and HTML.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from cybereval.core.database import get_db
from cybereval.models.evaluation import EvaluationRun, ModelResponse, Score
from cybereval.models.dataset import Scenario

router = APIRouter(prefix="/reports", tags=["Reports & Audits"])


@router.get("/{run_id}/markdown", response_class=PlainTextResponse)
async def generate_markdown_report(run_id: str, db: AsyncSession = Depends(get_db)):
    """
    Generates a formal Markdown evaluation report conforming to CyberEval benchmark standards.
    """
    stmt = (
        select(EvaluationRun)
        .options(
            selectinload(EvaluationRun.responses).selectinload(ModelResponse.scores),
        )
        .where(EvaluationRun.id == run_id)
    )
    res = await db.execute(stmt)
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")

    gate_status = "PASSED" if run.critical_gates_passed else "FAILED (GATE VIOLATION)"

    report = f"""# CyberEval Evaluation Audit Report
**Run ID:** `{run.id}`  
**Model:** `{run.model_name}`  
**Dataset Version:** `{run.dataset_version_id}`  
**Status:** {run.status.upper()}  
**Critical Safety Gates:** **{gate_status}**  
**Reproducibility Hash:** `{run.reproducibility_hash}`  
**Execution Time:** {run.execution_time_seconds}s | **Tokens:** {run.total_tokens_consumed}

---

## 1. Executive Summary & Dimension Scores

| Evaluation Dimension | Weight | Score | Evaluation Method |
| :--- | :--- | :--- | :--- |
| **Factual Correctness** | 30% | **{run.factual_correctness or 0.0:.1%}** | Reference-Based Verification |
| **Evidence Grounding** | 25% | **{run.evidence_grounding or 0.0:.1%}** | Claim-to-Evidence Bipartite Graph |
| **Attack-Chain Validity** | 20% | **{run.attack_chain_validity or 0.0:.1%}** | Topological Invariants & ATT&CK F1 |
| **Completeness** | 10% | **{run.completeness or 0.0:.1%}** | Required Finding Recall |
| **Remediation Quality** | 10% | **{run.remediation_quality or 0.0:.1%}** | Mitigation Relevance & Safety |
| **Format Compliance** | 5% | **{run.format_compliance or 0.0:.1%}** | Deterministic JSON Schema |
| **Overall Weighted Score** | **100%** | **{run.overall_score or 0.0:.1%}** | Calibrated Multi-Layer Score |

---

## 2. Statistical Reliability & Confidence Bounds

- **Bootstrap 95% Confidence Interval:** `[{run.ci_lower or 0.0:.1%}, {run.ci_upper or 0.0:.1%}]`
- **Standard Error ($SE$):** `{run.std_error or 0.0:.4f}`
- **Unsupported-Claim Rate:** `{run.unsupported_claim_rate or 0.0:.1%}`
- **Critical Omission Rate:** `{run.critical_omission_rate or 0.0:.1%}`

---

## 3. Scenario-Level Breakdown

| Scenario ID | Weighted Score | Gate Status | Latency | Tokens |
| :--- | :--- | :--- | :--- | :--- |
"""

    for r in run.responses:
        sc_val = r.scores.weighted_score if r.scores else 0.0
        g_pass = "PASS" if (r.scores and r.scores.critical_gates_passed) else "FAIL"
        report += f"| `{r.scenario_id[:8]}` | {sc_val:.1%} | {g_pass} | {r.latency_ms}ms | {r.prompt_tokens + r.completion_tokens} |\n"

    report += """
---
*Generated autonomously by CyberEval — Enterprise Cybersecurity AI Evaluation Platform.*
"""
    return report
