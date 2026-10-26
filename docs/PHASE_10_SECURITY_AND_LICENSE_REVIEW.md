# Security and dependency review — version 0.1.0

2026-10-26. **PARTIAL technical review; BLOCKED redistribution clearance.** This is an engineering inventory and review of the frozen release candidate, not legal certification, penetration testing, or a guarantee that no vulnerabilities or secrets exist.

## Security findings

| Check | Status | Result and scope |
|---|---|---|
| Application credential patterns | PASS | No common private-key, AWS access-ID, GitHub-token, or OpenAI-token pattern found in bundled application string constants or scanned small text resources. Candidate values are never printed. This is a scoped pattern check, not exhaustive secret detection. |
| Developer-only application paths | PASS | No absolute developer source filename or developer-path literal found in application PYZ code. Third-party binary debug strings were not exhaustively decoded. |
| Historical data in bundle | PASS | No chart database, XLSX, Parquet, or historical CSV found. The 69 CSV resources are byte-verified upstream PyQtGraph color maps. |
| Storage separation | PASS | Default writable database is under Local AppData; isolated overrides used during acceptance. Input cells do not select database/output destinations. |
| Arbitrary code execution from imports | PARTIAL | CSV/GZ are parsed as data; XLSX is read-only/data-only, with no workbook formula calculation or archive extraction to arbitrary paths. No application `eval`, pickle loading, shell command, dynamic plugin installation, or download/execute flow was identified. This does not establish safety against all malformed-file/parser vulnerabilities or resource exhaustion. |
| SQL and path handling | PASS | Imported fields are bound SQL values. Dynamic schema identifiers come from application constants. Staging/production paths are separate application-supplied paths, not CSV fields. Source hashes detect changed files. |
| Spreadsheet injection | PASS | Existing CSV/XLSX tests verify formula-like text escaping, including leading whitespace. Reports are reopened and parsed. |
| Rollback and cancellation | PASS | Tests cover changed-file refusal, duplicate/conflicting records, transactional rollback, interrupted imports, and SQLite integrity. |
| Logging privacy | PARTIAL | No credentials observed in inspected acceptance results. Exceptions can include local filenames, paths, and parser details. Rotating local logs are not a general-purpose redaction system. Review/redact logs before sharing; no local logs are included in the handover folder. |
| Uninstall retention | PARTIAL | Frozen payload's Phase 9 isolated host lifecycle preserved separate user data and removed app/shortcuts. Actual clean-VM installer lifecycle is not tested. Installer has no user-data deletion action. |
| Authenticode | PARTIAL | EXE and installer are `NotSigned`. Signing with legitimate credentials, or explicit customer security-policy acceptance of an unsigned candidate, remains open. No protection was bypassed. |
| Full vulnerability assessment | NOT TESTED | No complete CVE audit, fuzzing campaign, binary reverse engineering, endpoint protection compatibility assessment, or external penetration test was performed. |

The read-only audit also found bundled optional roots including `debugpy`, `ipykernel`, `requests`, `aiohttp`, and `cryptography`. Presence does not demonstrate that a debugger or network service starts; no such startup action was identified in application code. However, these broaden inventory and redistribution review beyond the 15-package core notice collector. Their removal would require a separately tested packaging change; the frozen artifacts were preserved in this acceptance phase.

## Dependency inventory and notice gaps

Core versions from the frozen build's notice inventory: Python 3.14.3; PySide6/Essentials/Addons/shiboken6 6.12.0; PyQtGraph 0.14.0; Pandas 2.3.3; NumPy 2.4.2; OpenPyXL 3.1.5; et-xmlfile 2.0.0; dateutil 2.9.0.post0; pytz 2026.1.post1; tzdata 2025.3; six 1.17.0; packaging 26.0. PyInstaller 6.22.0 was the build packager. Inno Setup 6.7.3 built the installer. The build-time inventories are useful evidence, not proof of the version/license of every native component.

| Component group | Status | Open obligation |
|---|---|---|
| PySide6 / Qt | BLOCKED | Determine the license route per shipped DLL/plugin, provide required license/notice materials, corresponding-source or valid source-offer materials where applicable, and usable replacement/relinking/installation instructions. The existing wheel commercial-license reference alone does not complete an LGPL distribution. Check proprietary application terms do not restrict applicable library rights. |
| PyQtGraph / Pandas / NumPy / OpenPyXL and support packages | PARTIAL | Core available notices are present. Confirm exact versions, third-party/vendor attributions, and completeness against the final binaries. Supplemental candidate notices are included alongside the installer for review. |
| Python runtime | PARTIAL | Python license is included. Review bundled OpenSSL, SQLite, libffi, compression libraries and other native/transitive obligations against the exact shipped runtime. |
| Optional Python modules | PARTIAL | Core installed notice collection did not cover every detected module root. Available supplemental distribution license files are collected into the review handover folder. Shared namespace mapping may over-identify packages; inventory is not an exact complete SBOM. |
| Windows native runtimes | PARTIAL | Verify redistribution rights and applicable notices for shipped Visual C++/UCRT and other system-support DLLs. No Windows system installation was changed. |
| PyInstaller | PARTIAL | Review exact build version/bootloader exception and dependency terms. Its commercial bundling exception does not replace dependency compliance. |
| Inno Setup | PARTIAL | Vendor requests commercial purchases but says purchase is not strictly required. Review the license and organization policy; no purchase/key changes were made. |

Qt Virtual Keyboard remains excluded from the frozen release. No claim is made that excluding that one component clears every remaining module. Dynamic DLL packaging alone is not full LGPL compliance. The review handover contains core notices plus available supplemental notices, clearly marked incomplete pending human approval; the frozen installer's own core-notice directory was not silently changed.

The handover verification caught Python bytecode copied from a vendor package
namespace named `licenses`; two supplemental bytecode files contained a local
installation-path string. Those values were not printed or sent. The collector
was tightened and code/bytecode removed from the companion folder before final
verification. The frozen core notice folder also contains four license-lookup
Python/code-cache files, but no matching developer account string was found in
that folder. These non-notice files are excluded from the companion documents;
the frozen installer remains unchanged. This is an inventory-quality finding
for the next approved packaging revision, not a claim that those files execute
during import or that the installed notice set is fully compliant.

## Primary references reviewed

- [Qt for Python licenses](https://doc.qt.io/qtforpython-6/licenses.html) and [Qt LGPL/GPL obligations](https://www.qt.io/development/open-source-lgpl-obligations): module terms, corresponding-source materials, notices and replacement rights need per-distribution review.
- [PyInstaller licensing](https://pyinstaller.org/en/stable/license.html): commercial application bundling is covered by its exception, subject to dependency licenses.
- [Python 3.14 license](https://docs.python.org/3.14/license.html): runtime and incorporated software notices; the shipped runtime license is retained with the candidate.
- [Inno commercial-license FAQ](https://jrsoftware.org/isorder.php) and [Inno license](https://jrsoftware.org/files/is/license.txt): distinguish the vendor's commercial-purchase request from a strict purchase requirement.
- [Microsoft signing guidance](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control): trusted signing and publisher verification require legitimate release-owner credentials; no bypass was used.

Before client redistribution, a release owner must complete the native/transitive license inventory and approve the applicable terms and materials. Available companion notices are preparation work, not that approval.
