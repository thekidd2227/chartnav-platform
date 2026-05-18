# IBM Cloud Projects — Git integration

> **Status:** Pipeline-only integration. **No product behavior
> change.** No LLM call. No real PHI. No production deploy.
> ChartNav is not "IBM-powered" or "watsonx-powered." IBM does
> not make ChartNav HIPAA compliant.
>
> **Type:** GitHub Actions workflow + config folder convention.
> Read with `docs/security/chartnav-ibm-watsonx-vendor-readiness.md`
> and `docs/security/chartnav-llm-vendor-evaluation.md`.

---

## 1. What this integration does

When a pull request is merged into `main`, the workflow
`.github/workflows/ibm-projects-config-update.yml`:

1. Exchanges the GitHub-secret IBM Cloud IAM API key for a
   short-lived IAM bearer token at
   `https://iam.cloud.ibm.com/identity/token`.
2. Computes the set of files changed in that PR's merge commit.
3. For each changed `*.json` file under `configs/` (skipping
   `*.template.json` placeholders), reads
   `{project_id, config_id, definition}`, and PATCHes the
   matching IBM Cloud Projects configuration at
   `https://projects.api.cloud.ibm.com/v1/projects/<id>/configs/<id>`.
4. Also exposed as `workflow_dispatch` for ad-hoc manual runs.

The workflow is **declarative**: the repo is the source of truth
for IBM Cloud Projects config bodies; merging to `main` is the
deploy event.

## 2. What this integration does **not** do

- ❌ Does **not** call watsonx.ai inference, Watson Machine
  Learning, watsonx.governance, or any model-inference endpoint.
- ❌ Does **not** deploy ChartNav application code. ChartNav's
  application deploy pipeline is unchanged.
- ❌ Does **not** process real PHI. The workflow's payloads are
  whatever you committed to `configs/`; that folder's README
  forbids PHI by policy.
- ❌ Does **not** mint, store, or echo long-lived secrets. The IAM
  API key lives in GitHub Secrets only; the bearer token is
  short-lived, masked via `::add-mask::`, and never persisted.
- ❌ Does **not** make any public claim that ChartNav is
  "IBM-powered" or that IBM/watsonx makes ChartNav HIPAA
  compliant. ChartNav is not HIPAA-certified.

## 3. Required GitHub secret

| Name | Type | Purpose |
|---|---|---|
| `IBM_CLOUD_API_KEY` | secret | IAM API key used to mint short-lived bearer tokens. Scope it to the minimum permissions needed for IBM Cloud Projects PATCH operations. **Do not** use an account-owner key. |

Set it under **Repo → Settings → Secrets and variables → Actions
→ New repository secret**.

## 4. Required GitHub variables

| Name | Value |
|---|---|
| `CONFIG_FOLDER_PATH` | `configs` |
| `IAM_URL` | `https://iam.cloud.ibm.com` |
| `PROJECTS_API_BASE_URL` | `https://projects.api.cloud.ibm.com` |

Set under **Repo → Settings → Secrets and variables → Actions →
Variables tab**. These are non-secret defaults; they live in the
repo settings (not the YAML) so an operator can pivot region or
endpoint without a code change.

## 5. Required repo path

```
configs/
├── README.md                              # policy + shape
├── example-project-config.template.json   # placeholder; skipped
└── <your-config>.json                     # patched on merge
```

`configs/README.md` documents the file contract and forbids
secrets / PHI in this folder.

## 6. PR-merge behavior

| Event | Workflow runs? |
|---|---|
| PR opened against `main` | No |
| PR updated against `main` | No |
| PR closed without merge | No |
| PR closed **and merged** into `main` | **Yes** |
| `workflow_dispatch` (manual) | Yes |

The `if:` guard at the top of the job double-checks
`github.event.pull_request.merged == true` because GitHub fires
the `closed` event for both merged and unmerged closes.

## 7. Manual `workflow_dispatch`

Use **Repo → Actions → IBM Projects Git Integration → Run
workflow** for ad-hoc syncs (e.g. after manual edits via the IBM
Console that need to be reconciled). The workflow uses the same
"changed since previous commit" diff, so it only PATCHes files
that have changed in the last commit on `main`.

## 8. Secret-handling rules

- IBM Cloud API key lives **only** in GitHub Secrets — never in
  any file under `configs/`, never in the workflow YAML, never
  echoed.
- Bearer tokens are short-lived. The workflow registers the
  bearer with `::add-mask::` after exchange so any subsequent
  log line that contains it is auto-redacted by GitHub.
