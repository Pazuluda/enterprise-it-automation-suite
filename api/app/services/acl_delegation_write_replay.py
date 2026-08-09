from __future__ import annotations

import fcntl
import json
import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.services.acl_delegation_write_trust import (
    AclDelegationWriteTrustBadRequest,
    resolve_trusted_acl_delegation_write_evidence,
)


ACL_DELEGATION_WRITE_REPLAY_CONTRACT_VERSION = "c8.4b2"

ACL_DELEGATION_WRITE_REPLAY_ENABLED = True

# C8.4B2 only consumes trusted evidence exactly once.
# It MUST NOT create or execute an ACL write job.
ACL_DELEGATION_WRITE_REPLAY_JOB_CREATION_ENABLED = False
ACL_DELEGATION_WRITE_REPLAY_RUNTIME_ENABLED = False
ACL_DELEGATION_WRITE_REPLAY_PRODUCTION_ENABLED = False
ACL_DELEGATION_WRITE_REPLAY_AD_WRITE_ENABLED = False

REGISTRY_FILE_MODE = 0o600
REGISTRY_MAX_RECORDS = 100000


class AclDelegationWriteReplayError(ValueError):
    pass


class AclDelegationWriteReplayConflict(
    AclDelegationWriteReplayError
):
    pass


class AclDelegationWriteReplayStorageError(
    AclDelegationWriteReplayError
):
    pass


@dataclass(frozen=True)
class AclDelegationWriteConsumption:
    consumption_id: str
    evidence_digest: str
    simulation_job_id: str
    security_descriptor_job_id: str
    target_dn: str
    target_object_guid: str
    principal_sid: str
    acl_fingerprint: str
    consumed_at: str
    consumed: bool
    job_creation_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    ad_write_authorized: bool


def _normalize_now(
    now: datetime | None,
) -> datetime:
    value = (
        now
        if now is not None
        else datetime.now(timezone.utc)
    )

    if not isinstance(value, datetime):
        raise AclDelegationWriteReplayError(
            "Horodatage de consommation invalide"
        )

    if value.tzinfo is None:
        raise AclDelegationWriteReplayError(
            "Horodatage de consommation sans fuseau"
        )

    return value.astimezone(timezone.utc)


def _normalize_registry_path(
    value: Path,
) -> Path:
    path = Path(value)

    if not path.name:
        raise AclDelegationWriteReplayStorageError(
            "Chemin du registre ACL invalide"
        )

    parent = path.parent.resolve()

    parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    resolved = parent / path.name

    if resolved.is_symlink():
        raise AclDelegationWriteReplayStorageError(
            "Lien symbolique interdit pour le registre ACL"
        )

    if (
        resolved.exists()
        and not resolved.is_file()
    ):
        raise AclDelegationWriteReplayStorageError(
            "Le registre ACL n'est pas un fichier"
        )

    return resolved


def _lock_path(
    registry_path: Path,
) -> Path:
    return registry_path.with_name(
        "." + registry_path.name + ".lock"
    )


def _safe_open_flags(
    base_flags: int,
) -> int:
    flags = base_flags

    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC

    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    return flags


@contextmanager
def _exclusive_registry_lock(
    registry_path: Path,
):
    lock_path = _lock_path(
        registry_path
    )

    if lock_path.is_symlink():
        raise AclDelegationWriteReplayStorageError(
            "Lien symbolique interdit pour le verrou ACL"
        )

    flags = _safe_open_flags(
        os.O_RDWR | os.O_CREAT
    )

    try:
        fd = os.open(
            lock_path,
            flags,
            REGISTRY_FILE_MODE,
        )
    except OSError as exc:
        raise AclDelegationWriteReplayStorageError(
            "Impossible d'ouvrir le verrou ACL"
        ) from exc

    try:
        os.fchmod(
            fd,
            REGISTRY_FILE_MODE,
        )

        fcntl.flock(
            fd,
            fcntl.LOCK_EX,
        )

        yield

    finally:
        try:
            fcntl.flock(
                fd,
                fcntl.LOCK_UN,
            )
        finally:
            os.close(fd)


