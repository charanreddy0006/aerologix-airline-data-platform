"""Validate relative Markdown links in README and docs without network access."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def main() -> None:
    errors = []
    documents = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
    for document in documents:
        content = document.read_text(encoding="utf-8")
        for target in LINK.findall(content):
            target = target.split("#", 1)[0]
            if not target or target.startswith(("https://", "http://", "mailto:")):
                continue
            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"{document.relative_to(ROOT)}: unresolved link {target}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Validated local Markdown links in {len(documents)} documents")


if __name__ == "__main__":
    main()
