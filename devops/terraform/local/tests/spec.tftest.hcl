run "local_spec" {
  command = plan

  assert {
    condition     = terraform_data.desired_spec.input.provisioning_enabled == false
    error_message = "This skeleton must not claim provisioning."
  }
}

run "reject_cloud" {
  command = plan
  variables {
    deployment_target = "cloud"
  }
  expect_failures = [var.deployment_target]
}

run "reject_invalid_namespace" {
  command = plan
  variables {
    namespace = "invalid_namespace"
  }
  expect_failures = [var.namespace]
}
