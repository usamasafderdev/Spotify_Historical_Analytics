# Phase 11 final acceptance and release blockers

2026-10-26 — US Music Charts Analytics **0.1.0**, production schema **2**.
**Human client delivery: BLOCKED; not approved.** No application or packaging
source was changed, no binaries were rebuilt, and no production/research data
was changed. Nothing was sent, published or purchased.

The Phase 10 acceptance report, handover checklist and security/license review
were read. PASS means the specified check succeeded within its scope; PARTIAL
means acceptance is incomplete; BLOCKED means a required environment, decision
or approval is unavailable; NOT TESTED means the action was not performed.

## 1. Frozen release identity — PASS

Both artifacts still match Phase 10 exactly:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `dist/USMusicChartsAnalytics/USMusicChartsAnalytics.exe` | 19,603,761 | `6710EB8DF605308F1F244D9A4D8B60EC1730BD35132258B47C6CC8C2EC5ECF32` |
| `dist/installer/US-Music-Charts-Analytics-Setup.exe` | 77,826,840 | `0D36E4A234D5425EF086EF8E2AE65EA5B184C3AF65205E4D63010473303C8D8D` |

The portable-folder and Phase 10 review-folder SHA256SUMS manifests were also
rechecked. The review folder remains the Phase 10 snapshot; it was not
regenerated or relabeled as a Phase 11 approved delivery. Current acceptance is
this report and the updated workspace checklist. Artifact identity does not
establish publisher trust, source rights or clean-machine compatibility.

## 2. VM availability and clean installation — BLOCKED

Read-only discovery on this HP EliteBook / Windows 11 Pro 10.0.26300 found:

- No `WindowsSandbox.exe`, `vmconnect.exe`, `VBoxManage.exe`, `vmrun.exe` or
  `Get-VM` command. Explicit standard Windows/VirtualBox/VMware and per-user
  VirtualBox executable checks were also negative.
- No VirtualBox user configuration or VM folders at the checked standard
  Documents locations.
- Hyper-V's `root/virtualization/v2` management query returned **Invalid
  namespace**. `vmcompute` exists but is **Stopped**. No `vmms` service was
  returned by the service query.
- The computer reports `HypervisorPresent = true`. This alone does **not**
  identify an available clean guest, management tooling, or authorization to
  reconfigure virtualization.

No usable authorized clean Windows 10/11 x64 environment was discovered. This
does not prove that no VM exists elsewhere. No service was started, hypervisor
setting changed, virtualization software installed, elevated action requested,
or VM snapshot taken. [Environment evidence](screenshots/phase11/environment.json).

| Clean-machine action | Status |
|---|---|
| Find an available authorized clean guest | BLOCKED |
| Snapshot/protect guest and copy actual frozen Setup | NOT TESTED |
| Install and launch actual production Setup from Start Menu without developer tools | NOT TESTED |
| Clean-guest pages/demo/import/export/persistence | NOT TESTED |
| Clean-guest uninstall/reinstall and user-data retention | NOT TESTED |

Precise manual steps, expected synthetic counts and required evidence are in
the [handover checklist](FINAL_CLIENT_HANDOVER_CHECKLIST.md). Developer-host
isolation and removing Python from PATH remain supporting evidence only.

## 3. Actual Windows GUI testing — PARTIAL

The **actual frozen packaged EXE** was launched on the existing desktop using
the Windows Qt platform and an isolated data-directory override. The existing
acceptance runner exercised all seven pages, empty states, synthetic preview,
search/no-results, numeric sorting, daily/weekly/date filters, details, scrolling,
Qt save controls, backup, settings persistence and return to real empty data.
It produced and reopened **12 demo CSV/XLSX reports**, with no runner errors;
the isolated normal database remained at zero observations.

Screenshots were actually opened and inspected: [contact sheet](screenshots/phase11/inspection.jpg),
[native window](screenshots/phase11/gui/demo-01-desktop.png),
[numeric chart](screenshots/phase11/gui/demo-01-content.png) and
[album detail](screenshots/phase11/gui/detail-albums-desktop.png).
The inspected labels, charts, notice, scrollbar and Close control were readable.
No new functional/visual defect requiring a binary change was identified in
this scoped check. [GUI results](screenshots/phase11/gui/results.json).

This was widget-driven automation with actual Windows HWND/QWidget captures,
not manual desktop acceptance. Calendar popup operation, physical mouse clicks,
tab order/keyboard activation, focus behavior, tooltip/zoom interactions,
accessibility and manual file-chooser behavior remain **NOT TESTED** in Phase 11.
The application uses a Qt widget chooser; a Windows shell chooser was not
substituted or tested. Earlier screenshots/tests are not relabeled as manual
interaction evidence.

## 4. Physical display and DPI — PARTIAL baseline; matrix NOT TESTED

