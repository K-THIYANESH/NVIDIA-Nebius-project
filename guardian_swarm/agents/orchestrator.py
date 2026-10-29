"""
NVIDIA Nemotron Agentic Engine: Planner, Decision Engine, Verifier & Safe Loop
=============================================================================
Orchestrates the core agentic loop:
Understand -> Plan -> Authorize -> Execute -> Observe -> Verify -> Conclude

Driven by NVIDIA Nemotron via Nebius Token Factory with strict fallback,
bounded step budget, policy authorization, and cryptographic audit logging.
"""

import os
import json
import re
import time
from typing import Dict, Any, List, Optional, Tuple

from guardian_swarm.providers.nebius_client import NebiusClient
from guardian_swarm.providers.model_config import DEFAULT_NEBIUS_MODEL
from guardian_swarm.tools.registry import get_available_tools_schema, execute_tool, TOOL_REGISTRY
from guardian_swarm.core.interceptor import GuardianInterceptor
from guardian_swarm.core.user_rbac import UserSession
from guardian_swarm.utils.logger import log_event


PLANNER_SYSTEM_PROMPT = """You are the Guardian Swarm Chief Planning Agent powered by NVIDIA Nemotron.
Your task is to analyze user objectives, determine required evidence, and formulate a structured execution plan.

You MUST respond strictly in valid JSON matching this schema:
{
  "task_analysis": "Concise summary of the user's objective",
  "category": "RESEARCH" | "CODE" | "DRAFTING" | "DATA_ANALYSIS" | "SUPPORT",
  "assigned_agent": "researcher" | "coder" | "deck_builder",
  "steps": [
    {
      "step_number": 1,
      "tool_name": "registered tool name",
      "arguments": { "arg_name": "arg_value" },
      "target": "resource path or identifier",
      "reason": "Technical rationale grounded in objective",
      "expected_evidence": "Description of evidence required to verify step"
    }
  ],
  "estimated_steps": 1-5,
  "risk_assessment": "LOW" | "MEDIUM" | "HIGH"
}

Permitted registered tools:
search_web, read_file, write_file, query_db, extract_text, create_slide, run_test

Never suggest tools outside this permitted set.
"""

DECISION_SYSTEM_PROMPT = """You are the Guardian Swarm Decision Agent powered by NVIDIA Nemotron.
Given a user task and accumulated tool execution evidence, decide whether to execute the next tool or conclude.

Respond strictly in valid JSON:
{
  "decision": "EXECUTE_TOOL" | "CONCLUDE" | "ESCALATE_TO_HUMAN",
  "tool_name": "registered tool name or null if concluding",
  "arguments": { "arg_name": "val" },
  "target": "target path or null",
  "reason": "Why this action is needed or why evidence is sufficient to conclude",
  "expected_evidence": "Evidence needed or null",
  "confidence": 0.0 to 1.0
}
"""

VERIFIER_SYSTEM_PROMPT = """You are the Guardian Swarm Verification Agent powered by NVIDIA Nemotron.
Your job is to objectively verify whether the tool execution evidence satisfies the user objective.
If the tool returned status 'SUCCESS' with relevant content, consider the step verified (verified: true).
Only mark verified: false if the tool explicitly failed, returned an error status, was blocked, or produced empty output.

Respond strictly in valid JSON:
{
  "verified": true | false,
  "confidence": 0.0 to 1.0,
  "evidence_summary": "Summary of confirmed facts from tool outputs",
  "unverified_items": ["Any assumptions or missing facts"],
  "final_conclusion": "Clear, grounded conclusion report for the user"
}
"""


def _clean_json_output(raw_text: str) -> Optional[Dict[str, Any]]:
    """Robustly extracts and parses JSON from model responses."""
    if not raw_text:
        return None
    # Strip markdown code blocks
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Search for first { ... } block
        match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    return None


