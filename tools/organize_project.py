from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
TOOLS = ROOT / "tools"

DIRECTORIES = ("css", "js", "images", "pdf")
PUBLIC_FILES = ("manifest.json", "service-worker.js")
TOOL_FILES = ("generate_pdf.py", "generate_placeholders.py", "process_logo.py")


def move(source, destination):
    if not source.exists():
        return
    if destination.exists():
        raise FileExistsError(f"Destino ja existe: {destination}")
    source.rename(destination)
    print(f"Movido: {source.relative_to(ROOT)} -> {destination.relative_to(ROOT)}")


def main():
    FRONTEND.mkdir(exist_ok=True)
    TOOLS.mkdir(exist_ok=True)

    for name in DIRECTORIES:
        move(ROOT / name, FRONTEND / name)

    for source in ROOT.glob("*.html"):
        move(source, FRONTEND / source.name)

    for name in PUBLIC_FILES:
        move(ROOT / name, FRONTEND / name)

    for name in TOOL_FILES:
        move(ROOT / name, TOOLS / name)


if __name__ == "__main__":
    main()
