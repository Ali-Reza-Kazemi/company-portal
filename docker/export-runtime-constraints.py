"""Regenerate Linux/Python 3.14 constraints only after the installed suite passes."""

from importlib.metadata import distributions
from pathlib import Path

import saeenaria_portal

excluded = {"frappe", "saeenaria-portal", "pip", "setuptools", "wheel"}
versions = {}
for distribution in distributions():
    name = distribution.metadata["Name"]
    normalized = name.lower().replace("_", "-")
    if normalized not in excluded:
        versions[normalized] = distribution.version
target = Path(saeenaria_portal.__file__).resolve().parents[1] / "constraints-runtime.txt"
target.write_text(
    "# Tested Linux / Python 3.14 dependency versions; regenerate after regression tests.\n"
    "# Frappe itself is pinned by commit in Dockerfile. Build tooling is image-owned.\n"
    + "".join(f"{name}=={version}\n" for name, version in sorted(versions.items())),
    encoding="utf-8",
)
print(f"Wrote {len(versions)} runtime constraints")