- The IAM-token-exchange response body is **never echoed** on
  failure. The workflow emits a generic "Failed to obtain IBM
  IAM token (response body redacted)" message.

## 9. PHI policy

`configs/` is not an appropriate place to store any data subject
to HIPAA's 18 PHI identifiers. The README in that folder
enumerates the policy. The workflow does not enforce a runtime
PHI scanner — repo authors are accountable for keeping
`configs/` PHI-free, same as any other source-controlled file.

## 10. IBM Cloud Projects vs watsonx.ai inference

This is the most common source of confusion. They are different
IBM services with different "project" concepts.

| Aspect | IBM Cloud Projects | watsonx.ai inference |
|---|---|---|
| Purpose | Deployment / IaC orchestration of cloud-resource bundles | Foundation-model inference (text generation, chat, embeddings) |
| API host | `projects.api.cloud.ibm.com` | `<region>.ml.cloud.ibm.com` (e.g. `us-south.ml.cloud.ibm.com`) |
| "Project" concept | A project that wraps configs for a deployable architecture | A watsonx.ai project that wraps a runtime, a Watson Machine Learning service instance, model access, and collaborators |
| Auth | IAM API key → IAM bearer | IAM API key → IAM bearer (same exchange) |
| Project ID shape | UUID | UUID (different ID space) |
| GitHub workflow scope | **This workflow.** | Out-of-tree dev script (`~/dev_live_watsonx_eval.py`); not part of any GitHub-Actions deploy. |

**Project IDs are not interchangeable across these services.** A
UUID issued by IBM Cloud Projects will not be recognized by the
watsonx.ai inference endpoint, and vice versa.

## 11. Current watsonx-inference blocker (unresolved)

The first live-call watsonx.ai eval (per
`docs/security/chartnav-llm-fake-data-evaluation-plan.md`) used
fixture F1 and reached the following state:

| Stage | Result |
|---|---|
| IAM token exchange | ✅ success |
| Inference call to `us-south.ml.cloud.ibm.com/ml/v1/text/generation` | ❌ 4xx — `container_not_found` |
| Error body | `Failed to find project_id c0bd6320-1b19-4538-a467-b948de3d8474` |
| Local script classification | `project_id` |

What is **not** yet determined and must be resolved manually
before any further IBM watsonx eval attempt:

1. Whether the UUID used (`c0bd…3d8474`) is an **IBM Cloud
   Projects** project ID — which is not valid for watsonx.ai
   inference — vs. a **watsonx.ai project** ID — which is what
   the inference endpoint expects.
2. Whether the watsonx.ai project has an associated **runtime**
   (the watsonx Console lets you create a project without
   binding it to a runtime; that project then has no inference
   container).
3. Whether the watsonx.ai project is bound to a **Watson Machine
   Learning service instance in the same region**
   (`us-south`). If WML is in `eu-de` but the inference call
   goes to `us-south`, the endpoint cannot find the container.
4. Whether the API-key identity (the user/serviceID that issued
   `CHARTNAV_WATSONX_API_KEY`) is a **collaborator** on the
   watsonx.ai project. Project-level access is enforced
   separately from account-level access.
5. Whether the chosen model id (default
   `ibm/granite-3-8b-instruct`) is **available in the watsonx.ai
   project's region + plan**. Some Granite variants are
   region-restricted or plan-restricted.

Until those five items are verified, no further live watsonx
inference attempts should run. The deterministic stub remains
the default; OpenAI and Anthropic pass the same F1 rubric.

## 12. Public-claim discipline

No marketing or public-facing artifact may describe ChartNav as:

- ❌ "IBM-powered"
- ❌ "watsonx-powered clinical documentation"
- ❌ "IBM makes ChartNav HIPAA compliant"
- ❌ "watsonx makes ChartNav compliant"
- ❌ "autonomous documentation"
- ❌ "automatic diagnosis"
- ❌ "production PHI-ready"
- ❌ "certified EHR"

These phrases are enforced by
`scripts/check_commercial_claims.sh`,
`scripts/check_website_claims.sh`, and
`scripts/check_demo_claims.sh` (per PR #48 + PR #49). The IBM
Cloud Projects Git integration **does not move ChartNav any
closer to a vendor-powered claim**; it is pipeline-only.

---

## Related documents

- `configs/README.md`
- `docs/security/chartnav-ibm-watsonx-vendor-readiness.md`
- `docs/security/chartnav-llm-vendor-evaluation.md`
- `docs/security/chartnav-llm-fake-data-evaluation-plan.md`
- `docs/security/chartnav-real-phi-go-live-gate.md`
