# Submission: Jibran and Alishba

The assignment is due **8 November 2026 at 23:59 PKT**. Submit one team entry on Google Classroom. The agent has not submitted it.

| Required item | Link |
| --- | --- |
| Public GitHub repository | [Jibran3134/Rahbar](https://github.com/Jibran3134/Rahbar) |
| CD: verification, publication and ephemeral deployment | [Release run 42090196319](https://github.com/Jibran3134/Rahbar/actions/runs/42090196319) |
| API image SHA tag | [Docker Hub API tags](https://hub.docker.com/r/jibran3134/rahbar-api/tags?name=47fdad99c57f5bddf437bcf318fe1eaee22e1763) |
| Indexer image SHA tag | [Docker Hub indexer tags](https://hub.docker.com/r/jibran3134/rahbar-indexer/tags?name=47fdad99c57f5bddf437bcf318fe1eaee22e1763) |
| UI image SHA tag | [Docker Hub UI tags](https://hub.docker.com/r/jibran3134/rahbar-ui/tags?name=47fdad99c57f5bddf437bcf318fe1eaee22e1763) |
| Real-corpus evaluation | [Results](../eval/results.json), [baseline](../eval/baseline.json) |

Release commit: `47fdad99c57f5bddf437bcf318fe1eaee22e1763`. CD run 42090196319 completed successfully, including required verification, publication of the exact scanned images, pulling those images, rollout, Ingress smoke and fixture evaluation. All three fixture gate metrics were 1.0 with zero execution errors. Subsequent documentation commits do not change the runtime implementation of that release.

[PR #1](https://github.com/Jibran3134/Rahbar/pull/1) demonstrates an actual [failing evaluation](https://github.com/Jibran3134/Rahbar/actions/runs/42046173348) and [corrected green CI](https://github.com/Jibran3134/Rahbar/actions/runs/42088730566). Required CI blocked the regression; the same questions and baseline were preserved. See [remote evidence](evidence/platform/P05/README.md) for original artifacts, registry digests and public workflow screenshots.

The hosted CD cluster is temporary and uses real fixture retrieval with deterministic stub generation. It is not a permanent public hosting URL. The real-corpus deployment uses local minikube and Ollama; follow [README](../README.md) for Windows startup and Ingress access. Real returned-evidence recall@5 is .933333, citation integrity and required abstentions are 1; these scores do not certify every answer's semantic completeness.

Before submission, Jibran and Alishba should review the generated code, reproduce key behaviors and be able to explain the recorded decisions. No human review or Alishba-authored commits are fabricated. At Jibran's direction GitHub requires zero approvals, so the assignment's one-independent-approval criterion remains unmet. The actual failed/green workflow screenshots and blocked-PR API snapshot are present; an authenticated screenshot of the greyed-out merge button and protection settings was not captured.
