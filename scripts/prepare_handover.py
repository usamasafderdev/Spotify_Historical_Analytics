"""Prepare an allowlisted INTERNAL REVIEW folder; never publish or contact clients."""
from __future__ import annotations

import hashlib
from importlib import metadata
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "dist/handover/USMusicChartsAnalytics-0.1.0-review"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    freeze = json.loads((ROOT / "build/phase10/freeze.json").read_text())
    audit = json.loads((ROOT / "build/phase10/security-inventory.json").read_text())
    acceptance = json.loads((ROOT / "build/phase10/acceptance.json").read_text())
    for artifact in freeze["artifacts"]:
        if digest(ROOT / artifact["path"]) != artifact["sha256"]:
            raise RuntimeError("A frozen artifact changed. Reverify it before preparing the folder.")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    setup = ROOT / "dist/installer/US-Music-Charts-Analytics-Setup.exe"
    shutil.copy2(setup, DESTINATION / setup.name)
    (DESTINATION / (setup.name + ".sha256")).write_text(f"{digest(setup)}  {setup.name}\n", encoding="ascii")
    files = {
        "docs/USER_GUIDE.md": "USER_GUIDE.md",
        "docs/WINDOWS_INSTALLATION_GUIDE.md": "INSTALLATION.md",
        "docs/SUPPORTED_DATA_SCHEMA.md": "SUPPORTED_DATA_SCHEMA.md",
        "docs/METRIC_DEFINITIONS.md": "METRIC_DEFINITIONS.md",
        "docs/KNOWN_LIMITATIONS.md": "KNOWN_LIMITATIONS.md",
        "docs/FINAL_CLIENT_HANDOVER_CHECKLIST.md": "FINAL_CLIENT_HANDOVER_CHECKLIST.md",
        "docs/PHASE_10_SECURITY_AND_LICENSE_REVIEW.md": "DEPENDENCY_AND_SECURITY_REVIEW.md",
    }
    for source, name in files.items():
        content = (ROOT / source).read_text(encoding="utf-8")
        content = content.replace("PHASE_10_RELEASE_ACCEPTANCE.md", "QA_ACCEPTANCE.md")
        content = content.replace("PHASE_9_ENGINEERING_QA.md", "QA_ACCEPTANCE.md")
        content = content.replace("PHASE_10_SECURITY_AND_LICENSE_REVIEW.md", "DEPENDENCY_AND_SECURITY_REVIEW.md")
        (DESTINATION / name).write_text(content, encoding="utf-8")
    notices = DESTINATION / "notices"
    shutil.copytree(ROOT / "dist/USMusicChartsAnalytics/_internal/notices", notices, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.py", "*.pyc", "*.pyo", "*.pyd", "*.dll", "*.exe"))
    supplemental = []
    for name in sorted({row["distribution"] for row in audit["installed_distribution_mapping"]}):
        dist = metadata.distribution(name)
        copied = []
        for file in dist.files or ():
            if not any(part.lower().startswith(("license", "licence", "copying", "notice")) for part in file.parts):
                continue
            # Some libraries have executable SPDX lookup packages named `licenses`.
            # Their Python sources/bytecode are not redistribution notice documents.
            leaf = Path(str(file))
            if leaf.suffix.lower() in {".py", ".pyc", ".pyo", ".pyd", ".dll", ".exe", ".key", ".pem"}:
                continue
            if (leaf.suffix.lower() not in {"", ".txt", ".md", ".rst", ".html", ".htm", ".license"}
                    and not leaf.name.lower().startswith(("license", "licence", "copying", "notice"))):
                continue
            source = Path(dist.locate_file(file))
            if not source.is_file():
                continue
            # Keep third-party relative names; never copy credentials or metadata wholesale.
            safe_parts = [part if part not in {"..", "."} else "_" for part in file.parts]
            target = notices / "supplemental" / name / Path(*safe_parts)
            if not target.resolve().is_relative_to(notices.resolve()):
                raise RuntimeError("Notice destination escapes the release folder.")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append(target.relative_to(DESTINATION).as_posix())
        expression = dist.metadata.get("License-Expression") or dist.metadata.get("License") or "Not declared"
        supplemental.append({"distribution": name, "build_environment_version": dist.version,
                             "declared_license_summary": expression.splitlines()[0][:200],
                             "available_notice_files": copied,
                             "scope": "Candidate from bundled module roots; shared namespaces can map to distributions not shipped in full."})
    (notices / "SUPPLEMENTAL_INVENTORY.json").write_text(json.dumps(supplemental, indent=2), encoding="utf-8")
    (notices / "REVIEW_REQUIRED.md").write_text(
        "# Notice review required\n\nCore notice documents and inventories are copied from the frozen bundle. Python sources/bytecode in license-lookup namespaces are excluded from this companion folder; the original inventory describes the frozen bundle and may list excluded non-document files. Supplemental text documents were collected from installed distribution records associated with bundled module roots. Shared namespaces can over-identify distributions. These files do not constitute a complete native-library/transitive SBOM or legal clearance.\n\n"
        "Complete the per-component license determination, required license texts/notices, corresponding-source or valid source-offer materials, and library replacement/relinking instructions before redistribution. Qt wheel commercial-license references alone do not satisfy an LGPL release. Review Windows runtime/OpenSSL/libffi/SQLite and vendored component materials as applicable. No client delivery is approved.\n", encoding="utf-8")
    version = {"application": "US Music Charts Analytics", "version": freeze["version"],
               "database_schema_user_version": freeze["schema_user_version"],
               "release_status": "INTERNAL REVIEW ONLY - CLIENT DELIVERY BLOCKED",
               "historical_data_bundled": False, "signing": "NotSigned",
               "installer_sha256": digest(setup),
               "source_exe_sha256": freeze["artifacts"][0]["sha256"]}
    (DESTINATION / "VERSION.json").write_text(json.dumps(version, indent=2), encoding="utf-8")
    (DESTINATION / "RELEASE_STATUS.txt").write_text(
        "INTERNAL REVIEW ONLY - DO NOT SEND TO CLIENT\n\nClient data scope/permissions, clean-machine acceptance, physical desktop/DPI acceptance, dependency redistribution review, and signing/security-policy disposition remain open. Historical data is not bundled. This folder was prepared locally and has not been published or sent.\n", encoding="utf-8")
    summary = "# QA acceptance summary - internal review\n\nVersion 0.1.0, database schema 2. This folder retains the frozen Phase 9 installer.\n\n| Check | Status | Evidence / limit |\n|---|---|---|\n"
    for item in acceptance["items"]:
        summary += f"| {item['item']} | {item['status']} | {item['result']} |\n"
    summary += f"\nInstaller SHA-256: `{digest(setup)}`. No final client-delivery approval. Detailed developer evidence is retained in the project, outside this handover folder.\n"
    (DESTINATION / "QA_ACCEPTANCE.md").write_text(summary, encoding="utf-8")
    sums = [f"{digest(path)}  {path.relative_to(DESTINATION).as_posix()}" for path in sorted(DESTINATION.rglob("*")) if path.is_file() and path.name != "SHA256SUMS.txt"]
    (DESTINATION / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    report = {"folder": DESTINATION.relative_to(ROOT).as_posix(), "files": len(sums),
              "installer_sha256": digest(setup), "supplemental_distribution_candidates": len(supplemental),
              "supplemental_notice_files": sum(len(row["available_notice_files"]) for row in supplemental),
              "published": False, "sent_to_client": False}
    (ROOT / "build/phase10/handover.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
