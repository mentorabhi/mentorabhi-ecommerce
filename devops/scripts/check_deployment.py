"""Validate alternate deployment artifacts without deploying a cluster."""
import json
from manage import ROOT, run

FIXTURES = [
    "--set", "existingSecret=fixture-secret",
    "--set", "bootstrap.postgresExistingConfigMap=fixture-init",
    "--set", "bootstrap.realmExistingConfigMap=fixture-realm",
]


def expect_rejection(command, markers):
    result = run(command, capture=True, check=False)
    output = result.stdout + result.stderr
    if result.returncode == 0 or not all(marker in output for marker in markers):
        raise RuntimeError("Negative deployment validation did not fail for its intended constraint.")


def main():
    lock = json.loads((ROOT / "devops/images.lock.json").read_text())
    helm = [
        "docker", "run", "--rm", "--mount",
        f"type=bind,source={ROOT / 'devops/helm'},target=/charts,readonly",
        lock["HELM_IMAGE"],
    ]
    run([*helm, "lint", "/charts/supersports", *FIXTURES])
    render = run([*helm, "template", "exercise", "/charts/supersports",
                  "--namespace", "alternate", *FIXTURES], capture=True)
    if "kind: Secret" in render.stdout:
        raise RuntimeError("The chart must reference external secrets, not render secret material.")
    expect_rejection([*helm, "lint", "/charts/supersports"],
                     ["existingSecret", "postgresExistingConfigMap", "realmExistingConfigMap"])
    expect_rejection([*helm, "template", "exercise", "/charts/supersports", *FIXTURES,
                      "--set", "apps.catalog.imagePullPolicy=Always"], ["imagePullPolicy"])
    print("PASS: Helm lint/render and intended negative constraints")
    terraform = [
        "docker", "run", "--rm", "--mount",
        f"type=bind,source={ROOT / 'devops/terraform/local'},target=/workspace",
        "--workdir", "/workspace", lock["TERRAFORM_IMAGE"],
    ]
    for arguments in (["fmt", "-check"], ["init", "-backend=false", "-input=false", "-no-color"],
                      ["validate", "-no-color"], ["test", "-no-color"]):
        run([*terraform, *arguments])
    print("PASS: Terraform fmt/init/validate/native tests; no cloud provisioning")


if __name__ == "__main__":
    main()
