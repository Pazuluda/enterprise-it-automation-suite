#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

python3 - <<'PY'
from __future__ import annotations

import pathlib
import re
import subprocess
import sys


def git_bytes(*arguments: str) -> bytes:
    return subprocess.check_output(
        ["git", *arguments],
        stderr=subprocess.DEVNULL,
    )


def git_paths(*arguments: str) -> list[str]:
    output = git_bytes(*arguments)

    return [
        value.decode("utf-8", errors="surrogateescape")
        for value in output.split(b"\0")
        if value
    ]


staged_files = git_paths(
    "diff",
    "--cached",
    "--name-only",
    "--diff-filter=ACMR",
    "-z",
)

if staged_files:
    scan_mode = "index Git préparé"
    candidate_files = staged_files
else:
    scan_mode = "modifications non préparées"

    candidate_files = sorted(
        set(
            git_paths(
                "diff",
                "--name-only",
                "--diff-filter=ACMR",
                "-z",
            )
            + git_paths(
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
            )
        )
    )


tracked_files = git_paths("ls-files", "-z")

ignored_directories = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
}

allowed_environment_files = {
    ".env.example",
    ".env.sample",
    ".env.template",
}

sensitive_extensions = {
    ".key",
    ".pem",
    ".p12",
    ".pfx",
    ".jks",
    ".keystore",
}

sensitive_names = {
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "service-account.json",
}

backup_patterns = (
    re.compile(r"\.backup-", re.IGNORECASE),
    re.compile(r"\.broken-", re.IGNORECASE),
    re.compile(r"\.tmp-", re.IGNORECASE),
    re.compile(r"\.(?:bak|old|orig|swp)$", re.IGNORECASE),
    re.compile(r"~$"),
)

content_patterns = (
    (
        "clé privée",
        re.compile(
            r"-----BEGIN "
            r"(?:RSA |EC |DSA |OPENSSH )?"
            r"PRIVATE KEY-----"
        ),
    ),
    (
        "jeton JWT littéral",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}"
            r"\.[A-Za-z0-9_-]{10,}"
            r"\.[A-Za-z0-9_-]{10,}\b"
        ),
    ),
    (
        "jeton Bearer littéral",
        re.compile(
            r"\bBearer\s+"
            r"[A-Za-z0-9._~+/=-]{20,}",
            re.IGNORECASE,
        ),
    ),
    (
        "jeton GitHub",
        re.compile(
            r"\b(?:"
            r"gh[pousr]_[A-Za-z0-9]{20,}"
            r"|github_pat_[A-Za-z0-9_]{20,}"
            r")\b"
        ),
    ),
    (
        "jeton GitLab",
        re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    ),
    (
        "clé AWS",
        re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    ),
    (
        "jeton Slack",
        re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    ),
    (
        "clé OpenAI",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    ),
    (
        "jeton npm",
        re.compile(r"\bnpm_[A-Za-z0-9]{20,}\b"),
    ),
)

generic_assignment = re.compile(
    r"""(?ix)
    \b(
        password
        |passwd
        |pwd
        |api[_-]?key
        |client[_-]?secret
        |secret
        |access[_-]?token
        |refresh[_-]?token
        |private[_-]?key
    )\b
    \s*[:=]\s*
    ["']
    ([^"'\r\n]{8,})
    ["']
    """
)

safe_value_markers = (
    "example",
    "sample",
    "placeholder",
    "changeme",
    "change_me",
    "replace_me",
    "replace-me",
    "your_",
    "your-",
    "dummy",
    "not_a_secret",
    "not-a-secret",
    "${",
    "{{",
    "<secret",
    "<token",
    "<password",
)

findings: list[tuple[str, int | None, str]] = []


def is_skipped_path(path_text: str) -> bool:
    parts = pathlib.PurePosixPath(path_text).parts
    return any(part in ignored_directories for part in parts)


def inspect_filename(path_text: str, tracked_check: bool = False) -> None:
    if is_skipped_path(path_text):
        return

    path = pathlib.PurePosixPath(path_text)
    basename = path.name.lower()
    suffix = path.suffix.lower()

    if (
        basename == ".env"
        or (
            basename.startswith(".env.")
            and basename not in allowed_environment_files
        )
    ):
        findings.append(
            (
                path_text,
                None,
                "fichier d’environnement sensible",
            )
        )

    if suffix in sensitive_extensions:
        findings.append(
            (
                path_text,
                None,
                f"extension sensible {suffix}",
            )
        )

    if basename in sensitive_names:
        findings.append(
            (
                path_text,
                None,
                "nom de fichier sensible",
            )
        )

    for pattern in backup_patterns:
        if pattern.search(path_text):
            findings.append(
                (
                    path_text,
                    None,
                    "sauvegarde ou fichier temporaire",
                )
            )
            break


def read_candidate(path_text: str) -> bytes | None:
    try:
        if staged_files:
            return git_bytes("show", f":{path_text}")

        path = pathlib.Path(path_text)

        if not path.is_file():
            return None

        return path.read_bytes()

    except (
        subprocess.CalledProcessError,
        OSError,
    ):
        return None


for tracked_file in tracked_files:
    inspect_filename(tracked_file, tracked_check=True)


for candidate in candidate_files:
    if is_skipped_path(candidate):
        continue

    inspect_filename(candidate)

    raw_content = read_candidate(candidate)

    if raw_content is None:
        continue

    if b"\0" in raw_content[:8192]:
        continue

    if len(raw_content) > 20 * 1024 * 1024:
        findings.append(
            (
                candidate,
                None,
                "fichier texte supérieur à 20 Mio non analysé",
            )
        )
        continue

    text = raw_content.decode(
        "utf-8",
        errors="replace",
    )

    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        if "secret-scan: allow" in line:
            continue

        for label, pattern in content_patterns:
            if pattern.search(line):
                findings.append(
                    (
                        candidate,
                        line_number,
                        label,
                    )
                )

        for match in generic_assignment.finditer(line):
            value = match.group(2).strip()
            lower_value = value.lower()

            if any(
                marker in lower_value
                for marker in safe_value_markers
            ):
                continue

            findings.append(
                (
                    candidate,
                    line_number,
                    "secret potentiel assigné en clair",
                )
            )


unique_findings = []
seen = set()

for finding in findings:
    if finding in seen:
        continue

    seen.add(finding)
    unique_findings.append(finding)


print("=== CONTRÔLE DE SÉCURITÉ PRÉ-COMMIT ===")
print(f"Mode : {scan_mode}")
print(f"Fichiers candidats : {len(candidate_files)}")
print(f"Fichiers suivis contrôlés par nom : {len(tracked_files)}")

if not candidate_files:
    print(
        "AVERTISSEMENT : aucun fichier modifié ou préparé "
        "à analyser."
    )

if unique_findings:
    print()
    print("ÉCHEC : élément(s) sensible(s) détecté(s).")

    for path_text, line_number, category in unique_findings:
        location = (
            f"{path_text}:{line_number}"
            if line_number is not None
            else path_text
        )

        # Ne jamais afficher la valeur potentiellement secrète.
        print(f"- {location} — {category}")

    print()
    print(
        "Le commit est bloqué. Corrige les alertes, "
        "puis relance le contrôle."
    )

    raise SystemExit(1)

print()
print("OK : aucun secret ni fichier sensible détecté.")
PY

echo
echo "=== CONTRÔLE DU FORMAT GIT ==="

if git diff --cached --quiet; then
    git diff --check
else
    git diff --cached --check
fi

echo
echo "VALIDATION SÉCURITÉ PRÉ-COMMIT : OK"
