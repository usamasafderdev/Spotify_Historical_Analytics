# Phase 10 release acceptance and handover preparation

2026-10-26, Windows 11 Pro x64 developer host, OS 10.0.26300. **Final client delivery: BLOCKED.** The frozen Phase 9 candidate remains useful for internal review. Nothing was published or sent to the client.

Status vocabulary: **PASS** = the stated scoped check succeeded; **PARTIAL** = limited evidence or unresolved work; **BLOCKED** = required external acceptance/decision/material is unavailable; **NOT TESTED** = the check was not performed. PASS does not imply complete data coverage, legal clearance, or clean-machine compatibility.

## 1. Final application version and freeze — PASS

Application **0.1.0**, production SQLite `PRAGMA user_version = 2`; local import staging schema 2, import adapter 3. Schema version was checked on a newly created isolated reference database. Existing user/research databases were not deleted, migrated, overwritten or imported into production during this phase.

Git HEAD at entry was `12e9286825d2ca3e8342a0b486aa33e24fb6b2d5`, with the shared Phase 9 working tree still dirty. This is not a clean tagged-source release. Existing Phase 9 application and packaging changes were preserved. Phase 10 added verification scripts/documentation and did not alter application functionality, application source, or packaging configuration. No rebuild was necessary; the exact existing EXE and installer were reverified. Artifact hashes, rather than the version string alone, identify this candidate.

| Frozen artifact | Bytes | SHA-256 |
|---|---:|---|
| `dist/USMusicChartsAnalytics/USMusicChartsAnalytics.exe` | 19,603,761 | `6710EB8DF605308F1F244D9A4D8B60EC1730BD35132258B47C6CC8C2EC5ECF32` |
| `dist/installer/US-Music-Charts-Analytics-Setup.exe` | 77,826,840 | `0D36E4A234D5425EF086EF8E2AE65EA5B184C3AF65205E4D63010473303C8D8D` |

Entry freeze evidence: [freeze.json](screenshots/phase10/freeze.json). Tests and known limitations were carried forward and independently rechecked as described below. No automatic commit or client data-delivery decision was made.

During verification, the shared repository HEAD moved to
`9631de5b78e8588f96fa6c34b0a3865291103a68` (`Add Phase 9 validation and installer safeguards`).
This acceptance workflow issued no commit command and preserved that shared
change. Both frozen artifacts and their manifests still match. This report is
an artifact acceptance freeze, not a claim that the shared Git tree stayed
unchanged or became a clean release tag. [Final verification](screenshots/phase10/final-verification.json)
records both HEAD values.

## 2. Feature acceptance — PASS within synthetic scope

| Feature | Status | Evidence |
|---|---|---|
| Overview and all seven sidebar pages | PASS | Frozen packaged EXE navigated with Windows Qt, real empty states and populated synthetic preview. |
| Songs, artists, albums | PASS | Independent Python arithmetic tests; packaged tables, sorting/search, and detail windows. |
| Numeric stream totals | PASS | Daily US oracle: 420; songs 220/80/120, full-credit Alice 300/Bob 220/unresolved 120, album editions 300/220. Canadian 9,999 and weekly 900 separated; synthetic inclusion explicit. |
| Collaborations and exact album mapping | PASS | Duplicate supplied relationships deduplicated; whole-credit fallback retained; same-name distinct album IDs remain separate. |
| Inclusive ranges / daily-weekly | PASS | Boundary/empty-period tests and packaged filter transitions. No artificial missing observations. |
| Duplicates / search | PASS | Import idempotency/conflict tests and packaged song search, no-result state, numeric sort. |
| Demo / return to real | PASS | Isolated temporary generated data, clear labels, parsed demo exports; isolated normal database remains empty after return. |
| Settings / backup / restart | PASS | GUI save action and integrity check, remembered export folder, database reopen; separate packaged restart smoke. |
| Complete historical-data acceptance | BLOCKED | No approved complete historical dataset; pending client scope/permissions. |

Independent oracles remain in `tests/test_phase9_correctness.py`; expected dictionaries use Python tuples/arithmetic, not the SQL under test. This phase did not replace them with screenshots or self-validating SQL expectations.

