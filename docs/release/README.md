# ChartNav Release Evidence

Use `docs/release/release-evidence-checklist.md` for every production, controlled-pilot, buyer-demo, or security-sensitive release.

The checklist is not a compliance certification. It is an operator record that captures what was tested, what was intentionally not changed, what risks remain, and who made the go/no-go decision.

Use it when a PR touches:

- clinical workflow behavior;
- auth, RBAC, org scoping, or audit behavior;
- runtime configuration;
- LLM/STT/vendor seams;
- demo reset scripts or demo runbooks;
- public/commercial/website claims;
- migrations, backups, restore, or deploy scripts.

Store completed copies with release artifacts or link them from the PR.
