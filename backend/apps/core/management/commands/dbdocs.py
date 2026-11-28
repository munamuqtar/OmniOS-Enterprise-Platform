import datetime
from collections import defaultdict
from django.apps import apps
from django.core.management.base import BaseCommand

TYPES = {
    "UUIDField": "uuid", "CharField": "varchar", "EmailField": "varchar", "SlugField": "varchar",
    "TextField": "text", "DateField": "date", "DateTimeField": "timestamptz", "DecimalField": "decimal",
    "BooleanField": "boolean", "IntegerField": "integer", "PositiveIntegerField": "integer (>= 0)",
    "PositiveSmallIntegerField": "smallint (>= 0)", "BigAutoField": "bigint", "AutoField": "integer",
    "FileField": "varchar (file path)", "ImageField": "varchar (file path)", "JSONField": "jsonb",
    "GenericIPAddressField": "inet",
}

APP_TITLES = {
    "organizations": "Organization", "branches": "Branches", "accounts": "Users and access",
    "access_control": "Roles and permissions", "hr": "HR (employees and departments)",
    "recruitment": "Recruitment", "crm": "CRM (leads, clients, opportunities)",
    "sales": "Sales (quotations and approvals)", "projects": "Projects and tasks",
    "timesheets": "Timesheets", "finance": "Finance (invoices and payments)",
    "notifications": "Notifications", "audit": "Audit log",
}

INTRO = """# Database architecture

PostgreSQL schema of the OmniOS Enterprise Platform. This file is **generated from the Django models**
(`python manage.py dbdocs --output ../docs/database.md`), so it always matches the migrations.

## Design principles

- **One source of truth.** Django migrations create the schema. PostgreSQL 14 or newer.
- **Keys and timestamps.** Every table has a UUID primary key plus `created_at` and `updated_at`.
- **Money is exact.** Amounts are stored as decimals, never floats, and every total is calculated on the server.
- **Nothing is silently deleted.** Business records use PROTECT foreign keys, so a client, project or invoice cannot be removed while other records depend on it. Records are closed with a status (cancelled, inactive, terminated) instead.
- **Branch isolation.** Every branch-owned record carries a branch, either directly or through its project or invoice. Every query is filtered by the branches assigned to the user (table `accounts_userbranch`).
- **Workflow history.** Status changes and decisions are kept in dedicated tables (lead, opportunity, application and invoice status history, quotation and timesheet approvals), so every decision can be explained later.
- **Audit trail.** `audit_auditlog` is append-only. It stores the user, module, record, branch, client IP, and the previous and new values as JSON. Passwords are never logged.
- **Integrity in the database, not only in code.** Unique numbers (invoice, payment, quotation, project, employee), composite unique keys (candidate and vacancy, user and role, user and branch, project and employee), a partial unique constraint that stops one payment reference being recorded twice on the same invoice, and indexes on branch and status columns.
- **Concurrency.** Approvals, conversions and payments run inside transactions with row locks (`SELECT ... FOR UPDATE`), so two people cannot approve or convert the same record twice.
"""

def local(model):
    return model.__module__.startswith("apps.")

def column_type(field):
    base = field.target_field if field.is_relation else field
    internal = base.get_internal_type()
    text = TYPES.get(internal, internal.lower())
    if internal in ("CharField", "EmailField", "SlugField") and base.max_length:
        text += f"({base.max_length})"
    if internal == "DecimalField":
        text += f"({base.max_digits},{base.decimal_places})"
    return text

def notes(field):
    out = []
    if field.primary_key:
        out.append("PK")
    if field.unique and not field.primary_key:
        out.append("unique")
    if field.is_relation:
        out.append(f"FK to `{field.related_model._meta.db_table}` ({field.remote_field.on_delete.__name__})")
    if field.has_default():
        d = field.default
        out.append("default: " + ("generated" if callable(d) else repr(d)))
    if field.choices:
        out.append("values: " + ", ".join(str(c[0]) for c in field.choices))
    return "; ".join(out)

def er_diagram(models):
    entities, rels = set(), []
    for m in models:
        entities.add(m._meta.object_name.upper())
        for f in m._meta.concrete_fields:
            if f.is_relation and local(f.related_model):
                target, source = f.related_model._meta.object_name.upper(), m._meta.object_name.upper()
                if f.one_to_one:
                    symbol = "|o--o|" if f.null else "||--o|"
                else:
                    symbol = "|o--o{" if f.null else "||--o{"
                rels.append(f'    {target} {symbol} {source} : "{f.name}"')
                entities.update([target, source])
    lines = ["```mermaid", "erDiagram"]
    for name in sorted(entities):
        lines += [f"    {name} {{", "        uuid id PK", "    }"]
    return "\n".join(lines + rels + ["```"])

class Command(BaseCommand):
    help = "Write the database architecture document (tables, columns, relationships) from the Django models."

    def add_arguments(self, parser):
        parser.add_argument("--output", help="File to write. Prints to the screen when omitted.")

    def handle(self, *args, **opts):
        models = sorted((m for m in apps.get_models() if local(m)), key=lambda m: (m._meta.app_label, m._meta.db_table))
        by_app = defaultdict(list)
        for m in models:
            by_app[m._meta.app_label].append(m)

        out = [INTRO, f"_Generated on {datetime.date.today().isoformat()}. {len(models)} tables._", "",
               "## Tables by module", "", "| Module | Tables |", "|---|---|"]
        for app, ms in by_app.items():
            out.append(f"| {APP_TITLES.get(app, app)} | " + ", ".join(f"`{m._meta.db_table}`" for m in ms) + " |")

        out += ["", "## Relationships", "",
                "Each line goes from the referenced (parent) table to the table that holds the foreign key. "
                "One parent can have many children. A circle on the parent side means the link is optional.", ""]
        for app, ms in by_app.items():
            out += [f"### {APP_TITLES.get(app, app)}", "", er_diagram(ms), ""]

        out += ["## Table reference", ""]
        for app, ms in by_app.items():
            out += [f"### {APP_TITLES.get(app, app)}", ""]
            for m in ms:
                out += [f"#### `{m._meta.db_table}` ({m._meta.object_name})", "",
                        "| Column | Type | Null | Notes |", "|---|---|---|---|"]
                for f in m._meta.concrete_fields:
                    out.append(f"| `{f.column}` | {column_type(f)} | {'yes' if f.null else 'no'} | {notes(f)} |")
                extras = [f"unique together: {', '.join(u)}" for u in m._meta.unique_together]
                for c in m._meta.constraints:
                    if c.__class__.__name__ == "UniqueConstraint":
                        extras.append(f"constraint `{c.name}`: unique on {', '.join(c.fields)}" + (" (partial, ignores rejected rows)" if c.condition else ""))
                extras += [f"index: {', '.join(i.fields)}" for i in m._meta.indexes]
                if extras:
                    out += ["", *[f"- {e}" for e in extras]]
                out.append("")

        text = "\n".join(out) + "\n"
        if opts["output"]:
            with open(opts["output"], "w", encoding="utf-8") as fh:
                fh.write(text)
            self.stdout.write(self.style.SUCCESS(f"Wrote {opts['output']} ({len(models)} tables)"))
        else:
            self.stdout.write(text)
