# Changelog

All notable changes to this project are documented here. The project follows
Semantic Versioning.

## 0.1.3 - 2026-09-12

- Show the installed package version in the Django admin application heading.

## 0.1.2 - 2026-09-12

- Assign one or more access Groups to each exposed SRP fleet.
- Restrict fleet lists, detail pages, and submissions to the Groups mapped to
  that specific fleet.
- Migrate the previous global required Group onto every existing exposure to
  preserve access during upgrades.

## 0.1.1 - 2026-09-12

- Handle delayed, empty, malformed, non-JSON, failed, and timed-out zKillboard
  responses without exposing internal exceptions.
- Tell users to retry after five minutes when a new killmail is not available
  from the zKillboard API yet.
- Log upstream validation failures with the killmail ID and a safe reason code.
- Preserve built-in SRP request creation, authorization, and duplicate protection.

## 0.1.0 - 2026-09-12

- Add configurable State and Group authorization.
- Add mappings for explicitly exposed built-in SRP fleets.
- Add restricted fleet list, detail, and request submission views.
- Store submissions as normal Alliance Auth built-in `SrpUserRequest` records.
- Add server-side direct URL protection, administration, tests, packaging, and
  Trusted Publishing workflow.
