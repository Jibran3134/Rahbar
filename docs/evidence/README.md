# Evidence index

These are actual local results, not substitutes for remote account/release proof. Root-level kubectl-top.txt, api-endpoints.txt, hpa.txt and resource-measurements.json point to detailed platform measurements. app/sprints retains S00-S22 application history; platform/P01-P04 contains image, manifest, scan, CI-equivalent, network, recovery, reindex, model-mismatch, rollout and evaluator evidence. Real and fixture reports remain separate.

Still missing: actual branch-protection screenshot, genuinely blocked regression PR/merge screenshot, corrected green PR proof, registry SHA image pages and successful remote CD run URL. None is fabricated. The local live fixture regression failed as intended and passed after correction, with unchanged baseline; see platform/P04/live-eval-gate.json. The actual UI capture is platform/P04/ui.png. Human review remains pending.


Final fresh committed-source checks passed 301 tests plus UI/types/lint/config/workflow/dependency checks; see platform/P04/fresh-source. Mechanical submission check: 163 passes, seven warnings, zero failures. This does not remove the remote requirements above.
