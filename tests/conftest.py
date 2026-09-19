import os
import tempfile
from pathlib import Path
import pytest

TEST_DIRECTORY = tempfile.TemporaryDirectory(prefix="nearguard-tests-")
os.environ["NEARGUARD_DB_PATH"] = str(Path(TEST_DIRECTORY.name) / "test.db")
os.environ["NEARGUARD_OUTPUTS_DIR"] = str(Path(TEST_DIRECTORY.name) / "outputs")

@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from backend.app.main import app
    with TestClient(app) as instance:
        yield instance

@pytest.fixture(scope="session")
def demo_job(client):
    from backend.app.services.job_worker import worker
    from unittest.mock import patch
    with patch.object(worker, "process_job_async", side_effect=worker._run_job_pipeline):
        response = client.post("/api/upload", data={"use_demo": "true"})
    assert response.status_code == 202, response.text
    result = client.get("/api/jobs/" + response.json()["id"]).json()
    assert result["status"] == "completed", result
    return result
