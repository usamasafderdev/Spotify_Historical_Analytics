# Final client handover checklist — 0.1.0

**BLOCKED — internal review only. Do not send the candidate to the client yet.** Status values: PASS, PARTIAL, BLOCKED, NOT TESTED. Current verification: [Phase 11 final acceptance](PHASE_11_FINAL_ACCEPTANCE.md). Earlier baseline: [Phase 10 acceptance](PHASE_10_RELEASE_ACCEPTANCE.md). The Phase 10 review folder remains an unchanged historical snapshot; this workspace checklist records current gates.

| Item | Status | Acceptance evidence / next action |
|---|---|---|
| Version and schema freeze | PASS | Version 0.1.0, production schema 2; preserve frozen SHA-256 identities. |
| Automated tests | PASS | Phase 10 full suite: 155 passed. Phase 11 targeted analytics/import/export: 52 passed in 4.11s. No production code change; independent oracles retained. |
| Packaged feature acceptance | PASS | All seven pages, synthetic preview, dates/search/sorting, details, imports, exports, backup/settings and return-to-real checked with isolated fixtures. |
| GUI screenshot inspection | PARTIAL | Windows Qt and native HWND screenshots opened and inspected. Human mouse/keyboard/focus/accessibility acceptance remains. |
| Physical Windows DPI | PARTIAL | Phase 11 read-only host observation: 1920x1080, 144 DPI/150%, no Qt override. Physical switching/matrix and manual acceptance remain NOT TESTED. Qt/window simulations do not fill missing results. |
| Clean Windows lifecycle | BLOCKED | Phase 11 found no usable authorized guest/tooling. HypervisorPresent=true is not a clean VM; Hyper-V namespace unavailable, vmcompute stopped. Do not provision or elevate without authorization. |
| Start Menu and standalone execution | PARTIAL | Phase 9 host shortcut targets and Python-free PATH launch passed for the same payload. Launch the actual installed app from Start on the clean VM. |
| Import/report acceptance | PASS | Synthetic fixtures, daily/weekly separation, accurate reopened CSV/XLSX, duplicates and rollback checked. |
| Client source decision | BLOCKED | Client must decide complete preloaded history versus client-supplied datasets. Do not choose on their behalf. |
| Historical coverage and rights | BLOCKED | Approve exact source versions/USA/cadence/coverage and permitted processing/commercial/export/distribution uses; verify stable metadata. No complete 2017-2026 coverage is asserted. |
| Dependency redistribution | BLOCKED | Complete native/transitive terms, notices and Qt source/replacement materials. Phase 11 records Qt PDF 6.140.0.0 versus other listed Qt 6.12.0.0, OpenSSL 3.5.5/3.0.18 and unknown exact libffi source version. Companion notices are not clearance. |
| Security review | PARTIAL | Scoped static/credential scan and input/export tests passed; broader assessment and optional bundled-module review remain. |
| Signing/publisher disposition | PARTIAL | Both artifacts unsigned. Obtain legitimate signing or explicit documented customer-policy acceptance; do not bypass controls. |
| User and schema documentation | PASS | Guide, installation/update instructions, metrics, supported columns and known limitations prepared. |
| Review handover folder | PASS | Setup, checksums, version/schema, documents, notices and QA summary prepared locally with a hash manifest. No raw local logs or research databases. |
| Client delivery authorization | BLOCKED | Resolve critical gates, obtain client acceptance and release-owner approval before sending. Nothing has been sent. |

## Clean-machine manual test procedure

1. Obtain access to an existing authorized clean Windows 10/11 x64 guest. Record its owner/authorization, OS build, tester/date, absence of Python/VS Code and a clean baseline. Create a VM snapshot or equivalent owner-approved recovery checkpoint before testing. Do not install virtualization software or change host hypervisor configuration without separate authorization. Use disposable synthetic data only; do not mount the host's real user-data/research directories for writes.
2. Copy the actual production `US-Music-Charts-Analytics-Setup.exe` into the guest. Run `Get-FileHash -Algorithm SHA256` inside the guest and verify `0D36E4A234D5425EF086EF8E2AE65EA5B184C3AF65205E4D63010473303C8D8D`. Record hash, OS and checkpoint ID. Install per user using normal approval/security processes, without disabling protections. Check Start Menu and optional Desktop shortcut, then launch from Start.
3. Visit every sidebar page. Check text, scrollbars, tab order, keyboard activation, focus visibility, date-calendar popup, sorting, tooltip/zoom behavior and details. Repeat at actual 1366x768, 1600x900 and 1920x1080 where available, with physical 100/125/150% settings. Record unavailable combinations as NOT TESTED.
4. Preview synthetic mode, change daily/weekly and date filters, search and sort, open details, export CSV/XLSX, and return to the real empty dashboard. Confirm labels distinguish synthetic results.
5. Import the explicitly synthetic example from the schema document under a clearly synthetic source name in the disposable environment. Verify 220 streams for song, artist and album. Repeat import and verify no increase. Test an invalid file and cancellation.
6. Export and reopen CSV/XLSX with a compatible viewer. Confirm dates, counts, headers and source/metric definitions. Check save-dialog and keyboard behavior; record the application's Qt chooser separately from a Windows shell chooser.
7. Back up, close/reopen and confirm database/settings persistence in Local AppData. Test a second simultaneous launch and migration/error recovery using disposable copies.
8. Uninstall. Verify application/shortcuts are removed while separate user data remains. Reinstall the same actual Setup and verify records/settings remain. Test an approved upgrade separately, retaining a verified backup.
9. Save sanitized evidence and sign off each item. A host-isolated test or removing Python from PATH cannot substitute for this procedure.

For each physical resolution/scaling combination, record the actual Windows
Display setting and restart/sign out if Windows requires it within the protected
test environment. Run the application without Qt scale overrides, capture the
result, and test labels/sidebar/charts/tables/dialogs, scrollbars, calendar,
mouse/keyboard/focus, exports and tooltips. Restore the guest/checkpoint or
original display state as agreed with its owner. Record unsupported settings
as NOT TESTED, not PASS.

## Human license and release evidence required

- Record the applicable license route per exact Qt DLL/plugin, including the
  PDF/PDFium build. Verify notices, license texts, corresponding-source or valid
  source-offer materials and usable replacement/relinking instructions as
  applicable. Check the proprietary application terms preserve library rights.
- Reconcile Python/native OpenSSL/libffi/Windows runtimes, PyQtGraph resources,
  vendored/optional modules and their required materials against actual hashes.
  An installed-distribution candidate list is not a complete SBOM.
- Record Inno license/organization-policy review and signing or accepted unsigned
  publisher policy. No purchase or legal approval is implied by these checkboxes.
- Obtain the client's dataset-scope decision and source-specific rights/coverage
  acceptance before describing the product as historical-data complete.

## Release-owner decision

Do not mark final delivery ready while the data decision, clean-machine lifecycle, required human desktop acceptance, or dependency obligations remain unresolved. Record signing/publisher policy explicitly. After any application/packaging change, rebuild and reverify the new artifact hashes; do not carry acceptance forward solely from a version string.
