"""Generate docs/database.md (database architecture) from the Django models.

Usage:  python manage.py dbdocs --output ../docs/database.md
"""
from collections import defaultdict
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand

TYPES = {
    "UUIDField": "uuid",
    "CharField": "varchar",
    "TextField": "text",
    "SlugField": "varchar",
    "EmailField": "varchar",
    "URLField": "varchar",
    "FileField": "varchar (path)",
    "ImageField": "varchar (path)",
    "BooleanField": "boolean",
    "IntegerField": "integer",
    "PositiveIntegerField": "integer",
    "PositiveSmallIntegerField": "smallint",
    "SmallIntegerField": "smallint",
    "BigIntegerField": "bigint",
    "DecimalField": "numeric",
    "FloatField": "double",
    "DateField": "date",
    "DateTimeField": "timestamptz",
    "TimeField": "time",
    "JSONField": "jsonb",
    "GenericIPAddressField": "inet",
}

APP_TITLES = {
    "accounts": "Accounts and authentication",
    "access_control": "Roles and permissions",
    "organizations": "Organizations",
    "branches": "Branches and departments",
    "hr": "Human resources",
    "recruitment": "Recruitment",
    "crm": "CRM (leads and clients)",
    "sales": "Sales (quotations)",
    "projects": "Projects and tasks",
    "timesheets": "Timesheets",
    "finance": "Finance (invoices and payments)",
    "notifications": "Notifications",
    "audit": "Audit log",
    "reports": "Reports",
    "core": "Core",
}

INTRO = """# OmniOS database architecture

This file is generated from the Django models by `python manage.py dbdocs`.
The database is PostgreSQL 16. Do not edit the tables by hand; change the models and regenerate.

## Design principles

- **UUID primary keys** on every table, so ids are not guessable and records can be merged safely.
- **Decimals for money** (`numeric`), never floats. Totals are recalculated on the server.
- **PROTECT on foreign keys** that matter for history, so a client, project or invoice cannot be deleted while records depend on it.
- **Branch isolation**: records that belong to a branch carry a branch foreign key, and every query is filtered by the user's branch unless the user is a Super Admin.
- **Status history tables** record every status change (who, when, from, to, reason).
- **Append-only audit log**: audit rows are written by signals and middleware (including the client IP) and cannot be edited or deleted through the API.
- **Database-level constraints**: unique constraints (including a partial unique constraint on payment reference) enforce rules even if application code is bypassed.
- **Row locks**: workflow services use `transaction.atomic` and `select_for_update` so two users cannot convert the same quotation or confirm the same payment twice.
"""


def local(model):
    return model.__module__.startswith("apps.")


def column_type(field):
    base = field.get_internal_type()
    sql = TYPES.get(base, base.lower())
    if base == "CharField" and field.max_length:
        sql = f"varchar({field.max_length})"
    if base == "DecimalField":
        sql = f"numeric({field.max_digits},{field.decimal_places})"
    return sql


def notes(field):
    out = []
    if field.primary_key:
        out.append("PK")
    if field.is_relation and field.many_to_one or field.one_to_one:
        target = field.related_model._meta.db_table
        rule = getattr(field.remote_field.on_delete, "__name__", "")
        out.append(f"FK to {target}" + (f" ({rule})" if rule else ""))
    if field.unique and not field.primary_key:
        out.append("unique")
    if field.null:
        out.append("nullable")
    if field.choices:
        out.append("choices: " + ", ".join(str(c[0]) for c in field.choices))
    if field.has_default() and not callable(field.default) and field.default != "":
        out.append(f"default {field.default}")
    return "; ".join(out)


def er_diagram(models):
    names = {m._meta.db_table for m in models}
    lines = ["```mermaid", "erDiagram"]
    for m in models:
        for f in m._meta.concrete_fields:
            if f.is_relation and f.related_model._meta.db_table in names:
                a = f.related_model._meta.db_table
                lines.append(f"    {a} ||--o{{ {m._meta.db_table} : \"{f.name}\"")
    lines.append("```")
    return "\n".join(lines)


class Command(BaseCommand):
    help = "Write the database architecture document from the models."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="../docs/database.md")

    def handle(self, *args, **opts):
        models = sorted(
            (m for m in apps.get_models() if local(m)),
            key=lambda m: (m._meta.app_label, m._meta.db_table),
        )
        by_app = defaultdict(list)
        for m in models:
            by_app[m._meta.app_label].append(m)

        out = [INTRO, "## Tables by module\n"]
        for app, ms in by_app.items():
            title = APP_TITLES.get(app, app)
            out.append(f"- **{title}**: " + ", ".join(f"`{m._meta.db_table}`" for m in ms))
        out.append("\n## Relationships\n")
        for app, ms in by_app.items():
            out.append(f"### {APP_TITLES.get(app, app)}\n")
            out.append(er_diagram(ms) + "\n")
        out.append("## Table reference\n")
        for app, ms in by_app.items():
            out.append(f"### {APP_TITLES.get(app, app)}\n")
            for m in ms:
                out.append(f"#### {m._meta.db_table}\n")
                if m.__doc__ and not m.__doc__.startswith(m.__name__ + "("):
                    out.append(m.__doc__.strip().splitlines()[0] + "\n")
                out.append("| Column | Type | Notes |")
                out.append("|---|---|---|")
                for f in m._meta.concrete_fields:
                    out.append(f"| `{f.column}` | {column_type(f)} | {notes(f)} |")
                for c in m._meta.constraints:
                    out.append(f"\nConstraint `{c.name}`: {c.__class__.__name__}")
                out.append("")
        path = Path(opts["output"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(out), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote {path} ({len(models)} tables)"))