## 3. GUI inspection — PARTIAL

The actual frozen packaged Windows EXE was launched again using the **windows** Qt platform. Three fresh runs constrained the main window for 1366x768, 1600x900, and 1920x1080 at host Qt device pixel ratio **1.5**. Logical sizes were 862x432, 1018x520, and 1200x640, reserving physical titlebar/taskbar space. No Windows display mode was changed. All seven pages, scrolling, filters, search/sorting, details, Qt Save controls, backup, demo/return, import and error flows were exercised using widget automation.

Screenshots were actually opened and inspected: [contact sheet](screenshots/phase10/inspection.jpg), [narrow layout](screenshots/phase10/gui-1366x768/demo-01.png), [bar chart](screenshots/phase10/gui-1920x1080/demo-01-content.png), [album detail](screenshots/phase10/gui-1920x1080/detail-albums-desktop.png), [import result](screenshots/phase10/import/06-import-result.png), and [date error](screenshots/phase10/gui-1920x1080/invalid-date-error.png). Contrast, wrapped notice, numeric bar axis, value labels, scrollbars and fixed Close control were readable in the inspected images. No additional visible defect was identified in this scoped pass.

Images ending `-desktop` capture the application's actual HWND with PrintWindow; other images are QWidget captures. This is graphical evidence, but **not manual mouse/keyboard acceptance**. No configured desktop-control connector was available. Calendar-popup interaction, tab order/focus, manual mouse/hover/zoom, accessibility, multiple monitors and native Windows shell choosers remain NOT TESTED. The application's Qt widget file chooser was exercised. Dialog bounds use the real host monitor's available geometry, not a simulated smaller monitor.

## 4. Independent clean Windows VM — BLOCKED

Discovery found no configured `WindowsSandbox.exe`, `vmconnect.exe`, `VBoxManage.exe`, `vmrun.exe`, or `Get-VM` command, nor an accessible configured environment in the checked common VMware/VirtualBox/Hyper-V locations. This does not establish that no VM exists elsewhere; no usable authorized clean VM was available to this session.

The actual production Setup was **not installed on a clean OS** in Phase 10. Start Menu launch, absence of Python/developer runtimes, fresh installation/import/export, uninstall/reinstall and retained data on an independent Windows 10/11 environment remain manual blockers. No virtualization software was installed, configured or elevated. Developer-host isolation is not a clean-machine result.

## 5. Physical display DPI — NOT TESTED

No physical Windows resolution/scaling setting was changed. The fresh Phase 10 checks use main-window constraints at host Qt DPR 1.5. Phase 9's nine combinations used Qt scale-factor simulation, not physical DPI changes. Human acceptance at actual 100%, 125%, and 150% and supported physical resolutions remains required where available. No true DPI pass is claimed.

## 6. Import/export and source readiness — PASS for compatible synthetic files

The packaged importer processed 4 generated fixture rows: 2 valid USA, 2 rejected, 1 inserted and 1 duplicate skipped. Integrity was `ok`; changed bytes blocked final import and cancellation was safe. Unit/service checks also cover CSV/GZ/XLSX, explicit weekly intervals, metadata conflicts and transaction rollback. The GUI fixture is synthetic and separate from the normal user database.

Each of the three packaged GUI runs created and reopened **12** date-filtered demo reports: songs/artists/albums, daily/weekly, CSV/XLSX. Independent arithmetic checks reopen real/demo reports and verify numeric columns, metadata and formula escaping. Excel desktop visual review remains NOT TESTED.

The separately documented synthetic schema sample was imported into a new isolated test database: 2 rows, 220 song streams, 220 artist streams, 220 album streams, repeat import 0 additions, SQLite integrity `ok`. This directly validates the guide's example without importing research history. [Schema sample result](screenshots/phase10/schema-sample.json).

The Windows application supports local compatible imports without Python or VS Code. [SUPPORTED_DATA_SCHEMA.md](SUPPORTED_DATA_SCHEMA.md) documents required date/title/credit/streams/country, formats, exact artist/album associations, cadence/coverage semantics, duplicate/source constraints and capacity considerations. This is readiness to accept compatible files, not approval of any source's commercial rights.

