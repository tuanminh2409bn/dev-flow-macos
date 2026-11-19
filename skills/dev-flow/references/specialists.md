# Optional specialist routing

Read only when the task has a gap this workflow cannot resolve. Use available skills by capability; installation is not required for ordinary development.

Prefer zero or one specialist for standard work. Add more only for distinct unresolved risks; do not follow an entire lifecycle merely because a file changed. Read a chosen skill once, and load its references only when relevant.

| Concrete need | Specialist |
| --- | --- |
| Material ambiguity in desired behavior | `interview-me` or `spec-driven-development` |
| Large accepted scope needing ordered slices | `planning-and-task-breakdown` or `incremental-implementation` |
| Complex test design or regression boundary | `test-driven-development` |
| Failure still unexplained after a focused reproduction | `debugging-and-error-recovery` |
| Public API/module contract design | `api-and-interface-design` |
| Substantial web UI implementation | `frontend-ui-engineering` |
| WCAG 2.2 AA audit or remediation of existing web UI | `accessibility-engineering` |
| Browser evidence needed | `browser-testing-with-devtools` if its tooling is available; otherwise use available browser tools |
| Auth, trust-boundary, or dependency-security risk | `security-and-hardening` |
| Measured performance bottleneck | `performance-optimization` |
| Uncertain version-sensitive integration | `source-driven-development` |
| Requested review or simplification | `code-review-and-quality` or `code-simplification` |
| Requested adversarial review of a critical decision | `doubt-driven-development`, subject to delegation authorization |
| CI, migration, observability, docs, Git, or release outcome | Matching specialist only |

Do not automatically spawn reviewers, create specs/ADRs, introduce coverage thresholds, or request a different model. Such work needs a concrete task or risk justification and existing authority. Preserve repository quality gates even when they are more demanding than this default workflow.
