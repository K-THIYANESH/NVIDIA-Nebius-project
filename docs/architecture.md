# Architecture & System Design
## Guardian Swarm — Controlled Agent Execution • Evidence • Verification

Guardian Swarm provides a production-grade, zero-trust autonomous agent operations runtime. It ensures that language models cannot execute tools without prior schema validation, multi-gate authorization, path confinement, and tamper-evident SHA-256 cryptographic logging.

```mermaid
graph TD
    User([User / Enterprise Identity]) --> API[Flask / REST & SSE Engine]
    API --> Planner[NVIDIA Nemotron Planner via Nebius]
    Planner -->|Structured Execution Plan| Loop[Safe Bounded Loop]
    
    subgraph MultiGate["5-Gate Enterprise Governance Pipeline"]
        G1[Gate 1: User RBAC Matrix]
        G2[Gate 2: Model Group Confinement]
        G3[Gate 3: Privacy & PII Scanner]
        G4[Gate 4: Token Budget & Quota Gate]
        G5[Gate 5: AI Safety & Debate Arbiter]
    end

    Loop -->|Action Proposal| MultiGate
    MultiGate -->|Denied / Blocked| Escalation[Escalation Queue / Audit Ledger]
    MultiGate -->|Authorized| ToolReg[Constrained Tool Registry]
    
    subgraph Tools["Real Tool Execution Layer"]
        T1[search_web]
        T2[read_file - Path Confined]
        T3[write_file - Artifacts Confined]
        T4[query_db - Parameterized]
        T5[extract_text - FileMind Parser]
    end

    ToolReg --> Tools
    Tools -->|Real Output Evidence| Observe[Observation & Evidence Collector]
    Observe --> Verifier[NVIDIA Nemotron Verifier via Nebius]
    Verifier -->|Objective Evaluation| Conclusion[Verified Final Outcome]
    Conclusion --> Ledger[(SHA-256 Cryptographic Audit Ledger)]
```

### Core Product Loop
1. **Understand:** User task description and context are ingested and classified.
2. **Plan:** NVIDIA Nemotron on Nebius Token Factory outputs a structured execution plan.
3. **Authorize:** The proposed tool, target, and arguments are independently validated against the 5-Gate Governance Pipeline.
4. **Execute:** The tool is invoked strictly within authorized project sandboxes (`artifacts/`, `data/`).
5. **Observe:** Real system output, byte counts, and return values are recorded.
6. **Verify:** Evidence is verified against the original objective.
7. **Conclude:** Final findings are summarized and sealed in the SHA-256 audit ledger.