def _empty_registry() -> dict:
    return {
        "contract_version": (
            ACL_DELEGATION_WRITE_REPLAY_CONTRACT_VERSION
        ),
        "records": [],
    }


def _validate_registry(
    data,
) -> dict:
    if not isinstance(data, dict):
        raise AclDelegationWriteReplayStorageError(
            "Registre anti-replay ACL invalide"
        )

    if (
        data.get("contract_version")
        != ACL_DELEGATION_WRITE_REPLAY_CONTRACT_VERSION
    ):
        raise AclDelegationWriteReplayStorageError(
            "Version du registre anti-replay ACL invalide"
        )

    records = data.get("records")

    if not isinstance(records, list):
        raise AclDelegationWriteReplayStorageError(
            "Liste anti-replay ACL invalide"
        )

    if len(records) > REGISTRY_MAX_RECORDS:
        raise AclDelegationWriteReplayStorageError(
            "Registre anti-replay ACL plein"
        )

    seen_consumptions = set()
    seen_digests = set()
    seen_simulations = set()
    seen_descriptors = set()

    required = {
        "consumption_id",
        "evidence_digest",
        "simulation_job_id",
        "security_descriptor_job_id",
        "target_dn",
        "target_object_guid",
        "principal_sid",
        "acl_fingerprint",
        "consumed_at",
        "state",
    }

    for record in records:
        if not isinstance(record, dict):
            raise AclDelegationWriteReplayStorageError(
                "Enregistrement anti-replay ACL invalide"
            )

        if not required.issubset(record):
            raise AclDelegationWriteReplayStorageError(
                "Enregistrement anti-replay ACL incomplet"
            )

        state = record.get("state")

        if state not in {
            "consumed",
            "claimed_dormant",
            "prewrite_ticketed",
            "prewrite_processing",
            "prewrite_validated",
            "prewrite_failed",
        }:
            raise AclDelegationWriteReplayStorageError(
                "Etat anti-replay ACL invalide"
            )

        if state in {
            "claimed_dormant",
            "prewrite_ticketed",
            "prewrite_processing",
            "prewrite_validated",
            "prewrite_failed",
        }:
            claim_required = {
                "claim_id",
                "contract_version_claim",
                "envelope_digest",
                "server_nonce",

                "principal_dn",
                "access_control_type",
                "rights",
                "inheritance_type",
                "dacl_sddl_sha256",

                "actor_subject",
                "actor_username",
                "actor_roles",
                "actor_issuer",
                "actor_azp",

                "issued_at",
                "expires_at",
                "claimed_at",

                "object_type_guid",
                "inherited_object_type_guid",
            }

            if not claim_required.issubset(record):
                raise AclDelegationWriteReplayStorageError(
                    "Claim ACL dormant incomplet"
                )

            for key in (
                "actor_roles",
                "rights",
            ):
                value = record.get(key)

                if (
                    not isinstance(value, list)
                    or not value
                    or not all(
                        isinstance(item, str)
                        and item.strip()
                        for item in value
                    )
                ):
                    raise AclDelegationWriteReplayStorageError(
                        "Liste du claim ACL invalide : "
                        + key
                    )

            nullable_guid_keys = (
                "object_type_guid",
                "inherited_object_type_guid",
            )

            scalar_keys = (
                claim_required
                - {
                    "actor_roles",
                    "rights",
                    *nullable_guid_keys,
                }
            )

            for key in scalar_keys:
                if not str(
                    record.get(key)
                    or ""
                ).strip():
                    raise AclDelegationWriteReplayStorageError(
                        "Valeur du claim ACL vide : "
                        + key
                    )

            for key in nullable_guid_keys:
                value = record.get(key)

                if (
                    value is not None
                    and not str(value).strip()
                ):
                    raise AclDelegationWriteReplayStorageError(
                        "GUID nullable du claim ACL invalide : "
                        + key
                    )

            for key in (
                "job_creation_authorized",
                "runtime_authorized",
                "production_authorized",
                "ad_write_authorized",
            ):
                if record.get(key) is not False:
                    raise AclDelegationWriteReplayStorageError(
                        "Claim ACL dormant autorisant interdit"
                    )

        if state in {
            "prewrite_ticketed",
            "prewrite_processing",
            "prewrite_validated",
            "prewrite_failed",
        }:
            ticket_required = {
                "prewrite_ticket_id",
                "prewrite_ticket_contract_version",
                "prewrite_ticket_created_at",
                "prewrite_ticket_expires_at",
                "prewrite_ticket_payload_digest",
                "prewrite_ticket_payload",
                "prewrite_validation_runtime_authorized",
            }

            if not ticket_required.issubset(record):
                raise AclDelegationWriteReplayStorageError(
                    "Ticket ACL pre-write incomplet"
                )

            for key in (
                "prewrite_ticket_id",
                "prewrite_ticket_contract_version",
                "prewrite_ticket_created_at",
                "prewrite_ticket_expires_at",
                "prewrite_ticket_payload_digest",
            ):
                if not str(
                    record.get(key)
                    or ""
                ).strip():
                    raise AclDelegationWriteReplayStorageError(
                        "Valeur ticket ACL pre-write vide : "
                        + key
                    )

            expected_prewrite_runtime = (
                state == "prewrite_processing"
            )

            if (
                record.get(
                    "prewrite_validation_runtime_authorized"
                )
                is not expected_prewrite_runtime
            ):
                raise AclDelegationWriteReplayStorageError(
                    "Etat runtime ticket ACL pre-write incoherent"
                )

            ticket_payload = record.get(
                "prewrite_ticket_payload"
            )

            if not isinstance(ticket_payload, dict):
                raise AclDelegationWriteReplayStorageError(
                    "Payload ticket ACL pre-write invalide"
                )

            if (
                ticket_payload.get("contract_version")
                != "c8.4b4"
                or ticket_payload.get("state")
                != "claimed_dormant"
            ):
                raise AclDelegationWriteReplayStorageError(
                    "Contrat payload ticket ACL invalide"
                )

            payload_authorization = (
                ticket_payload.get("authorization")
            )

            if not isinstance(
                payload_authorization,
                dict,
            ):
                raise AclDelegationWriteReplayStorageError(
                    "Authorization ticket ACL invalide"
                )

            for key in (
                "job_creation_authorized",
                "runtime_authorized",
                "production_authorized",
                "ad_write_authorized",
            ):
                if payload_authorization.get(key) is not False:
                    raise AclDelegationWriteReplayStorageError(
                        "Payload ticket ACL autorisant interdit"
                    )

            expected_pairs = (
                (
                    ticket_payload.get("claim_id"),
                    record.get("claim_id"),
                ),
                (
                    ticket_payload.get("consumption_id"),
                    record.get("consumption_id"),
                ),
                (
                    (
                        ticket_payload.get("target")
                        or {}
                    ).get("dn"),
                    record.get("target_dn"),
                ),
                (
                    (
                        ticket_payload.get("target")
                        or {}
                    ).get("object_guid"),
                    record.get("target_object_guid"),
                ),
                (
                    (
                        ticket_payload.get("principal")
                        or {}
                    ).get("dn"),
                    record.get("principal_dn"),
                ),
                (
                    (
                        ticket_payload.get("principal")
                        or {}
                    ).get("sid"),
                    record.get("principal_sid"),
                ),
                (
                    (
                        ticket_payload.get("ace")
                        or {}
                    ).get("access_control_type"),
                    record.get("access_control_type"),
                ),
                (
                    (
                        ticket_payload.get("ace")
                        or {}
                    ).get("rights"),
                    record.get("rights"),
                ),
                (
                    (
                        ticket_payload.get("ace")
                        or {}
                    ).get("inheritance_type"),
                    record.get("inheritance_type"),
                ),
                (
                    (
                        ticket_payload.get("ace")
                        or {}
                    ).get("object_type_guid"),
                    record.get("object_type_guid"),
                ),
                (
                    (
                        ticket_payload.get("ace")
                        or {}
                    ).get(
                        "inherited_object_type_guid"
                    ),
                    record.get(
                        "inherited_object_type_guid"
                    ),
                ),
                (
                    (
                        ticket_payload.get("dacl")
                        or {}
                    ).get("dacl_sddl_sha256"),
                    record.get("dacl_sddl_sha256"),
                ),
                (
                    (
                        ticket_payload.get("dacl")
                        or {}
                    ).get("acl_fingerprint"),
                    record.get("acl_fingerprint"),
                ),
            )

            if any(
                actual != expected
                for actual, expected
                in expected_pairs
            ):
                raise AclDelegationWriteReplayStorageError(
                    "Payload ticket ACL incoherent "
                    "avec le claim serveur"
                )

        if state in {
            "prewrite_processing",
            "prewrite_validated",
            "prewrite_failed",
        }:
            execution_required = {
                "prewrite_execution_id",
                "prewrite_claimed_at",
                "prewrite_claimed_by",
            }

            if not execution_required.issubset(
                record
            ):
                raise AclDelegationWriteReplayStorageError(
                    "Execution ACL pre-write incomplete"
                )

            for key in execution_required:
                if not str(
                    record.get(key)
                    or ""
                ).strip():
                    raise AclDelegationWriteReplayStorageError(
                        "Valeur execution ACL vide : "
                        + key
                    )

        if state in {
            "prewrite_validated",
            "prewrite_failed",
        }:
            final_required = {
                "prewrite_completed_at",
                "prewrite_success",
            }

            if not final_required.issubset(
                record
            ):
                raise AclDelegationWriteReplayStorageError(
                    "Resultat final ACL pre-write incomplet"
                )

            if not str(
                record.get(
                    "prewrite_completed_at"
                )
                or ""
            ).strip():
                raise AclDelegationWriteReplayStorageError(
                    "Horodatage final ACL pre-write vide"
                )

            if state == "prewrite_validated":
                if (
                    record.get("prewrite_success")
                    is not True
                ):
                    raise AclDelegationWriteReplayStorageError(
                        "Succes pre-write valide incoherent"
                    )

                if not isinstance(
                    record.get(
                        "prewrite_result_summary"
                    ),
                    dict,
                ):
                    raise AclDelegationWriteReplayStorageError(
                        "Resume resultat pre-write invalide"
                    )

            if state == "prewrite_failed":
                if (
                    record.get("prewrite_success")
                    is not False
                ):
                    raise AclDelegationWriteReplayStorageError(
                        "Echec pre-write incoherent"
                    )

                if not str(
                    record.get(
                        "prewrite_error_message"
                    )
                    or ""
                ).strip():
                    raise AclDelegationWriteReplayStorageError(
                        "Message echec pre-write manquant"
                    )

        values = {
            key: str(
                record.get(key) or ""
            ).strip()
            for key in required
            if key != "state"
        }

        if any(
            not value
            for value in values.values()
        ):
            raise AclDelegationWriteReplayStorageError(
                "Valeur anti-replay ACL vide"
            )

        consumption_id = values[
            "consumption_id"
        ]

        evidence_digest = values[
            "evidence_digest"
        ].lower()

        simulation_job_id = values[
            "simulation_job_id"
        ].lower()

        descriptor_job_id = values[
            "security_descriptor_job_id"
        ].lower()

        if consumption_id in seen_consumptions:
            raise AclDelegationWriteReplayStorageError(
                "ID de consommation ACL duplique"
            )

        if evidence_digest in seen_digests:
            raise AclDelegationWriteReplayStorageError(
                "Digest ACL duplique dans le registre"
            )

        if simulation_job_id in seen_simulations:
            raise AclDelegationWriteReplayStorageError(
                "Simulation ACL reutilisee dans le registre"
            )

        if descriptor_job_id in seen_descriptors:
            raise AclDelegationWriteReplayStorageError(
                "Security Descriptor reutilise dans le registre"
            )

        seen_consumptions.add(
            consumption_id
        )

        seen_digests.add(
            evidence_digest
        )

        seen_simulations.add(
            simulation_job_id
        )

        seen_descriptors.add(
            descriptor_job_id
        )

    return data


