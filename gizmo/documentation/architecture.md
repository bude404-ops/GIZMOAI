# GIZMO Architecture

GIZMO is organized as modular systems, not independent chatbots.

## Bootstrap systems implemented

1. Reaper Core / Executive Orchestrator — `gizmo/orchestrator`
2. 27 Core AI Agents — `gizmo/agents`
3. Agent Factory — `gizmo/agent_factory`
4. Task and Planning Engine — `gizmo/tasks`
5. Agent Communication System — `gizmo/communication`
6. Individual Agent Memory — `gizmo/memory`
7. Shared Organizational Memory — `gizmo/memory`
8. Project Memory — `gizmo/memory`
9. Knowledge/Research System — reserved module
10. Tool Registry — `gizmo/tools`
11. GitHub Integration — planned next expansion; repo remains source of truth
12. Autonomous Execution Engine — bootstrap orchestrator loop
13. Sandbox System — reserved runtime boundary and factory sandbox policy
14. Testing and QA System — pytest + self-test
15. Security System — policy gates + emergency stop
16. Evolution/Learning Engine — memory-backed lessons and factory proposals
17. Cost and Resource Manager — operation counter and limits
18. Artifact Management System — generated project artifacts
19. Project Generator — harmless web app generator
20. Unreal Engine Automation Layer — capability detection
21. Monitoring and Logging — structured audit log
22. Human Control System — operating modes and approval gates

## Decision loop

Understand objective → retrieve memory → plan tasks → assign agents → execute allowed work → test/review → store lessons → determine next action.

## Safety

Production/destructive actions are approval-gated. Emergency mode stops autonomous operation.
