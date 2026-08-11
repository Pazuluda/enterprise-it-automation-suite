from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.services import (
    ad_deleted_object_restore_execution_ticket
    as execution_ticket,
)

from app.services import (
    ad_deleted_object_restore_post_authorization
    as post_authorization,
)


CONFIRMATION = (
    "RESTORE "
    "b1018519-8b6e-4788-81c8-3108a188e7b4 "
    "AS GG_C95_RECYCLE_TEST "
    "TO OU=test,OU=Users,OU=EITAS,"
    "DC=API,DC=LOCAL"
)

EXPECTED_CANONICAL_SHA256 = (
    "3e10ab5bcaf88f94983d3cd1c2445812"
    "9d9f2961eabdbd0c108b45bf6b37bb3c"
)

EXPECTED_RAW_SHA256 = (
    "498574c38da96aa6c1dc3e0b2a978df5"
    "5d1c3f909a519e308bc176ae166c176f"
)


def test_post_authorization_confirmation_digest_is_canonical():
    actual = (
        post_authorization
        ._confirmation_sha256(
            CONFIRMATION
        )
    )

    assert (
        actual
        == EXPECTED_CANONICAL_SHA256
    )


def test_execution_ticket_and_post_authorization_share_digest_contract():
    ticket_digest = (
        execution_ticket
        ._canonical_sha256(
            {
                "confirmation_text":
                    CONFIRMATION,
            }
        )
    )

    post_digest = (
        post_authorization
        ._confirmation_sha256(
            CONFIRMATION
        )
    )

    assert (
        ticket_digest
        == post_digest
        == EXPECTED_CANONICAL_SHA256
    )


def test_raw_text_sha256_is_not_confirmation_contract():
    raw = hashlib.sha256(
        CONFIRMATION.encode(
            "utf-8"
        )
    ).hexdigest()

    assert raw == EXPECTED_RAW_SHA256

    assert (
        raw
        != EXPECTED_CANONICAL_SHA256
    )


def test_confirmation_helper_matches_explicit_canonical_json():
    canonical = json.dumps(
        {
            "confirmation_text":
                CONFIRMATION,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode(
        "utf-8"
    )

    expected = hashlib.sha256(
        canonical
    ).hexdigest()

    assert (
        post_authorization
        ._confirmation_sha256(
            CONFIRMATION
        )
        == expected
    )


def test_final_consumption_no_longer_hashes_raw_confirmation_text():
    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_post_authorization.py"
    ).read_text(
        encoding="utf-8"
    )

    start = source.index(
        "def _assert_final_consumption("
    )

    end = source.index(
        "def build_ad_deleted_object_restore_post_authorization_chain(",
        start,
    )

    block = source[
        start:end
    ]

    assert (
        "_confirmation_sha256("
        in block
    )

    assert (
        "confirmation_text.encode("
        not in block
    )
