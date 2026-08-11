from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "agent-windows" / "modules" / "EitasAdCheck.ps1"
RUNNER_PATH = ROOT / "agent-windows" / "Run-AdCheckWorker.ps1"


EXPECTED_FUNCTIONS = {
    "Invoke-EitasApi",
    "Send-AdCheckJobResult",
    "Claim-AdCheckJob",
    "Get-PendingAdCheckJobs",
    "Add-AdCheckOutputLine",
    "Get-EitasObjectValue",
    "Escape-AdFilterValue",
    "Test-EitasAdCheckSimulation",
    "Invoke-EitasAdCheckJob",
    "Process-PendingAdCheckJobs",
}


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def function_names(source: str) -> set[str]:
    return set(
        re.findall(
            r"(?mi)^function[ \t]+([A-Za-z0-9_-]+)[ \t]*\{",
            source,
        )
    )


def test_ad_check_module_is_packaged():
    assert MODULE_PATH.is_file(), (
        "Run-AdCheckWorker.ps1 depends on modules/EitasAdCheck.ps1, "
        "but the module is missing from the repository worktree"
    )


def test_ad_check_runner_loads_packaged_module():
    runner = read_source(RUNNER_PATH)
    assert ". (Join-Path $Root \"modules\\EitasAdCheck.ps1\")" in runner
    assert "Process-PendingAdCheckJobs" in runner


def test_ad_check_module_exposes_worker_contract():
    module = read_source(MODULE_PATH)
    names = function_names(module)
    assert EXPECTED_FUNCTIONS <= names


def test_ad_check_api_wrapper_delegates_to_shared_api_module():
    module = read_source(MODULE_PATH)
    assert "function Invoke-EitasApi {" in module
    assert (
        "return Invoke-EitasApiRequest -Method $Method -Path $Path "
        "-Body $Body -Config $Config"
    ) in module
    assert "# STEP162_AD_CHECK_FUNCTIONS_END" in module
