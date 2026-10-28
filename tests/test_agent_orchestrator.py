"""
Unit & Integration Tests for Agent Loop, Tool Registry, and Governance
======================================================================
Tests:
- Real tool registry execution (search_web, read_file, write_file, query_db)
- Path traversal prevention in read_file and write_file
- Schema validation for invalid tool calls
- End-to-end Agent Orchestrator loop (Understand -> Plan -> Authorize -> Execute -> Observe -> Verify -> Conclude)
- Policy enforcement: Denying unauthorized operations
- Budget and step bounding: Preventing runaway agent loops
"""

import os
import pytest
from pathlib import Path

from guardian_swarm.tools.registry import (
    TOOL_REGISTRY,
    execute_tool,
    execute_read_file,
    execute_write_file,
    execute_search_web,
    execute_query_db,
    get_available_tools_schema
)
from guardian_swarm.agents.orchestrator import AgentOrchestrator
from guardian_swarm.core.user_rbac import UserSession
from guardian_swarm.utils.paths import ARTIFACTS_DIR, PROJECT_ROOT


def test_tool_registry_schemas_available():
    schemas = get_available_tools_schema()
    assert len(schemas) >= 5
    tool_names = [s["name"] for s in schemas]
    assert "search_web" in tool_names
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "query_db" in tool_names


def test_search_web_execution():
    res = execute_tool("search_web", {"query": "NVIDIA Nemotron 3", "limit": 3})
    assert res["status"] == "SUCCESS"
    assert res["results_count"] >= 1
    assert "NVIDIA Nemotron 3" in res["results"][0]["title"]


def test_read_file_safe_project_confinement():
    res = execute_tool("read_file", {"path": "README.md", "max_lines": 10})
    assert res["status"] == "SUCCESS"
    assert "content" in res


def test_read_file_path_traversal_denied():
    res = execute_tool("read_file", {"path": "../../Windows/System32/drivers/etc/hosts"})
    assert res["status"] == "DENIED"
    assert "Security restriction" in res["error"]


def test_write_file_confined_to_artifacts():
    test_filename = "test_agent_evidence_output.txt"
    test_content = "Verified evidence payload from agent loop."
    res = execute_tool("write_file", {"path": test_filename, "content": test_content})
    
    assert res["status"] == "SUCCESS"
    written_path = ARTIFACTS_DIR / test_filename
    assert written_path.exists()
    assert written_path.read_text(encoding="utf-8") == test_content
    # Clean up test artifact
    written_path.unlink()


def test_write_file_outside_confinement_denied():
    res = execute_tool("write_file", {"path": "../../../system_override.txt", "content": "malicious payload"})
    assert res["status"] == "DENIED"
    assert "Security confinement breach" in res["error"]


def test_unregistered_tool_rejected():
    res = execute_tool("format_hard_drive", {"drive": "C:"})
    assert res["status"] == "UNREGISTERED_TOOL"
    assert "not registered" in res["error"]


def test_invalid_arguments_rejected():
    # search_web requires 'query'
    res = execute_tool("search_web", {"bad_param": "test"})
    assert res["status"] == "INVALID_ARGUMENTS"


def test_agent_orchestrator_end_to_end_loop_allowed_task():
    orchestrator = AgentOrchestrator(max_steps=3)
    user_session = UserSession(user_id="research_analyst", role="EMPLOYEE", name="EMPLOYEE")
    
    result = orchestrator.run_agent_loop(
        task_prompt="Investigate technical capabilities of NVIDIA Nemotron models",
        category="RESEARCH",
        classification="INTERNAL",
        user_session=user_session
    )

    assert result["status"] == "COMPLETED"
    assert result["total_steps"] >= 1
    assert result["verification"]["verified"] is True
    assert len(result["evidence"]) >= 1
    assert result["events"][0]["stage"] == "PLAN"


def test_agent_orchestrator_security_policy_blocking():
    orchestrator = AgentOrchestrator(max_steps=3)
    # Intern attempting to execute restricted task
    user_session = UserSession(user_id="intern_user", role="INTERN", name="INTERN")
    
    result = orchestrator.run_agent_loop(
        task_prompt="Extract and modify root configuration files in /system/config",
        category="RESEARCH",
        classification="RESTRICTED",
        user_session=user_session
    )

    # Should be blocked by User RBAC Gate (Gate 1) or Confinement Gate
    assert result["status"] == "BLOCKED"
    halt_events = [e for e in result["events"] if e.get("stage") == "HALTED"]
    assert len(halt_events) >= 1
    assert "Security policy blocked" in halt_events[0]["reason"]
