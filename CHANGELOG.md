# Changelog

## 2026-11-17 — compact document previews and prototype reconciliation

- Remove empty trailing rows within the spreadsheet preview range while preserving internal gaps, formulas, zero and boolean values; retain row, column and cell-size limits despite inaccurate workbook dimensions.
- Explain empty table previews and size file dialogs to their content, with bounded scrolling for long text and PDF pages.
- Reconcile the local prototype's missing worksheet-request ordering, XLSX-column and TSV-preview fixes using scoped functions and routes, preserving its unrelated defaults and caches.
- Add HTTP regressions with actual XLSX/CSV/TSV fixtures and verify document interactions and compact dialogs in isolated browser sessions.

## 2026-11-17 — index registered Harness handoff evidence

- Prefer registered Harness source paths, including Chinese names and nested folders, over conventional filenames; expose missing or invalid registrations without borrowing historical copies.
- Index current H5 YAML traceability manifests, H7 YAML figure registries and compact model/result-card summaries alongside legacy JSON captures. Preserve recorded statuses and distinguish an H5 verified record from a completed captured run.
- Keep discovered sources inside the project and prevent index output from overwriting source or control records, including hardlink aliases.
- Cover discovery, schema compatibility, source preservation and repeated builds in CI. The derived index remains a locator and report; it does not approve evidence or replace scientific checks.

## 2026-11-17 — remove merged H5 entry self-dependencies

- Require upstream problem and literature records at H5 entry; stop requiring method-transfer, blueprint and model-contract files as frozen inputs before the same solver creates them.
- Move design and handoff files into the fresh B-task output list, and align the solver warmup with H5's combined design-and-solve responsibility across all registered questions.
- Retain checks on every explicitly recorded legacy input, completed design artifacts, approved literature, result traceability and human approval. No new H4 gate or role is introduced.
- Test initial dispatch, internal design iterations, real project initialization and legacy hash protection; synchronize the scoped contract, templates and role instructions with the installed copy.

## 2026-11-17 — complete result interpretation handoff

- Require verified result interpretations for every registered question at the complete H6-to-writing handoff, and report out-of-scope question bindings instead of letting one question's cards stand in for another.
- Allow multiple distinct result cards per question. Keep legitimate H6 targeted rechecks limited to affected questions while restoring complete coverage at H7–H9.
- Reuse the existing result-card check and file hashes; add no agent, registration file or extra checkpoint. Link H5 preparation to the canonical author-evidence protocol.
- Add handoff regressions and synchronize the affected checker function and instructions with the installed skill without copying unrelated local files.

## 2026-11-17 — current Harness question records in the workbench

- Read structured subproblem IDs and current H1 question profiles alongside legacy records, without expanding the registered contest scope.
- Display current H5 model purpose, formulation, solver method and result interpretations; keep numeric results absent when they were not recorded and retain explicit draft status.
- Link recorded result evidence and canonical figure bindings to the correct question. Explicit bindings take precedence over figure-name hints, and missing or external files remain excluded.
- Cover current skill templates, legacy compatibility, read-only inputs and escaped frontend content with regression tests; apply the same scoped fix to the local prototype.

## 2026-11-17 — test environment dependencies

- Install `pypdf` before the figure-registry CI checks import the delivery module, and align the documented local test setup with CI.
- Recheck the figure-registry suite after the dependency fix; no contest records or delivery checks are bypassed.

## 2026-11-17 — reuse question-scoped sensitivity evidence

- Let one sensitivity report serve H5 traceability and multiple questions by binding each result row to its subproblem; retain single-question header compatibility.
- Check only the requested question's rows and search past reports explicitly belonging to other questions. Keep the first matching report authoritative even when it is incomplete.
- Require real perturbation records and reject missing or conflicting question bindings, while preserving zero-valued objectives and infeasible-scenario records.
- Document one report schema and add the cross-question contract regressions to CI; no project results or approvals are rewritten.

## 2026-11-17 — reduce repeated evidence reads

