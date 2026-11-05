# Remote delivery evidence

- [Green development CI](https://github.com/Jibran3134/Rahbar/actions/runs/42046219261): required verification passed after a transient upstream tool-download retry.
- [Actual failing regression run](https://github.com/Jibran3134/Rahbar/actions/runs/42046173348): live fixture retrieval under the deliberately incorrect .99 relevance floor produced recall@5=0. The evaluator rejected both the recall regression and undefined citation validity, returning exit 1. All preceding checks passed.
- [PR #1](https://github.com/Jibran3134/Rahbar/pull/1): pr-blocked-red.json records BLOCKED while this required evaluation failed. No bad merge was attempted.

red-e2e contains original uploaded runner evidence; remote-red-eval.log is the actual failed job log. The fixture baseline and questions were unchanged. The correction restores the existing validated .65 floor. Initial release-download HTTP 504 failures are retained separately and are not evaluation proof.

protection-current.json records seven strict GitHub Actions checks bound to app 15368 with admin enforcement and zero required approvals, per Jibran's explicit instruction. The assignment's independent-approval criterion remains unmet. API snapshots are not UI screenshots. GitHub secret names were verified present; no secret values were read.
