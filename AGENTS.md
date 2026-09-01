# WBrain Agent Instructions

This file applies to all work in this repository.

## Source of engineering skills

Use the production engineering skill pack from:

- Repository: `https://github.com/addyosmani/agent-skills`
- License: MIT
- Skill source: `skills/<skill-name>/SKILL.md`
- Reference checklists: `references/`

The project uses the full lifecycle pack. When a task matches a skill below, the agent MUST follow that skill's workflow and verification gates. Do not paste or duplicate full skill files into this document; load the relevant `SKILL.md` from the pinned/local skill installation when executing the workflow.

## Complete skill catalog

### Meta

- `using-agent-skills` — map incoming work to the correct skill and shared operating rules.

### Define

- `interview-me` — one-question-at-a-time requirements clarification.
- `idea-refine` — turn a rough idea into a concrete proposal.
- `spec-driven-development` — write a product specification before significant implementation.
- `constraint-driven-development` — establish quality thresholds and enforceable constraints.

### Plan

- `planning-and-task-breakdown` — create small, ordered, independently verifiable tasks.

### Build

- `incremental-implementation` — implement thin vertical slices with safe checkpoints.
- `test-driven-development` — use red-green-refactor and the test pyramid.
- `context-engineering` — provide agents with the right scoped context and rules.
- `source-driven-development` — ground framework/API decisions in authoritative sources.
- `doubt-driven-development` — adversarially verify high-risk decisions.
- `frontend-ui-engineering` — build responsive, accessible, maintainable UI.
- `api-and-interface-design` — design stable contracts, boundaries, and error semantics.

### Verify

- `browser-testing-with-devtools` — inspect live DOM, console, network, and performance behavior.
- `debugging-and-error-recovery` — reproduce, localize, reduce, fix, and guard regressions.

### Review

- `code-review-and-quality` — review correctness, maintainability, security, tests, and change size.
- `code-simplification` — simplify without changing behavior.
- `security-and-hardening` — apply OWASP, secrets, auth, input, dependency, and boundary controls.
- `performance-optimization` — measure before optimizing and verify regressions.

### Ship

- `git-workflow-and-versioning` — use atomic commits, semantic versions, and safe history practices.
- `ci-cd-and-automation` — add quality gates, automation, and failure feedback.
- `deprecation-and-migration` — plan compatibility, migration, and removal of old behavior.
- `documentation-and-adrs` — record decisions, API behavior, and operational rationale.
- `observability-and-instrumentation` — use structured logs, RED metrics, tracing, and alerts.
- `shipping-and-launch` — use rollout, monitoring, rollback, and launch checklists.

## Specialist personas

Use the following perspectives for high-risk or review tasks:

- `code-reviewer` — senior staff engineering review.
- `test-engineer` — QA strategy and coverage review.
- `security-auditor` — threat model, vulnerability, and hardening review.
- `web-performance-auditor` — browser performance audit.

## Automatic skill selection

Before implementation, run `using-agent-skills` mentally or explicitly and select the smallest complete set:

| Work type | Required skills |
|---|---|
| New feature or vague requirement | `using-agent-skills`, `spec-driven-development`, `planning-and-task-breakdown` |
| Multi-file implementation | `incremental-implementation`, `test-driven-development` |
| API or schema change | `api-and-interface-design`, `source-driven-development` |
| Web UI/camera/browser change | `frontend-ui-engineering`, `browser-testing-with-devtools` |
| Production/security/license/model protection | `security-and-hardening`, `doubt-driven-development`, `documentation-and-adrs` |
| Performance/real-time inference | `performance-optimization`, `observability-and-instrumentation` |
| Failed test or runtime error | `debugging-and-error-recovery`, `test-driven-development` |
| Before merge or push | `code-review-and-quality`, `code-simplification`, `git-workflow-and-versioning` |
| Release/deployment/versioning | `ci-cd-and-automation`, `shipping-and-launch`, `git-workflow-and-versioning` |
| Breaking change or cleanup | `deprecation-and-migration`, `documentation-and-adrs` |

## Required workflow for this project

1. Read the relevant project code and current specs before editing.
2. For non-trivial work, update or create the OpenSpec change under `openspec/changes/`.
3. Separate user-facing requirements from technical design and implementation tasks.
4. Mark unstated decisions as assumptions and request review for high-impact assumptions.
5. Implement one independently verifiable vertical slice at a time.
6. Add tests before or with behavior changes; never defer all tests to the end.
7. Run focused tests first, then broader tests/builds.
8. For browser changes, verify the actual served page, browser console, and network request.
9. For security changes, test tampering, invalid credentials, expiry, rollback, and unauthorized access.
10. For release changes, verify image digest, SBOM, checksum, clean Git status, and rollback instructions.
11. Do not commit generated artifacts, model binaries, customer licenses, encryption keys, `.env` files, or Docker volumes.
12. Do not claim a model, container, test, or deployment works unless it was actually verified.

## WBrain-specific boundaries

- CPU is the default and supported inference profile.
- YOLO detector uses the exported ONNX artifact; model source/checkpoints stay outside Git.
- EditCTC `s1024` is the current recognizer checkpoint for local/on-prem testing.
- Customer release output belongs under ignored `release/`.
- Per-version release notes belong under tracked `release-notes/vX.Y.Z.md`.
- Customer-specific license/key material MUST NOT be committed or baked into generic images.
- Ed25519 is for license signatures; Fernet/AES-GCM is for artifact encryption, not authenticity.
- Never claim protection against a customer Administrator/root. Use vendor-controlled inference or confidential computing for that threat model.
- Preserve upstream Apache 2.0 and third-party license obligations for SkillHub-derived code.

## Reference checklist usage

When available, also load the matching reference from the agent-skills repository:

- `definition-of-done.md` — project completion gate.
- `testing-patterns.md` — test design and anti-patterns.
- `security-checklist.md` — security pre-commit checks.
- `performance-checklist.md` — frontend/backend performance checks.
- `accessibility-checklist.md` — WCAG and keyboard/accessibility checks.
- `observability-checklist.md` — production telemetry and on-call checks.
- `orchestration-patterns.md` — multi-persona delegation rules.

## Agent skill installation

For a local project installation, use the official command from the source repository:

```bash
npx skills add addyosmani/agent-skills
```

To inspect before installing:

```bash
npx skills add addyosmani/agent-skills --list
```

The installed skill files are the operational source. This AGENTS.md is the project-specific routing and policy layer.
