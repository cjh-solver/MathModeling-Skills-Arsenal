# Changelog

## 2026-11-15 — repository maintenance

- Refresh the project homepage, installation guidance, contribution entry points and maintenance documentation.
- Document the current focused checks and the separate full-release blockers; keep historical validation results dated.
- Add the public-experience importer regression tests to CI and specify the Node.js version used by workbench tests.

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