class AgentOrchestrator:
    """
    Coordinates the 7-stage agent loop:
    Understand -> Plan -> Authorize -> Execute -> Observe -> Verify -> Conclude
    """

    def __init__(
        self,
        nebius_client: Optional[NebiusClient] = None,
        interceptor: Optional[GuardianInterceptor] = None,
        max_steps: int = 5
    ):
        self.client = nebius_client or NebiusClient()
        self.interceptor = interceptor or GuardianInterceptor()
        self.max_steps = max_steps

    def create_plan(
        self,
        task_prompt: str,
        category: str = "RESEARCH",
        user_session: Optional[UserSession] = None
    ) -> Dict[str, Any]:
        """Stage 1 & 2: Understand & Plan using NVIDIA Nemotron via Nebius or structured heuristics."""
        tools_schema = get_available_tools_schema()
        
        if self.client.is_configured:
            messages = [
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": f"User Task: {task_prompt}\nPreferred Category: {category}\nAvailable Tools: {json.dumps(tools_schema)}"}
            ]
            resp = self.client.chat_completion(messages=messages, temperature=0.2)
            if resp.get("success"):
                parsed = _clean_json_output(resp.get("content", ""))
                if parsed and "steps" in parsed and isinstance(parsed["steps"], list):
                    parsed["source"] = f"NVIDIA Nemotron via Nebius ({self.client.model})"
                    parsed["live_inference"] = True
                    return parsed

        # Robust, deterministic fallback planner when live key is absent or on transient error
        return self._heuristic_plan(task_prompt, category)

    def _heuristic_plan(self, task_prompt: str, category: str) -> Dict[str, Any]:
        """Provides a valid structured plan matching tool schemas."""
        cat_upper = category.upper()
        if "code" in cat_upper or "file" in task_prompt.lower() and "write" in task_prompt.lower():
            target_tool = "write_file"
            agent_type = "coder"
            target = "generated_solution.py"
            arguments = {"path": target, "content": f"# Solution generated for: {task_prompt}\ndef run(): return True\n"}
            expected = "File written to artifacts successfully"
        elif "slide" in task_prompt.lower() or "deck" in cat_upper or "draft" in cat_upper:
            target_tool = "create_slide"
            agent_type = "deck_builder"
            target = "slide_presentation"
            arguments = {"title": task_prompt[:60], "template": "technical_dark"}
            expected = "Slide created and structured"
        elif "read" in task_prompt.lower() or "check" in task_prompt.lower():
            target_tool = "read_file"
            agent_type = "researcher"
            target = "README.md"
            arguments = {"path": target, "max_lines": 50}
            expected = "File content extracted safely"
        else:
            target_tool = "search_web"
            agent_type = "researcher"
            target = task_prompt[:40]
            arguments = {"query": task_prompt, "limit": 3}
            expected = "Structured research evidence results"

        return {
            "task_analysis": f"Objective: {task_prompt}",
            "category": cat_upper if cat_upper in ["RESEARCH", "CODE", "DRAFTING", "DATA_ANALYSIS", "SUPPORT"] else "RESEARCH",
            "assigned_agent": agent_type,
            "steps": [
                {
                    "step_number": 1,
                    "tool_name": target_tool,
                    "arguments": arguments,
                    "target": target,
                    "reason": f"Initial evidence gathering for '{task_prompt}'",
                    "expected_evidence": expected
                }
            ],
            "estimated_steps": 1,
            "risk_assessment": "LOW",
            "source": "Guardian Swarm Local Deterministic Planner (Awaiting Nebius Live Key for Dynamic Generation)",
            "live_inference": False
        }

    def run_agent_loop(
        self,
        task_prompt: str,
        category: str = "RESEARCH",
        classification: str = "INTERNAL",
        user_session: Optional[UserSession] = None
    ) -> Dict[str, Any]:
        """
        Executes bounded 7-stage workflow:
        Understand -> Plan -> Authorize -> Execute -> Observe -> Verify -> Conclude
        """
        start_time = time.time()
        session = user_session or UserSession(user_id="intern_user", role="INTERN", name="INTERN")
        events: List[Dict[str, Any]] = []

        # Stage 1 & 2: Plan
        plan = self.create_plan(task_prompt, category, session)
        events.append({
            "stage": "PLAN",
            "plan": plan,
            "timestamp": time.time()
        })

        steps = plan.get("steps", [])
        evidence_chain: List[Dict[str, Any]] = []
        final_verdict = "INCOMPLETE"
        completed_steps = 0
        overall_approved = True

        for step in steps[:self.max_steps]:
            completed_steps += 1
            tool_name = step.get("tool_name", "search_web")
            arguments = step.get("arguments", {})
            target = step.get("target", "default_target")
            agent_type = plan.get("assigned_agent", "researcher")

            # Stage 3: Authorize (Independent Server-Side Multi-Gate Governance)
            params = {
                "prompt": task_prompt,
                "data_classification": classification,
                "task_category": category,
                "task_group": category,
                "model_name": self.client.model,
                **arguments
            }

            approved, audit_entry = self.interceptor.intercept_action(
                agent_id=f"{agent_type}_{session.user_id}",
                agent_type=agent_type,
                tool=tool_name,
                target=target,
                params=params,
                user_session=session
            )

            events.append({
                "stage": "AUTHORIZE",
                "step": completed_steps,
                "tool": tool_name,
                "target": target,
                "approved": approved,
                "verdict": audit_entry.get("verdict"),
                "reasoning": audit_entry.get("reasoning"),
                "trace": audit_entry.get("investigation_trace", []),
                "action_id": audit_entry.get("action_id")
            })

            if not approved:
                overall_approved = False
                events.append({
                    "stage": "HALTED",
                    "step": completed_steps,
                    "reason": f"Security policy blocked execution of tool '{tool_name}' on target '{target}'.",
                    "error_code": audit_entry.get("params", {}).get("error_code")
                })
                break

            # Stage 4: Execute (Real Tool Execution within Confinement)
            tool_res = execute_tool(tool_name, arguments)
            
            # Stage 5: Observe (Capture real tool results)
            events.append({
                "stage": "OBSERVE",
                "step": completed_steps,
                "tool": tool_name,
                "result": tool_res
            })

            evidence_chain.append({
                "step": completed_steps,
                "tool": tool_name,
                "target": target,
                "result": tool_res
            })

        # Stage 6: Verify (Objective Evaluation of Evidence)
        verification_result = self._verify_evidence(task_prompt, evidence_chain)
        events.append({
            "stage": "VERIFY",
            "verification": verification_result
        })

        # Stage 7: Conclude
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        conclude_status = "COMPLETED" if overall_approved and verification_result.get("verified") else ("BLOCKED" if not overall_approved else "REVIEW_REQUIRED")

        return {
            "task_id": f"task-agent-{int(start_time)}",
            "status": conclude_status,
            "task_prompt": task_prompt,
            "category": category,
            "classification": classification,
            "user_id": session.user_id,
            "user_role": session.role,
            "model": self.client.model,
            "provider": "Nebius Token Factory" if self.client.is_configured else "Nebius Token Factory (Ready - Config Pending)",
            "live_inference": self.client.is_configured,
            "plan": plan,
            "evidence": evidence_chain,
            "verification": verification_result,
            "events": events,
            "latency_ms": elapsed_ms,
            "total_steps": completed_steps
        }

    def _verify_evidence(self, task_prompt: str, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Objective verification against tool evidence."""
        if not evidence:
            return {
                "verified": False,
                "confidence": 0.0,
                "evidence_summary": "No tool evidence collected due to policy block or empty plan.",
                "unverified_items": ["All claims unverified"],
                "final_conclusion": "Execution halted by security policy before evidence gathering."
            }

        successful_steps = [e for e in evidence if e.get("result", {}).get("status") == "SUCCESS"]
        all_passed = len(successful_steps) == len(evidence)

        if self.client.is_configured:
            messages = [
                {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Task: {task_prompt}\nEvidence: {json.dumps(evidence)}"}
            ]
            resp = self.client.chat_completion(messages=messages, temperature=0.1)
            if resp.get("success"):
                parsed = _clean_json_output(resp.get("content", ""))
                if parsed and isinstance(parsed, dict) and "verified" in parsed:
                    # If all tool operations succeeded, ensure overall verified status aligns
                    if all_passed and not parsed.get("unverified_items") and parsed.get("confidence", 0) > 0.5:
                        parsed["verified"] = True
                    elif all_passed and parsed.get("verified") is not False:
                        parsed["verified"] = True
                    return parsed

        return {
            "verified": all_passed,
            "confidence": 0.95 if all_passed else 0.4,
            "evidence_summary": f"Executed {len(evidence)} tool step(s). Verified {len(successful_steps)} successful real outputs.",
            "unverified_items": [] if all_passed else ["One or more tool steps reported failure or truncation"],
            "final_conclusion": f"Task successfully completed with {len(successful_steps)} validated tool execution outputs."
        }
