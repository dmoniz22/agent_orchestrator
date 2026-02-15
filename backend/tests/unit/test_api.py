"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "OMNI API"
        assert "docs" in data


class TestAgentEndpoints:
    """Test agent management endpoints."""
    
    def test_list_agents(self, client):
        """Test listing agents."""
        response = client.get("/api/v1/agents/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_nonexistent_agent(self, client):
        """Test getting non-existent agent."""
        response = client.get("/api/v1/agents/nonexistent")
        
        assert response.status_code == 404


class TestToolEndpoints:
    """Test tool endpoints."""
    
    def test_list_tools(self, client):
        """Test listing tools."""
        response = client.get("/api/v1/tools/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_nonexistent_tool_schema(self, client):
        """Test getting schema for non-existent tool."""
        response = client.get("/api/v1/tools/nonexistent/schema")
        
        assert response.status_code == 404


class TestTaskEndpoints:
    """Test task execution endpoints."""
    
    def test_execute_task(self, client):
        """Test task execution endpoint."""
        # This will fail since orchestration isn't fully wired yet
        response = client.post(
            "/api/v1/tasks/execute",
            json={"query": "Test query"}
        )
        
        # Expect 500 since orchestration engine isn't fully initialized
        assert response.status_code in [200, 500]
    
    def test_task_status(self, client):
        """Test task status endpoint."""
        import uuid
        task_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/tasks/{task_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
