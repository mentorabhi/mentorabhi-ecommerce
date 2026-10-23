# Local desired deployment skeleton

Use Terraform 1.17.0 (BSL-1.1), verified against the official installation page on
2026-10-23: https://developer.hashicorp.com/terraform/install.
Download and verify the platform binary using upstream checksums/signature;
place it under ignored `devops/.local/bin`, never install globally for this exercise.

From the repository root:

```sh
devops/.local/bin/terraform -chdir=devops/terraform/local fmt -check -recursive
devops/.local/bin/terraform -chdir=devops/terraform/local init -backend=false
devops/.local/bin/terraform -chdir=devops/terraform/local validate
devops/.local/bin/terraform -chdir=devops/terraform/local test
devops/.local/bin/terraform -chdir=devops/terraform/local plan
```

The only resource is built-in `terraform_data`; no provider downloads, cloud,
managed resources or actual Docker/Kubernetes provisioning are implemented.
`apply` merely records the non-secret desired spec locally. The deployment itself
uses the explicit kind/kubectl/Helm steps in `docs/lessons/S1-M02.md`.
State, `.terraform/` and plans are already ignored by repository rules. Never put
passwords into variables, outputs or state. Tests cover target/namespace validation
and the non-provisioning contract; host execution is required before claiming pass.

## Containerized validation
The delivered .venv/bin/python devops/scripts/check_deployment.py runs pinned Terraform 1.17.0 and Helm 4.3.1 tool containers, so host installations are optional for validation. It initializes with -backend=false, validates and runs the three Terraform native tests. No cloud provider or infrastructure apply is executed.
