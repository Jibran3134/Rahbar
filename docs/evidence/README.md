# Evidence index

P01-P04 contain actual local results. P05 adds remote GitHub Actions and protection evidence; local results alone do not establish a release. Root-level kubectl-top.txt, api-endpoints.txt, hpa.txt and resource-measurements.json point to detailed platform measurements. app/sprints retains S00-S22 application history; platform/P01-P04 contains image, manifest, scan, CI-equivalent, network, recovery, reindex, model-mismatch, rollout and evaluator evidence. Real and fixture reports remain separate.

P05 records actual required-check protection (zero approvals at Jibran's request), a green dev CI run, and PR #1 blocked by the genuine fixture regression (recall@5=0; evaluator exit 1). API snapshots and original logs are retained. [Corrected CI](https://github.com/Jibran3134/Rahbar/actions/runs/42088730566), the protected PR merge, registry SHA publication/digests and [successful CD](https://github.com/Jibran3134/Rahbar/actions/runs/42090196319) are now recorded in P05. Original published-image fixture metrics are all 1.0 with zero execution errors. Actual public red, green and release workflow screenshots are included. Branch-protection/blocked-merge UI screenshots and an independent approval have not been captured; API evidence is not presented as a screenshot. The local live fixture regression failed as intended and passed after correction, with unchanged baseline; see platform/P04/live-eval-gate.json. The actual UI capture is platform/P04/ui.png. Human review remains pending.


Final fresh committed-source checks passed 301 tests plus UI/types/lint/config/workflow/dependency checks; see platform/P04/fresh-source. Mechanical submission check: 163 passes, seven warnings, zero failures. This does not remove the remote requirements above.


See [submission links](../SUBMISSION.md) for the release SHA and Docker Hub pages. P05 also records recovery of the local minikube/Ollama services after Docker restarted: readiness, Ingress UI and info returned 200; persistent claims remained bound; HPA CPU metrics recovered to 14%/70%; the original unrelated kube context remained selected. No new index was required.
