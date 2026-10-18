"""
Integration tests for CyberEval FastAPI Endpoints
"""

import pytest
from httpx import AsyncClient, ASGITransport
from cybereval.main import app
from cybereval.core.database import init_db, AsyncSessionLocal
from cybereval.services.seed_data import seed_benchmark_data


@pytest.mark.asyncio
async def test_full_api_workflow():
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_benchmark_data(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Datasets API
        ds_res = await client.get("/api/v1/datasets")
        assert ds_res.status_code == 200
        datasets = ds_res.json()
        assert len(datasets) >= 1
        ds_id = datasets[0]["id"]
        v_id = datasets[0]["versions"][0]["id"]

        # 2. Scenarios API
        sc_res = await client.get(f"/api/v1/datasets/{ds_id}/versions/{v_id}/scenarios")
        assert sc_res.status_code == 200
        scenarios = sc_res.json()
        assert len(scenarios) >= 1
        first_scen_id = scenarios[0]["id"]

        sc_detail = await client.get(f"/api/v1/datasets/scenarios/{first_scen_id}")
        assert sc_detail.status_code == 200
        assert "evidence_items" in sc_detail.json()

        # 3. Model Providers API
        mp_res = await client.get("/api/v1/models/providers")
        assert mp_res.status_code == 200
        providers = mp_res.json()
        assert len(providers) >= 1

        # 4. Evaluation Run API (Run ground truth baseline on a single scenario)
        eval_payload = {
            "dataset_version_id": v_id,
            "model_name": "baseline-ground-truth-v1",
            "run_label": "integration-test-run",
            "scenario_subset_codes": [scenarios[0]["scenario_code"]],
        }
        eval_res = await client.post("/api/v1/evaluations", json=eval_payload)
        assert eval_res.status_code == 201
        run_data = eval_res.json()
        run_id = run_data["id"]
        assert run_data["status"] == "completed"
        assert run_data["overall_score"] is not None

        # 5. Evaluation Results API
        res_res = await client.get(f"/api/v1/evaluations/{run_id}/results")
        assert res_res.status_code == 200
        res_data = res_res.json()
        assert len(res_data["responses"]) == 1
        m_resp_id = res_data["responses"][0]["id"]

        # 6. Claim-to-Evidence Graph API (Innovation 1)
        graph_res = await client.get(f"/api/v1/claims/graph/{m_resp_id}")
        assert graph_res.status_code == 200
        graph_data = graph_res.json()
        assert "nodes" in graph_data
        assert "edges" in graph_data

        # 7. Audit Report API
        report_res = await client.get(f"/api/v1/reports/{run_id}/markdown")
        assert report_res.status_code == 200
        assert "# CyberEval Evaluation Audit Report" in report_res.text

        # 8. Benchmark Leakage Audit API (Innovation 6)
        leak_res = await client.get(f"/api/v1/audit/leakage/{v_id}")
        assert leak_res.status_code == 200
        assert "integrity_passed" in leak_res.json()
