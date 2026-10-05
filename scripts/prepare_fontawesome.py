"""Vendor a deterministic Free SVG archive from the pinned official npm package."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import tarfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "7.3.1"
URL = f"https://registry.npmjs.org/@fortawesome/fontawesome-free/-/fontawesome-free-{VERSION}.tgz"
INTEGRITY = "wmglKKPDIkgV3aWlZzWECCPoGIkYCulzBwxG9+w7rc5BGapZ6cPMpoPOT8k36J0Ni7PPX6c/rsoMWfS4d1MUMg=="
ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    data = urllib.request.urlopen(URL, timeout=60).read()
    if base64.b64encode(hashlib.sha512(data).digest()).decode("ascii") != INTEGRITY:
        raise ValueError("Font Awesome package integrity check failed")
    resources = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as package:
        for member in package:
            if member.isfile() and (member.name.startswith("package/svgs-full/") and member.name.endswith(".svg")
                                    or member.name == "package/LICENSE.txt"):
                resources[member.name] = package.extractfile(member).read()
    if not resources or "package/LICENSE.txt" not in resources:
        raise ValueError("Package is missing SVG resources or its license")
    target = ROOT / "src/stavellum/assets/fontawesome"
    target.mkdir(parents=True, exist_ok=True)
    icons = []
    with zipfile.ZipFile(target / "icons.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, svg in sorted(resources.items()):
            if not path.endswith(".svg"):
                continue
            relative = path.removeprefix("package/svgs-full/")
            style, filename = relative.split("/")
            if style not in ("solid", "regular", "brands"):
                continue
            entry = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, svg, compresslevel=9)
            icons.append({"name": filename.removesuffix(".svg"), "style": style,
                          "path": relative, "sha256": hashlib.sha256(svg).hexdigest()})
    index = {"version": VERSION, "source": URL, "integrity": "sha512-" + INTEGRITY,
             "archive_sha256": hashlib.sha256((target / "icons.zip").read_bytes()).hexdigest(), "icons": icons}
    (target / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    license_data = resources["package/LICENSE.txt"]
    (target / "LICENSE.txt").write_bytes(license_data)
    print(f"Vendored {len(icons)} Free {VERSION} SVGs; license SHA-256: {hashlib.sha256(license_data).hexdigest()}")


if __name__ == "__main__":
    main()