A read-only Windows/Qt observation, with Qt scaling overrides removed for that
observation, reported **1920x1080**, **144 DPI** for the created window, and Qt
device pixel ratio **1.5**. These values describe the current host's 150% setting.
No Windows display configuration was changed. The GUI run used a 1200x640
logical main window; screenshots do not establish full-screen acceptance at
other resolutions. [Display snapshot](screenshots/phase11/display.json).

| Actual resolution / scaling acceptance | 100% | 125% | 150% |
|---|---|---|---|
| 1366x768 | NOT TESTED | NOT TESTED | NOT TESTED |
| 1600x900 | NOT TESTED | NOT TESTED | NOT TESTED |
| 1920x1080 | NOT TESTED | NOT TESTED | PARTIAL: current host observation and window captures |

Only the active user's desktop was available, with no isolated guest/display
session and tested recovery path for changing configurations during ongoing
work. Physical resolution/scaling switches were therefore not attempted.
Prior `QT_SCALE_FACTOR` runs and window resizing remain simulations; they do
not fill any missing physical matrix result. A human tester must complete
the requested settings and mouse/keyboard/focus checks in the protected test
environment, recording unsupported combinations as NOT TESTED.

## 5. Installer lifecycle and signing — PARTIAL

The actual production Setup file was verified by size/hash and Authenticode.
It was not newly installed on the live host or on a clean guest. Phase 9's
isolated QA-identity installation, shortcuts, upgrade, persistence and uninstall
results still concern the same frozen payload, but do not prove a clean-machine
production-identity installation. Reinstall/data-retention acceptance on the
required guest remains NOT TESTED.

Both EXE and Setup report **NotSigned**. No signing credentials were available
or used. Signing with legitimate release-owner credentials, or explicit
documented customer security-policy acceptance of the unsigned candidate,
remains unresolved. No SmartScreen/Defender control was bypassed or disabled.
Unsigned status is not automatically a runtime defect requiring an unnecessary
rebuild; the release owner must decide the distribution policy.

## 6. Exact dependency review and obligations — BLOCKED clearance

The frozen core inventory still has 15 distribution records and 45 files in
its notice directory. Available Phase 10 companion materials remain unchanged.
The native inventory is more precise than assuming all Qt components share a
version: [native version evidence](screenshots/phase11/qt-native-versions.json).

| Frozen component | Observed identity | Status / human review required |
|---|---|---|
| Qt Core/Gui/Network/Widgets, OpenGL/OpenGLWidgets | DLL file/product versions 6.12.0.0 | BLOCKED: confirm exact licensing route and required per-component notices, source and replacement materials. |
| Qt Qml/QmlMeta/QmlModels/QmlWorkerScript/Quick | DLL versions 6.12.0.0 | BLOCKED: include these shipped libraries and dependencies in the inventory even when not directly used by the dashboard. |
| Qt Svg/SvgWidgets | DLL versions 6.12.0.0 | BLOCKED: confirm exact module/build and third-party attributions. |
| Qt Pdf | DLL version **6.140.0.0** | BLOCKED: review the matching PDF/PDFium build and transitive notices; do not infer 6.12.0 from the main bindings alone. The version difference itself is not a demonstrated runtime defect. |
| Python / PySide6 / PyQtGraph | Frozen build records: Python 3.14.3, PySide6 6.12.0, PyQtGraph 0.14.0 | PARTIAL: retain runtime/MIT notices and verify all native/transitive/resource terms. |
| OpenSSL DLLs | `libssl/libcrypto-3-x64`: 3.5.5; `libssl/libcrypto-3`: 3.0.18 by file/product resources | PARTIAL: identify provenance of both sets and provide their applicable notices/materials. These are version-resource observations, not an upstream-binary attestation. |
| libffi | `libffi-8.dll`, no file-version string | PARTIAL: ABI filename does not establish exact libffi source version; match the runtime build and retain its copyright/permission notice. |
| PyInstaller | Frozen build inventory 6.22.0, packaged COPYING/bootloader exception inspected | PARTIAL: commercial bundling exception does not clear dependency redistribution terms. |
| Inno Setup | Frozen build compiler 6.7.3 | PARTIAL: review license and organization policy; vendor purchase request is not a strict purchase requirement according to its FAQ. No purchase made. |
| Other Python/native/vendor resources | Phase 10 optional-module and companion inventories retained | PARTIAL: complete the transitive/native SBOM and notice reconciliation; namespace mapping is not exact proof of inclusion. |

Qt Virtual Keyboard is still absent. The known core notice-folder non-document
files and incomplete LGPL materials remain Phase 10 inventory findings; they
were not silently changed inside the frozen installer. All 69 CSV resources
were previously identified as upstream chart color maps rather than history;
the unchanged complete bundle manifest preserves those bytes. PyQtGraph's
shipped MIT license and PyInstaller's shipped exception text were read again.

