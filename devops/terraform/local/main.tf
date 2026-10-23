terraform {
  required_version = "= 1.17.0"
}

variable "namespace" {
  description = "Local exercise namespace; no namespace is provisioned."
  type        = string
  default     = "supersports"
  validation {
    condition     = length(var.namespace) <= 63 && can(regex("^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", var.namespace))
    error_message = "Use a Kubernetes DNS label of at most 63 characters."
  }
}

variable "deployment_target" {
  description = "Desired local or self-hosted target, recorded only."
  type        = string
  default     = "kind"
  validation {
    condition     = contains(["kind", "self-hosted"], var.deployment_target)
    error_message = "Only kind and self-hosted targets belong to this local skeleton."
  }
}

locals {
  desired_spec = {
    namespace            = var.namespace
    target               = var.deployment_target
    chart                = "devops/helm/supersports"
    kind_config          = "devops/kubernetes/kind.yaml"
    public_issuer        = "http://localhost:8180/realms/supersports"
    provisioning_enabled = false
    memory_limits_mib = {
      postgres      = 384
      identity      = 768
      catalog       = 512
      configuration = 512
    }
  }
}

# Built-in state record only: no provider, provisioner, Docker or Kubernetes calls.
resource "terraform_data" "desired_spec" {
  input = local.desired_spec
}

output "desired_deployment" {
  description = "Desired specification only; apply records local state, it creates no infrastructure."
  value       = terraform_data.desired_spec.output
}
