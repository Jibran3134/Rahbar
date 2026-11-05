# Alishba: platform implementation ledger

Jibran authorized implementation of Alishba's scope on 5 November 2026 and continued local commits directly on main. This supersedes the earlier file-ownership restriction for this work. Codex is implementing and testing these changes; Alishba's authorship or human review is not claimed. No remote push, publishing or account changes are implied by local commits.

| Stage | Scope | Status | Evidence |
| --- | --- | --- | --- |
| P01 | Non-root images, runtime/OCR checks, UI shared sessions | PASS | P01/container-smoke.json; images.json; node UI test |
| P02 | Kustomize and isolated real-corpus minikube deployment | PASS; failure/network experiments continue in P04 | P02 Ingress, Job, endpoints/HPA and cgroup evidence |
| P03 | CI/CD, security remediation and real fixture cluster | Local PASS; remote release pending | P03/summary.json, scans, coverage and e2e |
| P04 | Network/recovery/mismatch/reindex/real eval/rollout/docs | Local PASS including fresh source; remote release pending | P04/acceptance.json, real-results.json, rollout-rollback.json, live-eval-gate.json |

Existing context k3d-civicpulse-ci and unrelated Docker workloads must remain untouched. Rahbar cluster operations use an explicit separate context/profile. Native application services and data remain separate from cluster state.


## Current platform handoff

Docker Hub account metadata identified jibran3134, which Jibran requested using. GitHub publishing secrets are not configured; no token was read or displayed and nothing was pushed/published. P01 committed 9879bd5, P02 1835903 and P03 ef57ee9 on main. Local fixture and real Ingress gates passed. User-requested main commits do not establish protected remote delivery. Account gates still require actual protection/PR/approval, failed-and-corrected eval PR proof, registry credentials and SHA publication/CD links. No authorship or human review by Alishba is fabricated.

Default-context monitoring found rahbar selected after local tooling recovery; the originally observed k3d-civicpulse-ci context was restored, and Windows cluster/image helpers now save/restore their starting context. No CivicPulse resource operation was performed. CI uses its own kubeconfig. Initial script/import, PowerShell argument, cold-pull, startup and Ingress-propagation failures are retained with their corrections.


Final fresh-source verification of 756304d216fd16a32fbd7b123c40a87184c549ae passed 301 pytest cases, UI tests, both mypy checks, Ruff, manifest/config invariants, actionlint and dependency consistency. The latest unchanged submission checker reports 163 passes, seven warnings, zero failures. Final development images use platform-p04; runtime/readiness/image IDs are in P04/final-state.json, with the API/indexer root filesystem layers matching the scan-passing images. A local dev branch was prepared without switching off main. Remaining work requires actual remote release authorization/credentials and human protected-review/merge evidence.


## P05 remote delivery authorization and protection

Jibran approved pushing review branches, configuring protection, creating regression/fix PRs and publishing SHA-tagged Docker Hub/CD releases. The tested code was pushed to dev; PR #1 uses a separate evidence/eval-gate worktree/branch with a deliberate CI-only floor .99 regression. Working main keeps the valid .65 fixture configuration. GitHub Actions' actual check contexts were bound to app ID 15368. After Jibran explicitly said not to require approval, protection retains PRs/required CI/admin enforcement but uses zero required approvals. No independent approval is fabricated; the assignment's one-approval criterion is unmet by user choice.

DOCKERHUB_USERNAME=jibran3134 is configured; Jibran was given official instructions to create a Repo Read & Write token and add DOCKERHUB_TOKEN privately. No token was requested in chat. Initial remote failures were release-asset HTTP 504s before scan/schema checks, not accepted evidence of evaluation regression. Bounded retry logic was added and four targeted tests passed, bringing pytest total to 305. Original remote failure logs are preserved.


P05 actual remote gate proof: dev CI run 42046219261 is green. PR #1 run 42046173348 reached the live fixture evaluator and failed with recall@5=0, citation_validity undefined and exit 1 under the deliberate .99 floor; all preceding lint/test/manifests/build/scan jobs passed. The PR reported BLOCKED with zero required approvals, proving CI enforcement rather than a review requirement. Logs, actual fixture responses and API snapshots are retained in platform/P05. DOCKERHUB_TOKEN and DOCKERHUB_USERNAME are now present in Actions; only secret names were checked. Registry authentication remains unverified until the publish job. Restore .65 on the same PR without changing golden questions/baseline, then require a green run before merge.