## 7. Fresh development checks — PASS

- `python -m pytest -q`: **155 passed in 236.62 seconds**, including 25k/100k/500k cases.
- `python -m compileall -q src scripts tests`: passed; repeated after adding Phase 10 verification scripts.
- `git diff --check`: passed.
- Existing packaged startup/restart, persistence, integrity, six ranking CSV/XLSX exports and demo smoke were rerun without rebuilding.

The performance cases are synthetic functional scaling checks, not a new controlled optimization benchmark or proof of client-device latency. Phase 9's insertion/RAM/performance limitations remain. Detailed local evidence: [acceptance.json](screenshots/phase10/acceptance.json); the local test transcript remains under `build/phase10/pytest.log` and is excluded from the handover folder.

## 8. Installer verification — PARTIAL

The exact requested Setup exists, is 77,826,840 bytes, and matches its sibling checksum and the entry freeze. The full portable-folder `SHA256SUMS.txt` is rechecked before handover. Both public binaries report `NotSigned`.

Phase 9's isolated host installation, shortcut targets, Python-removed-from-PATH launch, package-version upgrade, persistence/export/demo, and uninstall/data-retention results still apply to the **identical frozen payload**. Those tests used a QA GUID/name and the same application payload; they are not an independent installation of the actual production Setup identity or a clean-machine test. Phase 10 did not repeat or relabel that earlier lifecycle as a fresh clean-OS pass. A clean-VM install/uninstall/reinstall procedure is in the handover checklist.

## 9. Final installer hash — PASS

`US-Music-Charts-Analytics-Setup.exe`:

```text
0D36E4A234D5425EF086EF8E2AE65EA5B184C3AF65205E4D63010473303C8D8D
```

The review folder contains the same bytes and a matching `.sha256` file. Hash equality establishes artifact identity, not publisher authenticity or safety.

## 10. Release security — PARTIAL

`scripts/audit_release.py` inspected bundled application code constants/source filenames and selected text resources: no common credential-pattern candidates and no application developer-path candidates were found. Resource/dataset inventory was rechecked; the only CSVs are upstream color maps. Default data routing is per-user AppData and all acceptance writes were isolated. Imports bind SQL values, do not execute file-provided code or extract archives to cell-supplied paths, and preserve transactional cancellation/rollback. Formula escaping and atomic export failure behavior remain tested.

This is not exhaustive credential detection or a vulnerability certificate. Logs can contain selected local paths/parser details and must be reviewed before sharing. Optional bundled roots include `debugpy`, `ipykernel`, `requests`, `aiohttp`, and `cryptography`; no application startup of a debugger/network service was identified, but this increases review scope. No credentials were printed, protections bypassed, or user data removed. See [security and license review](PHASE_10_SECURITY_AND_LICENSE_REVIEW.md) and [machine inventory](screenshots/phase10/security-inventory.json).

The handover scan caught local-path strings in supplemental vendor bytecode
accidentally selected from a namespace named `licenses`. The companion collector
was fixed to exclude code/bytecode before final verification. The final review
folder has zero matches for the scanned credential patterns, workspace root or
developer account string. Ten entry/bootstrap scripts were also inspected for
developer-path constants with no matches. These remain scoped findings, not an
exhaustive binary or secret-free certification.

## 11. Dependency-license clearance — BLOCKED

The exact frozen build's 15-distribution core inventory and available notices were inspected. It contains 45 core notice files but does not cover every optional/native/transitive component. Available supplemental distribution notices are collected alongside the frozen installer in the review folder; namespace-to-installed-distribution mapping can over-identify packages, so it is not an exact SBOM. The frozen installer's internal notice set is unchanged.

Open items include per-Qt-module license choice, required license texts, applicable corresponding-source/source-offer and replacement/relinking instructions, native runtime/OpenSSL/libffi notices and terms, and vendor/optional-module notices. Qt Virtual Keyboard remains absent. PyInstaller's commercial bundling exception does not clear dependency terms. Inno's purchase request is distinguished from its FAQ's statement that purchase is not strictly required. No commercial purchase or license-key changes were made. Primary official sources and exact scope are recorded in [the review](PHASE_10_SECURITY_AND_LICENSE_REVIEW.md). No legal certification or proprietary-distribution approval is claimed.