def _safe_load_registry(
    registry_path: Path,
) -> dict:
    if not registry_path.exists():
        return _empty_registry()

    if registry_path.is_symlink():
        raise AclDelegationWriteReplayStorageError(
            "Lien symbolique interdit pour le registre ACL"
        )

    flags = _safe_open_flags(
        os.O_RDONLY
    )

    try:
        fd = os.open(
            registry_path,
            flags,
        )
    except OSError as exc:
        raise AclDelegationWriteReplayStorageError(
            "Impossible de lire le registre ACL"
        ) from exc

    try:
        with os.fdopen(
            fd,
            "r",
            encoding="utf-8",
        ) as handle:
            try:
                data = json.load(handle)
            except json.JSONDecodeError as exc:
                raise AclDelegationWriteReplayStorageError(
                    "Registre anti-replay ACL corrompu"
                ) from exc

    except Exception:
        raise

    return _validate_registry(
        data
    )


def _atomic_write_registry(
    registry_path: Path,
    data: dict,
) -> None:
    _validate_registry(
        data
    )

    payload = (
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    temp_path = registry_path.with_name(
        "."
        + registry_path.name
        + "."
        + uuid.uuid4().hex
        + ".tmp"
    )

    flags = _safe_open_flags(
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
    )

    fd = None

    try:
        fd = os.open(
            temp_path,
            flags,
            REGISTRY_FILE_MODE,
        )

        os.fchmod(
            fd,
            REGISTRY_FILE_MODE,
        )

        offset = 0

        while offset < len(payload):
            written = os.write(
                fd,
                payload[offset:],
            )

            if written <= 0:
                raise OSError(
                    "Ecriture registre ACL incomplete"
                )

            offset += written

        os.fsync(fd)
        os.close(fd)
        fd = None

        os.replace(
            temp_path,
            registry_path,
        )

        os.chmod(
            registry_path,
            REGISTRY_FILE_MODE,
        )

        try:
            dir_fd = os.open(
                str(registry_path.parent),
                os.O_DIRECTORY,
            )

            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)

        except OSError:
            pass

    except OSError as exc:
        raise AclDelegationWriteReplayStorageError(
            "Echec d'ecriture atomique du registre ACL"
        ) from exc

    finally:
        if fd is not None:
            os.close(fd)

        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass


