# Changelog

## 2026-11-15 — repository maintenance

- Surface unreadable or malformed project role registries without hiding valid manual session links.
- Repair tech-route-maker links and example commands for clean checkouts; validate documentation targets against the Git index rather than ignored local files.
- Restore Darwin Skill's MIT license and bilingual diagrams; validate links in all skill README variants.
- Report duplicate YAML fields in project records rather than silently replacing their values; retain standard YAML merge overrides.
- Detect YAML mapping keys that would collide in JSON, reporting the issue instead of silently dropping a modeling result.
- Keep Harness control, role and approval records within the selected project boundary, including when symbolic links are present.
- Remove unavailable ModelViz showcase image references and point readers to a clearly labeled reproducible example; check skill README image paths in repository validation.

- Teach the orchestrator health check to distinguish categorized repository packages from a flat skill installation; repository presence does not certify installation.
- Refresh the project homepage, installation guidance, contribution entry points and maintenance documentation.
- Document the current focused checks and the separate full-release blockers; keep historical validation results dated.
- Add the public-experience importer regression tests to CI, specify the Node.js version used by workbench tests and update the official GitHub Actions used by the workflow.

## 2026-11-13 to 2026-11-15 — workbench and experience import

- Keep the selected project stable during asynchronous refresh, preserve recoverable role-session registrations and show a clear warning when a registration file cannot be read.
- Improve Chinese text preview, file recommendations and access to registered paper evidence when the file scan is incomplete.
- Check chapter-prompt preparation against recorded approvals, hashes, timing and visual-plan requirements before offering a manual copy action. These checks do not replace the Harness gates.
- Preserve model-limitations text in public-case imports and prevent imports from overwriting existing cases or review manifests; existing damaged text was restored against the original public dataset.

## 2026-11-12 — local Harness workbench

- Add a Chinese local viewer for existing Harness projects, with per-tab project selection, automatic read-only refresh and document previews.
- Document setup, contest use, privacy boundaries and verification; the workbench does not replace human approval or run contest tasks.
- Update repository links to the current GitHub account.

## 2026-11-01 — public packaging verification

- Refresh the TikZ catalog and ten hash-verified starter files used by the current workflow.
- Support the repository's category layout in the route-diagram test fixture, while retaining the installed flat layout.
- Run behavior checks against the public, sanitized copy and publish the result summary.

## 2026-10-31 — workflow and documentation update

- Sync the recent scoped MathorCup evidence, reproduction, role-registration and writing improvements across six skills.
- Add chapter-approved writing and parallel figure revisions for new Harness and MathorCup controls; preserve historical workflow records.
- Add a task-oriented README, copyable prompts, a reproducible synthetic chapter example and explicit validation limits.
- Add repository hygiene checks, focused workflow CI and structured issue templates.
- Preserve existing version registrations and third-party licenses. This update is not a new fully validated stable orchestrator release.
