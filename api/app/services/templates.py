from __future__ import annotations

from pathlib import Path

from app.core.storage import load_json, save_json


class TemplatesError(Exception):
    pass


class TemplatesNotFound(TemplatesError):
    pass


def get_templates(templates_file: Path) -> dict:
    return load_json(templates_file, {"departments": {}})


def upsert_department_template(
    templates_file: Path,
    name: str,
    default_ou: str,
    default_groups: list[str],
) -> tuple[dict, dict]:
    templates = get_templates(templates_file)
    departments = templates.setdefault("departments", {})

    existing_department = departments.get(name, {})
    existing_roles = existing_department.get("roles", {})

    departments[name] = {
        "default_ou": default_ou,
        "default_groups": sorted(set(default_groups)),
        "roles": existing_roles,
    }

    save_json(templates_file, templates)

    audit_event = {
        "action": "template_department_upserted",
        "actor": "admin",
        "message": f"Département template créé/modifié : {name}",
        "details": {
            "department": name,
            "default_ou": default_ou,
            "default_groups": default_groups,
        },
    }

    return {
        "message": "Département template créé/modifié",
        "department": departments[name],
    }, audit_event


def delete_department_template(templates_file: Path, department_name: str) -> tuple[dict, dict]:
    templates = get_templates(templates_file)
    departments = templates.setdefault("departments", {})

    if department_name not in departments:
        raise TemplatesNotFound("Département template introuvable")

    deleted_department = departments.pop(department_name)

    save_json(templates_file, templates)

    audit_event = {
        "action": "template_department_deleted",
        "actor": "admin",
        "message": f"Département template supprimé : {department_name}",
        "details": {
            "department": department_name,
        },
    }

    return {
        "message": "Département template supprimé",
        "department_name": department_name,
        "deleted": deleted_department,
    }, audit_event


def upsert_role_template(
    templates_file: Path,
    department_name: str,
    role_name: str,
    groups: list[str],
) -> tuple[dict, dict]:
    templates = get_templates(templates_file)
    departments = templates.setdefault("departments", {})

    if department_name not in departments:
        raise TemplatesNotFound("Département template introuvable")

    roles = departments[department_name].setdefault("roles", {})

    roles[role_name] = {
        "groups": sorted(set(groups)),
    }

    save_json(templates_file, templates)

    audit_event = {
        "action": "template_role_upserted",
        "actor": "admin",
        "message": f"Poste template créé/modifié : {role_name}",
        "details": {
            "department": department_name,
            "role": role_name,
            "groups": groups,
        },
    }

    return {
        "message": "Poste template créé/modifié",
        "department": department_name,
        "role": role_name,
        "data": roles[role_name],
    }, audit_event


def delete_role_template(
    templates_file: Path,
    department_name: str,
    role_name: str,
) -> tuple[dict, dict]:
    templates = get_templates(templates_file)
    departments = templates.setdefault("departments", {})

    if department_name not in departments:
        raise TemplatesNotFound("Département template introuvable")

    roles = departments[department_name].setdefault("roles", {})

    if role_name not in roles:
        raise TemplatesNotFound("Poste template introuvable")

    deleted_role = roles.pop(role_name)

    save_json(templates_file, templates)

    audit_event = {
        "action": "template_role_deleted",
        "actor": "admin",
        "message": f"Poste template supprimé : {role_name}",
        "details": {
            "department": department_name,
            "role": role_name,
        },
    }

    return {
        "message": "Poste template supprimé",
        "department": department_name,
        "role": role_name,
        "deleted": deleted_role,
    }, audit_event