def consume_trusted_acl_delegation_write_evidence(
    *,
    ad_admin_jobs_file: Path,
    ad_explorer_jobs_file: Path,
    replay_registry_file: Path,
    intent_payload: dict,
    now: datetime | None = None,
) -> AclDelegationWriteConsumption:
    if not ACL_DELEGATION_WRITE_REPLAY_ENABLED:
        raise AclDelegationWriteReplayError(
            "Anti-replay ACL desactive"
        )

    validation_now = _normalize_now(
        now
    )

    try:
        evidence = (
            resolve_trusted_acl_delegation_write_evidence(
                ad_admin_jobs_file=(
                    ad_admin_jobs_file
                ),
                ad_explorer_jobs_file=(
                    ad_explorer_jobs_file
                ),
                intent_payload=(
                    intent_payload
                ),
                now=validation_now,
            )
        )

    except AclDelegationWriteTrustBadRequest as exc:
        raise AclDelegationWriteReplayError(
            str(exc)
        ) from exc

    if (
        not evidence.trusted_evidence_loaded
        or not evidence.binding_validated
        or evidence.job_creation_authorized
        or evidence.runtime_authorized
        or evidence.production_authorized
        or evidence.ad_write_authorized
    ):
        raise AclDelegationWriteReplayError(
            "Preuve ACL de confiance non sure"
        )

    registry_path = (
        _normalize_registry_path(
            replay_registry_file
        )
    )

    with _exclusive_registry_lock(
        registry_path
    ):
        registry = _safe_load_registry(
            registry_path
        )

        records = registry["records"]

        digest = (
            evidence.evidence_digest.lower()
        )

        simulation_id = (
            evidence.simulation_job_id.lower()
        )

        descriptor_id = (
            evidence.security_descriptor_job_id.lower()
        )

        for record in records:
            if (
                str(
                    record.get(
                        "evidence_digest"
                    )
                    or ""
                ).lower()
                == digest
            ):
                raise AclDelegationWriteReplayConflict(
                    "Preuve ACL deja consommee"
                )

            if (
                str(
                    record.get(
                        "simulation_job_id"
                    )
                    or ""
                ).lower()
                == simulation_id
            ):
                raise AclDelegationWriteReplayConflict(
                    "Simulation ACL deja consommee"
                )

            if (
                str(
                    record.get(
                        "security_descriptor_job_id"
                    )
                    or ""
                ).lower()
                == descriptor_id
            ):
                raise AclDelegationWriteReplayConflict(
                    "Security Descriptor deja consomme"
                )

        if (
            len(records)
            >= REGISTRY_MAX_RECORDS
        ):
            raise AclDelegationWriteReplayStorageError(
                "Registre anti-replay ACL plein"
            )

        consumption_id = str(
            uuid.uuid4()
        )

        consumed_at = (
            validation_now.isoformat()
        )

        record = {
            "consumption_id": (
                consumption_id
            ),
            "evidence_digest": (
                evidence.evidence_digest
            ),
            "simulation_job_id": (
                evidence.simulation_job_id
            ),
            "security_descriptor_job_id": (
                evidence.security_descriptor_job_id
            ),
            "target_dn": (
                evidence.binding.target_dn
            ),
            "target_object_guid": (
                evidence.binding.target_object_guid
            ),
            "principal_sid": (
                evidence.binding.principal_sid
            ),
            "acl_fingerprint": (
                evidence.binding.acl_fingerprint
            ),
            "consumed_at": (
                consumed_at
            ),
            "state": "consumed",
        }

        records.append(
            record
        )

        _atomic_write_registry(
            registry_path,
            registry,
        )

    return AclDelegationWriteConsumption(
        consumption_id=consumption_id,
        evidence_digest=(
            evidence.evidence_digest
        ),
        simulation_job_id=(
            evidence.simulation_job_id
        ),
        security_descriptor_job_id=(
            evidence.security_descriptor_job_id
        ),
        target_dn=(
            evidence.binding.target_dn
        ),
        target_object_guid=(
            evidence.binding.target_object_guid
        ),
        principal_sid=(
            evidence.binding.principal_sid
        ),
        acl_fingerprint=(
            evidence.binding.acl_fingerprint
        ),
        consumed_at=consumed_at,
        consumed=True,
        job_creation_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        ad_write_authorized=False,
    )


def assert_acl_delegation_write_replay_invariants(
) -> None:
    if not ACL_DELEGATION_WRITE_REPLAY_ENABLED:
        raise RuntimeError(
            "C8.4B2 anti-replay must remain enabled"
        )

    if ACL_DELEGATION_WRITE_REPLAY_JOB_CREATION_ENABLED:
        raise RuntimeError(
            "C8.4B2 job creation must remain disabled"
        )

    if ACL_DELEGATION_WRITE_REPLAY_RUNTIME_ENABLED:
        raise RuntimeError(
            "C8.4B2 runtime must remain disabled"
        )

    if ACL_DELEGATION_WRITE_REPLAY_PRODUCTION_ENABLED:
        raise RuntimeError(
            "C8.4B2 Production must remain disabled"
        )

    if ACL_DELEGATION_WRITE_REPLAY_AD_WRITE_ENABLED:
        raise RuntimeError(
            "C8.4B2 AD writes must remain disabled"
        )


assert_acl_delegation_write_replay_invariants()
