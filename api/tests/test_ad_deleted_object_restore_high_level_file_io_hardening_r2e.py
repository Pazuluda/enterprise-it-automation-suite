from __future__ import annotations

from pathlib import Path

import pytest

from app.services import (
    ad_deleted_object_restore_human_authorization as human,
)

from app.services import (
    ad_deleted_object_restore_post_authorization as post,
)


def test_post_auth_rejects_broken_symlink(
    tmp_path,
):
    path = (
        tmp_path
        / "broken.json"
    )

    path.symlink_to(
        tmp_path
        / "missing.json"
    )

    with pytest.raises(
        post.AdDeletedObjectRestorePostAuthorizationError,
        match="symlink",
    ):
        post._safe_absolute_path(
            path,
            field="probe",
        )


def test_human_auth_rejects_broken_symlink(
    tmp_path,
):
    path = (
        tmp_path
        / "broken.json"
    )

    path.symlink_to(
        tmp_path
        / "missing.json"
    )

    with pytest.raises(
        human.AdDeletedObjectRestoreHumanAuthorizationError,
        match="symlink",
    ):
        human._assert_absolute_path(
            path,
            field="probe",
        )


def test_post_auth_rejects_symlink_parent(
    tmp_path,
):
    real = (
        tmp_path
        / "real"
    )

    real.mkdir()

    link = (
        tmp_path
        / "link"
    )

    link.symlink_to(
        real,
        target_is_directory=True,
    )

    with pytest.raises(
        post.AdDeletedObjectRestorePostAuthorizationError,
        match="parent.*symlink",
    ):
        post._safe_absolute_path(
            link
            / "registry.json",
            field="probe",
        )


def test_human_auth_rejects_symlink_parent(
    tmp_path,
):
    real = (
        tmp_path
        / "real"
    )

    real.mkdir()

    link = (
        tmp_path
        / "link"
    )

    link.symlink_to(
        real,
        target_is_directory=True,
    )

    with pytest.raises(
        human.AdDeletedObjectRestoreHumanAuthorizationError,
        match="parent.*symlink",
    ):
        human._assert_absolute_path(
            link
            / "registry.json",
            field="probe",
        )


def test_post_auth_loader_uses_fd_nofollow_pattern():
    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_post_authorization.py"
    ).read_text(
        encoding="utf-8"
    )

    start = source.index(
        "def _load_authorization_record("
    )

    end = source.index(
        "@contextmanager\n"
        "def _exclusive_post_authorization_lock(",
        start,
    )

    block = source[
        start:end
    ]

    assert ".read_text(" not in block
    assert "os.open(" in block
    assert "os.O_RDONLY" in block
    assert "os.fstat(" in block
    assert "os.fdopen(" in block
    assert "_open_flags(" in block


def test_human_auth_loader_uses_fd_nofollow_pattern():
    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_human_authorization.py"
    ).read_text(
        encoding="utf-8"
    )

    start = source.index(
        "def _load_registry_records("
    )

    end = source.index(
        "def _load_ticket_record(",
        start,
    )

    block = source[
        start:end
    ]

    assert ".read_text(" not in block
    assert "os.open(" in block
    assert "os.O_RDONLY" in block
    assert "os.fstat(" in block
    assert "os.fdopen(" in block
    assert "_open_flags(" in block


def test_post_auth_lock_does_not_create_missing_parent(
    tmp_path,
):
    parent = (
        tmp_path
        / "does-not-exist"
    )

    target = (
        parent
        / "authorization-consumption.json"
    )

    with pytest.raises(
        post.AdDeletedObjectRestorePostAuthorizationError,
        match="parent must already exist",
    ):
        with post._exclusive_post_authorization_lock(
            target
        ):
            pass

    assert not parent.exists()


def test_human_auth_lock_does_not_create_missing_parent(
    tmp_path,
):
    parent = (
        tmp_path
        / "does-not-exist"
    )

    target = (
        parent
        / "authorization.json"
    )

    with pytest.raises(
        human.AdDeletedObjectRestoreHumanAuthorizationError,
        match="parent must already exist",
    ):
        with human._exclusive_human_authorization_lock(
            target
        ):
            pass

    assert not parent.exists()


def test_high_level_lock_blocks_have_no_recursive_mkdir():
    post_source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_post_authorization.py"
    ).read_text(
        encoding="utf-8"
    )

    human_source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_human_authorization.py"
    ).read_text(
        encoding="utf-8"
    )

    p0 = post_source.index(
        "@contextmanager\n"
        "def _exclusive_post_authorization_lock("
    )

    p1 = post_source.index(
        "def _assert_final_consumption(",
        p0,
    )

    h0 = human_source.index(
        "@contextmanager\n"
        "def _exclusive_human_authorization_lock("
    )

    h1 = human_source.index(
        "def _assert_authorization_not_reused(",
        h0,
    )

    assert ".mkdir(" not in post_source[p0:p1]
    assert ".mkdir(" not in human_source[h0:h1]

    assert "os.open(" in post_source[p0:p1]
    assert "os.open(" in human_source[h0:h1]
