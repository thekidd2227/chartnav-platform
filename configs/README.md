# IBM Cloud Projects configuration folder

This folder holds **IBM Cloud Projects** configuration JSON files
that are PATCHed by the GitHub Actions workflow
`.github/workflows/ibm-projects-config-update.yml` after a pull
request is merged into `main`.

**Scope clarification — read this first.** This folder is for the
**IBM Cloud Projects** service (`projects.api.cloud.ibm.com`),
which is a deployment / IaC orchestration product. It is **not**
the same as **watsonx.ai inference**
(`us-south.ml.cloud.ibm.com/ml/v1/...`). The two services use
different "project" concepts; project IDs are not
interchangeable. See
`docs/integrations/ibm-cloud-projects-git-integration.md` for
the full distinction and the current watsonx-inference blocker.

## Hard rules — what may live in this folder

- ✅ IBM Cloud Projects config JSON files keyed by `project_id`,
  `config_id`, and a `definition` block.
- ✅ Placeholder template files with the `.template.json` suffix.
  The workflow ignores them by suffix.
- ✅ Markdown documentation like this README.

## Hard rules — what may **NOT** live in this folder

- ❌ **Secrets of any kind.** No API keys, no bearer tokens, no
  service credentials, no passwords, no JWT private keys.
- ❌ **PHI of any kind.** No real patient names, DOBs, MRNs,
  phone numbers, addresses, or any other identifier defined by
  HIPAA's 18 PHI identifiers.
- ❌ **Real IBM Cloud project IDs** in any file with the
  `.template.json` suffix. Templates use the literal placeholder
  string `replace-with-…`.
- ❌ **IAM bearer tokens** (short-lived watsonx / IBM Cloud
  tokens). The workflow exchanges the API key for a bearer at
  runtime; bearers never live on disk.
- ❌ **Production deploy approval.** This workflow does not deploy
  ChartNav production code. It only PATCHes IBM Cloud Projects
  configs.

## Required repo settings

The workflow refuses to start unless these are configured under
GitHub repo Settings → Secrets and variables → Actions.

| Kind | Name | Example |
|---|---|---|
| Secret | `IBM_CLOUD_API_KEY` | A long-lived IBM Cloud IAM API key with **only** the permissions needed for IBM Cloud Projects PATCH operations. **Never** an account-owner key. |
| Variable | `CONFIG_FOLDER_PATH` | `configs` |
| Variable | `IAM_URL` | `https://iam.cloud.ibm.com` |
| Variable | `PROJECTS_API_BASE_URL` | `https://projects.api.cloud.ibm.com` |

## File shape

A non-template config file must be valid JSON with **at minimum**
these three top-level keys:

```json
{
  "project_id": "<UUID issued by IBM Cloud Projects>",
  "config_id":  "<UUID issued by IBM Cloud Projects>",
  "definition": { "...": "service-specific body" }
}
```

The workflow reads `project_id` + `config_id` to assemble the
PATCH URL, then sends `{"definition": <definition>}` as the body.

## File-naming convention

- `*.template.json` — placeholder; never PATCHed. Used in this
  folder to document the expected shape.
- `<descriptive-name>.json` — real config; PATCHed on merge if the
  file changes in that PR.

## Audit hygiene

- Every PR that adds or modifies a file under `configs/`
  triggers the workflow on merge. Inspect the GitHub Actions log
  for `Project ID` + `Config ID` lines that match what you
  expected to change.
- If a config file is removed in a PR, the workflow does not
  delete it from IBM Cloud Projects. Deletion is a manual IBM
  Console operation by design.

## Related docs

- `docs/integrations/ibm-cloud-projects-git-integration.md`
- `docs/security/chartnav-llm-vendor-evaluation.md`
- `docs/security/chartnav-ibm-watsonx-vendor-readiness.md`