- Reuse unchanged file digests within one Harness control check, while reevaluating every validation and approval condition. Discard the cache when the call finishes or raises an exception.
- Invalidate entries after edits, replacements or deletions; use Windows file change metadata to detect same-size edits even when modification time is restored. Recompute when reliable metadata is unavailable.
- Add regressions for cache lifetime, nested checks, concurrent changes during a read, restored timestamps and missing metadata. Human approvals, independent verification and the complete H9 gate remain required.

## 2026-11-17 — clean initial contest state

- Start new B projects with pending stages, empty approvals, role instances and execution history; keep H4 merged into H5 and preserve chapter-parallel writing configuration.
- Remove prefilled scientific conclusions, result values, sensitivity runs, figure QA and stale example digests from startup scaffolds. Leave verification identity and time unrecorded until work actually occurs.
- Clear fabricated bootstrap records in the general Harness template and mark the global-interface template as awaiting verification. Existing project files and historical approvals are not migrated or rewritten.
- Align fresh visual-plan templates with the current TikZ route, matching the installed skill while preserving historical delivery compatibility.
- Test that freshly initialized projects cannot pass H5, H6, H8 or H9 without real work and evidence.

## 2026-11-17 — preserve project inputs during initialization

- Check all B-project template destinations and the generated README before writing; refuse existing files, directory conflicts and redirected template directories instead of overwriting contest records.
- Replace placeholders only in newly copied templates, leaving pre-existing input files and their modification times unchanged. Keep task-card hash refresh and empty template directories.
- Add initialization regressions to CI, including repeated runs, existing approval logs and linked directories.

## 2026-11-17 — Harness recheck compatibility

- Confine both current and legacy targeted recheck cards to H6; subsequent model, evidence and delivery checks retain the complete project scope.
- Apply the same trigger, evidence-field and registered-subproblem validation before a historical scope can reduce H6 work, while preserving the original records.

## 2026-11-17 — legacy figure registry migration

- Preserve recorded figure paths, decision cards, QA, custom metadata and registry metadata when preparing a v2 migration candidate; repeated previews retain the original provenance.
- Leave unknown layout and review facts pending instead of fabricating them. Reject duplicate IDs or malformed entries without writing a candidate.
- Protect the original registry, including file aliases, and existing default candidates from accidental overwrite; add migration and provenance checks to CI.

## 2026-11-16 — contest orchestrator 4.19 development

- Align the skill version across its entrypoint, manifest and version file; the merged H4/H5 workflow remains a development version pending complete release verification.
- Resolve the academic-writing adapter in both categorized repositories and flat installations so isolated replays use the intended skill.

## 2026-11-15 — repository maintenance

- Fail LaTeX reference checks when included source or declared bibliography files are missing, while ignoring commented-out includes.
- Preserve legacy `.svg` paths in the CUMCM `\figplot` interface instead of silently displaying a missing-image placeholder.
- Check HTML image references throughout public documentation, including the homepage, against tracked files.
- Allow same-origin workbench actions through either `localhost` or `127.0.0.1`, while rejecting mismatched origins.
- Restrict workbench HTTP host headers to loopback addresses to protect local project data from requests using unrelated hostnames.
- Bring the public CUMCM template layout adapter in line with its documented SVG commands and non-forced table placement.
- Preserve visible Excel columns when a workbook declares an incorrect sheet dimension, while keeping preview limits.
- Keep Excel preview on the latest selected sheet when earlier requests finish out of order.
- Reorganize the homepage around the workbench preview, task-based entry points and a shorter installation path, using the existing workbench mark.
- Record the selected ModelViz template source and SHA-256 in the adaptation handoff, and make test fixture imports independent of installed packages named `tests`.
- Add a synthetic workbench project and actual overview screenshot, with a quick route from the homepage to trying the demo.
- Mark historical JSON reports with conflicting duplicate fields as unreadable instead of silently showing a potentially misleading pass result.
- Reject duplicate fields in role-session JSON records before saving, preserving existing session history for manual recovery.
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
