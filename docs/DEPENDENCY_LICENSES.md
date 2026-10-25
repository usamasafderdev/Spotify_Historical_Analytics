# Third-Party Dependency and License Checklist

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
