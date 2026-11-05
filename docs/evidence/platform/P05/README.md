# Remote delivery evidence

- [Green development CI](https://github.com/Jibran3134/Rahbar/actions/runs/42046219261): required verification passed after a transient upstream tool-download retry.
- [Actual failing regression run](https://github.com/Jibran3134/Rahbar/actions/runs/42046173348): live fixture retrieval under the deliberately incorrect .99 relevance floor produced recall@5=0. The evaluator rejected both the recall regression and undefined citation validity, returning exit 1. All preceding checks passed.
- [PR #1](https://github.com/Jibran3134/Rahbar/pull/1): pr-blocked-red.json records BLOCKED while this required evaluation failed. No bad merge was attempted.

red-e2e contains original uploaded runner evidence; remote-red-eval.log is the actual failed job log. The fixture baseline and questions were unchanged. The correction restores the existing validated .65 floor. Initial release-download HTTP 504 failures are retained separately and are not evaluation proof.

protection-current.json records seven strict GitHub Actions checks bound to app 15368 with admin enforcement and zero required approvals, per Jibran's explicit instruction. The assignment's independent-approval criterion remains unmet. API snapshots are not UI screenshots. GitHub secret names were verified present; no secret values were read.


## Corrected PR and successful release

[Corrected CI 42088730566](https://github.com/Jibran3134/Rahbar/actions/runs/42088730566) passed all required checks. green-e2e contains original hosted results (recall@5, citation validity and required abstentions all 1.0; zero execution errors), with hosted API/indexer coverage 90.12%/90.26%. pr-green.json records CLEAN before merge; pr-merged.json records the actual protected merge. red-green-summary.json verifies unchanged golden/baseline hashes across the red, corrected and merged commits.

[CD 42090196319](https://github.com/Jibran3134/Rahbar/actions/runs/42090196319) succeeded for 47fdad99c57f5bddf437bcf318fe1eaee22e1763: verification -> publish exact scanned images -> pull from Docker Hub -> fresh kind rollout -> Ingress smoke -> real fixture retrieval gate. release-e2e contains original release artifacts; release-green.json records actual job conclusions. published-images.json records independently inspected registry digests. remote-red-run.png, remote-green-run.png and remote-release-run.png are actual public GitHub pages captured with a fresh anonymous browser profile. They are not authenticated merge-button/settings screenshots.

The release cluster is ephemeral and uses fixture retrieval/stub generation. Real-corpus minikube measurements remain in P04; local-after-restart files record successful recovery of the existing persisted stack and HPA after Docker restarted. [Submission links](../../../SUBMISSION.md) list registry pages and remaining human/rubric items.
