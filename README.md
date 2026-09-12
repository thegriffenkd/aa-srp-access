# aa-srp-access

`aa-srp-access` is a standalone Alliance Auth application that provides a
restricted frontend for Alliance Auth's built-in Ship Replacement Program
(SRP). It does not replace the built-in SRP backend or administration.

Restricted users can access the frontend only when both conditions are true:

- their Alliance Auth State is eligible; and
- they belong to a Django/Alliance Auth Group assigned to the requested fleet.

They see only built-in SRP fleets explicitly exposed to one of their Groups by
an administrator. Different Groups can therefore have separate fleet lists,
while a fleet may deliberately be shared with multiple Groups.
Requests are stored as normal built-in `SrpUserRequest` records, so existing
SRP administrators continue to approve, reject, update, and pay them through
the normal Alliance Auth SRP interface.

## Compatibility

- Alliance Auth `5.2.x`
- Python `3.10` through `3.14`, matching Alliance Auth 5.2 metadata
- Django `5.2.x`, supplied by Alliance Auth

The initial compatibility target is Alliance Auth 5.2.0. Test upgrades before
changing either the Alliance Auth or app version constraint.

## Security model

Every plugin view performs server-side authorization. Navigation visibility is
only a convenience and is not treated as access control. A submitted fleet ID
is re-queried through the authorized fleet queryset, and an unexposed fleet
returns a safe 404. Anonymous users are redirected to login; authenticated
users who fail the State or Group check receive 403.

State, Group, and fleet names are never authorization constants. Configuration
uses database relations to `authentication.State`, per-fleet `auth.Group`
mappings, and the built-in `srp.SrpFleetMain` model.

## Requirements

- A working Alliance Auth 5.2 installation with built-in SRP enabled
- Django admin access
- The built-in `auth.srp_management` permission for app configuration

## Installation

Add a pinned release to the Alliance Auth requirements file:

```text
aa-srp-access==0.1.3
```

Add the Python module to local settings:

```python
INSTALLED_APPS += [
    "srp_access",
]
```

Rebuild the application image, then run:

```bash
python manage.py migrate srp_access
python manage.py collectstatic --noinput
```

Restart the web, worker, and scheduler processes using the deployment's normal
procedure. No Alliance Auth core files or core migrations are changed.

## Docker installation

Service names vary between deployments. From the correct Compose project
directory, the usual sequence is:

1. Add `aa-srp-access==0.1.3` to `conf/requirements.txt`.
2. Add `srp_access` to `INSTALLED_APPS` in local Django settings.
3. Rebuild the Alliance Auth image with `docker compose build`.
4. Run `docker compose run --rm <web-service> python manage.py migrate srp_access`.
5. Run `docker compose run --rm <web-service> python manage.py collectstatic --noinput`.
6. Recreate the web, workers, and beat/scheduler services.
7. Verify container health and both the standard and restricted SRP pages.

Back up the database and configuration first. Determine the correct Compose
project and service names before running commands; do not copy the examples
blindly into a production deployment.

## Initial configuration

1. Sign in to Django admin as a staff user with `auth.srp_management`.
2. Open **Restricted SRP settings**.
3. Choose State behavior:
   - enable **allow any public state** to require `State.public=True`; or
   - disable it and select one or more specific State objects.
4. Add **Exposed SRP fleet** rows for existing built-in SRP fleets.
5. On each exposure, select the Group or Groups allowed to see that fleet.
6. Leave an exposure enabled only while that fleet should be available.

An exposure with no selected Groups is inaccessible by design.

An exposed fleet must also be open in built-in SRP: it needs a non-empty SRP
code and an incomplete status. Disabling or completing it in built-in SRP
removes it from the restricted list without deleting the exposure mapping.

## Permissions and groups

Access Groups are application data selected separately on each fleet exposure;
their names are not fixed. State eligibility and membership of at least one
Group assigned to the requested fleet are both mandatory. Superuser or staff
status does not bypass the restricted frontend's State-and-Group rule.

Configuration in Django admin is guarded by Alliance Auth's existing
`auth.srp_management` permission. Normal built-in SRP permissions and pages are
not modified.

## How to expose fleets

Create fleets through the normal built-in SRP interface. In Django admin, add
an **Exposed SRP fleet** mapping, select the existing fleet object, and select
its access Groups. The one-to-one relation prevents duplicate fleet mappings.
Removing a built-in fleet also removes its exposure mapping; it does not affect
unrelated SRP data.

## Upgrading

1. Back up the Alliance Auth database and configuration.
2. Pin the desired `aa-srp-access` version in requirements.
3. Rebuild the image.
4. Run `python manage.py migrate srp_access`.
5. Run `collectstatic` when release notes require it.
6. Recreate services and verify both SRP frontends.

When upgrading from 0.1.1, the migration copies the previous global required
Group to every existing fleet exposure before removing the global field. You
can then split those mappings into separate Groups in Django admin.

Test Alliance Auth upgrades on a test server with the currently pinned plugin
version before upgrading production.

## Uninstall considerations

Removing the app does not remove built-in SRP fleets or requests. Plugin-owned
settings and exposure mappings remain in the database unless their tables are
explicitly removed. Back up first; do not reverse migrations casually on a
production installation. Remove `srp_access` from `INSTALLED_APPS` only after
planning whether to retain or remove those plugin tables.

## Development and testing

Run tests against a Redis instance on localhost database 15:

```bash
python -m django test srp_access.tests --settings=testauth.settings
```

Build and validate distributions:

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

The test suite uses SQLite and arbitrary fixture names. It covers anonymous,
State, per-fleet Group isolation, migration of legacy Group mappings, direct
URL protection, submission, built-in SRP regression, and built-in administrator
behavior.

## Release process

Update the changelog and version, merge tested changes, and create a deliberate
GitHub Release. The release workflow builds and validates wheel/sdist artifacts
before publishing through a PyPI Trusted Publisher and the protected `pypi`
GitHub environment. Ordinary pushes never publish.
