# Third-Party Dependency and License Checklist

## Phase 9 release inventory and review

`scripts/write_release_notices.py` now collects exact core distribution metadata,
available installed license/notice files, and the Python runtime license before
each build. The bundle includes `_internal/notices/dependency-inventory.json`,
`THIRD_PARTY_NOTICES.md`, and copied notices. This is a concrete improvement over
the earlier checklist, but it is not a complete transitive SBOM or licensing
clearance. In particular, the installed PySide wheel license directory exposes
commercial-license references; these alone do not satisfy all LGPL materials.
The final bundled DLL inventory and release assessment are in [Phase 9 QA](PHASE_9_ENGINEERING_QA.md).

The initial Phase 9 inventory found the automatically collected
`Qt6VirtualKeyboard.dll` and its input-context plugin, although this desktop app
does not use an on-screen keyboard. [Qt Virtual Keyboard's license page](https://doc.qt.io/qt-6/qtvirtualkeyboard-index.html)
lists commercial or GPLv3 terms. The build specification now excludes that
optional plugin, DLL, and matching resources. Final bundle inspection and
Windows text-entry/import/export checks verify the exclusion without removing
the standard Windows input context. This reduces the redistribution scope but
does not certify licensing of every remaining component.

Qt's published guidance requires review per module and, for LGPL distribution,
applicable notices, library source availability, and replacement/relinking rights.
Some modules have GPL-only open-source terms. The dynamic DLL packaging does not
by itself complete these obligations. See [Qt obligations](https://www.qt.io/development/open-source-lgpl-obligations)
and [Qt 6 licensing](https://doc.qt.io/qt-6/licensing.html). Final proprietary
distribution review remains open; no commercial Qt license was purchased.

Inno Setup 6.7.3 was already installed in the current user's Programs folder and
was used to compile the installer. Its compiler reports non-commercial use. The
vendor requests commercial purchases but explicitly says they are not strictly
required in its [commercial-license FAQ](https://jrsoftware.org/isorder.php).
Review the applicable [Inno license](https://jrsoftware.org/files/is/license.txt)
and organization policy before release; no purchase or license-key changes were made.

The EXE and Setup are unsigned. Authorized publisher signing and client security
policy acceptance remain release work. See [Microsoft signing guidance](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control).
No Defender or SmartScreen protection was disabled for these checks.

## Earlier inventory

This is a release review inventory, not a legal opinion or a complete generated software bill of materials. Build-time versions observed during Phase 5 audit: Python 3.14.3; PyInstaller 6.22.0; PySide6, PySide6-Essentials, and PySide6-Addons 6.12.0; PyQtGraph 0.14.0; Pandas 2.3.3; NumPy 2.4.2; OpenPyXL 3.1.5; et-xmlfile 2.0.0; Pillow 12.1.1; and pytest 9.0.3. Pillow and pytest are build/test dependencies. PyArrow was explicitly excluded from the final bundle. Re-run `python -m pip show <package>` and inspect installed `METADATA`/license files for the exact release being shipped. The build environment's versions are not a substitute for the final bundle inventory.

| Component | Usage | Commonly declared license | Release action |
|---|---|---|---|
| Python runtime | Executable runtime | Python Software Foundation License | Include required notices for the exact runtime distribution. |
| PySide6 / Qt Essentials and Addons | Qt bindings and native GUI libraries/plugins | Varies by Qt module/build: LGPLv3, GPL, or commercial terms may apply | Inventory every bundled Qt library, module, and plugin. Confirm proprietary distribution route, notices, source/relinking obligations, and license compatibility with Qt counsel. |
| PyQtGraph | Interactive charts | MIT | Include the exact upstream copyright and license notice. |
| Pandas | CSV/data processing | BSD 3-Clause | Include the exact upstream notice and bundled dependency notices. |
| NumPy | Pandas/PyQtGraph numeric dependency | BSD 3-Clause | Inventory exact version and include its notices. |
| OpenPyXL | XLSX workbook import/export | MIT | Include the exact upstream copyright and license notice. |
| et-xmlfile | OpenPyXL dependency | MIT | Inventory exact bundled version and include its notice if shipped. |
| PyInstaller | Build-time packager and bootloader | GPLv2 with a special exception for distribution of applications it packages | Keep PyInstaller out of the application runtime unless collected; retain and review its bootloader exception and notices for the exact release. |
| Pillow | Build-time ICO generator | HPND | Build-only dependency; do not bundle unless later runtime imports require it. |
| pytest | Test-only dependency | MIT | Must not be shipped in the client runtime. |
| SQLite | Local database runtime | Public domain | Confirm exact bundled Python SQLite runtime and any platform notices. |
| KaggleHub 1.0.3 / kagglesdk 0.1.38 | Optional Phase 6 research downloader only | Apache-2.0 (verify exact package metadata) | Optional research extra; not imported by app startup or intended for the packaged client runtime. |
| PyArrow 24.0.0 / psutil 7.2.2 / tqdm 4.67.3 | Optional research audit and bounded processing | Apache-2.0 / BSD-3-Clause / MPL-2.0 (verify exact package metadata) | Optional research extra; verify exact licenses if redistributed. Not required by the production desktop app. |
| certifi 2026.10.23 | KaggleHub HTTPS certificate bundle | MPL-2.0 | Optional transitive research dependency; review if it is ever redistributed. |

## Mandatory release actions

- [ ] Generate a package/SBOM inventory from the final `dist\USMusicChartsAnalytics` directory, not only from `pyproject.toml`.
- [ ] Archive exact wheel/package license files and versions used for the approved build.
- [ ] Inspect PySide6-Essentials, PySide6-Addons, Qt plugins, Qt translations, and the Qt platform plugin selection actually collected by PyInstaller.
- [ ] Determine whether Qt is being distributed under LGPLv3, GPL, or a commercial license, per each included component.
- [ ] For LGPL components, obtain legal confirmation of all applicable relinking/replacement, notices, source availability, reverse-engineering, and installation-information obligations for this installer and product model.
- [ ] Review Pandas/NumPy/dateutil/tzdata and OpenPyXL/et-xmlfile transitive notices.
- [ ] Include a third-party notices file in the installed distribution if required. Do not treat this checklist alone as the notice package.
- [ ] Confirm icon artwork is original and does not contain Spotify marks/assets.
- [ ] Have counsel approve proprietary distribution before client release.

No code-signing certificate or license counsel review was available in this iteration. No claim is made that the current bundle satisfies every redistribution obligation.