## 12. Documentation and handover — PASS for preparation

Updated the existing user guide with schema reference and update instructions. Added supported schema, known limitations, security/license review, this acceptance report and [FINAL_CLIENT_HANDOVER_CHECKLIST.md](FINAL_CLIENT_HANDOVER_CHECKLIST.md). The checklist uses PASS/PARTIAL/BLOCKED/NOT TESTED and includes an executable human clean-machine/DPI acceptance procedure.

Prepared folder: `dist/handover/USMusicChartsAnalytics-0.1.0-review/`. It contains the frozen production Setup, its checksum, full file hash manifest, user/installation/update instructions, version/schema information, supported data schema, metrics, known limitations, core and available supplemental notices, a sanitized QA summary and final checklist. It is explicitly marked **INTERNAL REVIEW ONLY — DO NOT SEND TO CLIENT**.

Final folder: **170 files including the manifest**, with 114 available
supplemental notice documents across 68 distribution candidates. Candidate count
is not a claim that every shared-namespace distribution is shipped in full.
Both the complete handover manifest and original portable-folder manifest were
rechecked, as were document links and forbidden data/log/code files in the
companion folder. [Package verification](screenshots/phase10/package-verification.json)
and [handover receipt](screenshots/phase10/handover.json) record the results.

The packaging script uses a document/artifact allowlist. No research staging database/archive, genuine historical dataset, raw development log, credentials, private workspace screenshot, or synthetic fixture masquerading as historical data is included. Synthetic examples in the schema documentation are explicitly labeled. The installer internally retains generated demo capability and public library color-map resources. Nothing was sent or published.

Phase 10 updated `README.md`, `docs/USER_GUIDE.md`, `docs/WINDOWS_INSTALLATION_GUIDE.md`, `docs/DEPENDENCY_LICENSES.md`, and `docs/CLIENT_HANDOVER_DRAFT.md`. It added `docs/PHASE_10_RELEASE_ACCEPTANCE.md`, `docs/FINAL_CLIENT_HANDOVER_CHECKLIST.md`, `docs/SUPPORTED_DATA_SCHEMA.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/PHASE_10_SECURITY_AND_LICENSE_REVIEW.md`, `docs/screenshots/phase10/` evidence, `scripts/audit_release.py`, and `scripts/prepare_handover.py`. Pre-existing dirty application/packaging files are Phase 9 work; no Phase 10 application feature change was made.

## 13. Outstanding historical-data dependency — BLOCKED

The client still must decide complete preloaded history versus client-supplied imports. No decision was inferred from silence. No MGD+, Dhruvil or Zenodo research records were imported into production or bundled. Source years, USA/cadence semantics, completeness, corrections, metadata associations and permitted acquisition/processing/commercial/export/redistribution uses need source-specific approval. Compatible-file support and source attribution do not establish permission or complete 2017-2026 history.

## 14. Exact release blockers and disposition — BLOCKED

1. Client data-delivery decision, approved source rights and verified actual coverage/metadata are unresolved.
2. No authorized clean Windows VM lifecycle acceptance of the actual production Setup, including Start Menu launch, standalone behavior, persistence, uninstall/reinstall and retained data.
3. Required human desktop, keyboard/focus/accessibility and actual display/DPI acceptance remain incomplete; native shell chooser and Excel viewer checks were not performed.
4. Dependency redistribution obligations and complete native/transitive notice/source/replacement materials require human review; the installed core notices alone are insufficient evidence of clearance.
5. Both binaries are unsigned. Obtain legitimate signing or explicit documented customer security-policy disposition; do not bypass protections. This is a policy/signing decision, not a claim that unsigned test candidates cannot exist.
6. Client/release-owner acceptance and authorization to send have not been given. No distribution has occurred.

**Disposition: internal review package prepared; final client delivery remains blocked.** Resolve and record these gates against the exact hashes. Any later application/packaging change requires a rebuilt artifact, new hashes and relevant repeated acceptance checks.