Before redistribution, the owner/legal reviewer must determine the applicable
license route for each shipped Qt module/plugin, provide required license texts
and prominent notices, arrange applicable corresponding-source or valid
source-offer materials, document usable library replacement/relinking and
installation procedures, and ensure application terms preserve required library
rights. Dynamic DLLs alone do not complete LGPL obligations. No commercial Qt
license or legal approval is assumed.

Primary references checked: [Qt obligations](https://www.qt.io/development/open-source-lgpl-obligations),
[Qt PDF licensing overview](https://doc-snapshots.qt.io/qtpdf/qtpdf-index.html),
[OpenSSL release-dependent licenses](https://openssl-library.org/source/license/),
[libffi license](https://github.com/libffi/libffi/blob/master/LICENSE),
[PyInstaller exception](https://pyinstaller.org/en/stable/license.html), and
[Inno commercial FAQ](https://jrsoftware.org/isorder.php).
Qt PDF's published overview identifies LGPLv3/GPLv2/commercial alternatives;
OpenSSL 3.x uses Apache 2.0; libffi's license requires retaining its notices.
These references guide human review of exact shipped builds, not automated
legal certification. No tools, subscriptions or licenses were purchased.

## 7. Client data readiness — PASS schema; BLOCKED real data

[SUPPORTED_DATA_SCHEMA.md](SUPPORTED_DATA_SCHEMA.md) was checked against the
actual importer. Required date/title/whole credit/streams/country and optional
position, track ID, artist ID/name, album ID/name and weekly bounds remain
distinct. Source cadence is explicit; it is not inferred by manufacturing
missing daily values.

A new explicitly generated mixed-cadence fixture in a new isolated test database
verified: US daily streams **220** from two rows; US weekly streams **900** from
one row; Canadian 9,999 excluded; chart positions, stable track ID and reporting
dates preserved; supplied artist/album mappings yield the corresponding
220/900 charting totals. [Fixture result](screenshots/phase11/schema-result.json).
This verifies compatible schema mechanics, not the content or rights of any
future client file.

The client has still not decided bundled complete history versus client-supplied
imports. Actual client dataset acceptance is NOT TESTED; approved sources,
coverage, metadata and permitted uses remain BLOCKED. No research archive was
opened for production import, no research row was bundled, and no 2022-2026
daily observation was invented. Synthetic examples and demos remain labeled.

## 8. QA scope and changes — PASS scoped checks

Fresh targeted command:

```text
python -m pytest -q tests/test_phase9_correctness.py tests/test_import_sessions.py tests/test_exports.py
52 passed in 4.11s
```

These include independent arithmetic, daily/weekly/date/collaboration/edition
semantics, validation/duplicates/rollback and reopened exports. The full
**155-test** result remains Phase 10's result, not a new Phase 11 full-suite
claim. No production source changed, so a full suite and rebuild were not
required. No new defect was found that justified changing the frozen release.
Only this report, the handover checklist and Phase 11 evidence were added or
updated. Existing shared-worktree changes were retained.

## 9. Exact remaining blockers and closure evidence

| Blocker | Status | Owner and evidence needed to close |
|---|---|---|
| Authorized clean guest | BLOCKED | Environment owner supplies an existing authorized clean Windows 10/11 x64 guest and protected baseline/snapshot. No privileged provisioning is implied. |
| Actual Setup lifecycle | BLOCKED | Tester records exact hash, clean baseline, Start Menu launch, no developer-runtime dependency, import/export/persistence, uninstall/reinstall and retained AppData evidence. |
| Human GUI and physical DPI acceptance | PARTIAL | Tester completes the checklist and physical matrix, with screenshots, mouse/keyboard/calendar/focus/tooltip/file-chooser results. |
| Dependency redistribution materials | BLOCKED | Release owner/legal reviewer signs off exact components, notices, applicable source/replacement materials and proprietary distribution terms. |
| Signing/security-policy disposition | PARTIAL | Legitimate signing with new hashes/reverification, or explicit accepted unsigned policy, recorded by release owner/customer. |
| Historical data scope, rights, coverage | BLOCKED | Client confirms scope; owner approves exact datasets/versions, USA/cadence/coverage, metadata and permitted uses. |
| Human authorization to deliver | BLOCKED | Client/release owner approves acceptance against exact artifacts after required gates close. |

## 10. Delivery decision

**Not approved for human client delivery.** The frozen engineering candidate
is preserved, useful checks passed, and blocker-closure instructions are ready.
Unavailable environments, unperformed physical/manual acceptance and missing
human decisions were not converted into PASS results. The application was not
sent to the client. Any eventual binary/packaging correction or signing must
produce new hashes and repeat the relevant acceptance checks.

Final receipt: [verification.json](screenshots/phase11/verification.json).
Document links and `git diff --check` passed; frozen artifact and both folder
manifests matched at the final check.
