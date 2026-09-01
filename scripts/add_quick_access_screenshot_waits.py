"""Insert a UI-settle wait before Photos and Editorial screenshots."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
targets = [
    *sorted((ROOT / "Scenarios").glob("ANON_PHOTO_*.yaml")),
    *sorted((ROOT / "Scenarios").glob("ANON_EDITORIAL_*.yaml")),
    ROOT / "Common" / "OPEN_ANONYMOUS_PHOTOS.yaml",
    ROOT / "Common" / "OPEN_ANONYMOUS_EDITORIAL.yaml",
    ROOT / "Common" / "OPEN_ANONYMOUS_EDITORIAL_ARTICLE.yaml",
]

changed = 0
screenshots = 0
for path in targets:
    if not path.exists():
        continue
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    output: list[str] = []
    file_changed = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("- takeScreenshot:"):
            indent = line[: len(line) - len(stripped)]
            wait_line = f"{indent}- waitForAnimationToEnd"
            if not output or output[-1].strip() != "- waitForAnimationToEnd":
                output.append(wait_line)
                file_changed = True
            screenshots += 1
        output.append(line)
    if file_changed:
        path.write_text("\n".join(output) + "\n", encoding="utf-8")
        changed += 1

print(f"updated_files={changed} screenshots_guarded={screenshots}")
