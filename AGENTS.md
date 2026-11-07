# Development and delivery

Use a separate topic branch for each logical change. Name branches
`fix/<short-kebab-case-description>`, `feat/<description>`,
`docs/<description>` or `chore/<description>` as appropriate.

Implement and test the change, commit it, and push the topic branch. Open a pull
request from the topic branch into `dev`. After the automated checks pass, merge
it without waiting for teammate approval. Then open a pull request from `dev`
into `main`, wait for the required automated checks, and merge it. Do not push
development commits directly to `main` or bypass its required checks.

Jibran explicitly requested this topic -> dev -> main workflow and zero required
teammate approvals on 7 November 2026. Keep the automated CI/CD gates. Use merge
commits for promotion to preserve ancestry; do not force-push shared branches or
delete other people's work. Report the actual branch, PRs, checks and merge results.
