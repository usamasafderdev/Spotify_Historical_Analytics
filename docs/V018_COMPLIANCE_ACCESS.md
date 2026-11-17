# Dependency materials: 0.1.8 INTERNAL-READY

Setup installs the retained dependency-r3 notices, Qt source/replacement archives, runtime prerequisite terms and library replacement instructions under `_internal\compliance`. Exact current core dependency notices and inventory are under `_internal\notices`. Keep these directories with the application; the handover ZIP does not duplicate the large source archives already contained in Setup.

The original dependency-r3 inventories are retained as historical evidence, not relabeled as a new full audit. `v018-runtime-normalization.json` records this build's staged import-name normalization and hashes. `v018-runtime-normalization.py` preserves its recipe. Only D: build copies were normalized; installed Python dependencies were not modified.

No Microsoft runtime DLLs or redistributable installer are bundled. Windows 10/11 x64 and the official Microsoft Visual C++ v14 x64 runtime 14.44.35211.0 or newer are prerequisites; Setup checks the required system DLL versions and gives the official Microsoft download address when missing. It does not download or install that prerequisite automatically.

This preservation and mechanical bundle verification do not approve the external distribution of the historical datasets. That authorization remains unestablished; the archive is INTERNAL-READY only. The application/installer is unsigned, and installed-host QA is not a clean Windows VM certification.
