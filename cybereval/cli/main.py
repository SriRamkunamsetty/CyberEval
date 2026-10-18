"""
CyberEval - Command Line Interface (CLI)
Automates evaluation runs, regression gate checks, and report generation in CI/CD pipelines.
"""

import sys
import asyncio
import click
from cybereval.core.database import init_db, AsyncSessionLocal
from cybereval.services.seed_data import seed_benchmark_data
from cybereval.schemas.evaluation import EvaluationRunCreate
from cybereval.schemas.regression import RegressionComparisonRequest
from cybereval.api.v1.evaluations import start_evaluation_run
from cybereval.api.v1.regressions import compare_runs
from cybereval.api.v1.reports import generate_markdown_report
from cybereval.models.dataset import DatasetVersion
from sqlalchemy import select


@click.group()
def cli():
    """CyberEval CLI - Cybersecurity AI Benchmark & CI/CD Gatekeeper."""
    pass


@cli.command()
@click.option("--model", default="baseline-ground-truth-v1", help="Model name or provider ID")
@click.option("--label", default="cli-eval-run", help="Evaluation run label")
def run(model: str, label: str):
    """Execute an evaluation run headlessly."""
    async def _run():
        await init_db()
        async with AsyncSessionLocal() as session:
            await seed_benchmark_data(session)
            
            # Fetch latest dataset version
            v_res = await session.execute(select(DatasetVersion).order_by(DatasetVersion.created_at.desc()))
            version = v_res.scalars().first()
            if not version:
                click.echo("Error: No benchmark dataset version found.", err=True)
                sys.exit(1)

            payload = EvaluationRunCreate(
                dataset_version_id=version.id,
                model_name=model,
                run_label=label,
            )
            click.echo(f"[*] Starting CyberEval benchmark run for '{model}' on version {version.version_tag}...")
            run_result = await start_evaluation_run(payload=payload, db=session)
            
            click.echo("\n================ CYBEREVAL BENCHMARK RESULTS ================")
            click.echo(f"Run ID:                  {run_result.id}")
            click.echo(f"Overall Score:           {run_result.overall_score:.1%}")
            click.echo(f"Factual Correctness:     {run_result.factual_correctness:.1%}")
            click.echo(f"Evidence Grounding:      {run_result.evidence_grounding:.1%}")
            click.echo(f"Attack-Chain Validity:   {run_result.attack_chain_validity:.1%}")
            click.echo(f"Completeness:            {run_result.completeness:.1%}")
            click.echo(f"Remediation Quality:     {run_result.remediation_quality:.1%}")
            click.echo(f"Format Compliance:       {run_result.format_compliance:.1%}")
            click.echo(f"Bootstrap 95% CI:        [{run_result.ci_lower:.1%}, {run_result.ci_upper:.1%}]")
            click.echo(f"Unsupported Claim Rate:  {run_result.unsupported_claim_rate:.1%}")
            click.echo(f"Critical Gates Passed:   {run_result.critical_gates_passed}")
            click.echo("=============================================================\n")

            if not run_result.critical_gates_passed:
                click.echo("FAILURE: Critical safety gates violated!", err=True)
                sys.exit(1)

    asyncio.run(_run())


@cli.command()
@click.option("--candidate", required=True, help="Candidate Run ID")
@click.option("--baseline", required=True, help="Baseline Run ID")
def gate(candidate: str, baseline: str):
    """Compare candidate run against baseline and enforce CI/CD release gates."""
    async def _gate():
        await init_db()
        async with AsyncSessionLocal() as session:
            req = RegressionComparisonRequest(
                candidate_run_id=candidate,
                baseline_run_id=baseline,
            )
            res = await compare_runs(payload=req, db=session)
            click.echo("\n============= CYBEREVAL CI/CD REGRESSION GATE =============")
            click.echo(f"Verdict:                 {res.gate_verdict}")
            click.echo(f"Gate Passed:             {res.is_gate_passed}")
            click.echo(f"Overall Delta:           {res.overall_score_delta:+.2%}")
            click.echo(f"Regressed Scenarios:     {res.scenarios_regressed_count}")
            click.echo(f"New Unsupported Claims:  {res.new_unsupported_claims_count}")
            if res.blocked_reasons:
                click.echo("\nGate Block Reasons:")
                for r in res.blocked_reasons:
                    click.echo(f" - {r}")
            click.echo("===========================================================\n")

            if not res.is_gate_passed:
                sys.exit(1)

    asyncio.run(_gate())


@cli.command()
@click.option("--run-id", required=True, help="Evaluation Run ID")
@click.option("--output", default=None, help="Output file path for report")
def report(run_id: str, output: str | None):
    """Export benchmark audit report in markdown format."""
    async def _report():
        await init_db()
        async with AsyncSessionLocal() as session:
            text = await generate_markdown_report(run_id=run_id, db=session)
            if output:
                with open(output, "w", encoding="utf-8") as f:
                    f.write(text)
                click.echo(f"[+] Audit report saved to {output}")
            else:
                click.echo(text)

    asyncio.run(_report())


if __name__ == "__main__":
    cli()
