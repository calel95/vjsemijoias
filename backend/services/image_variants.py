from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError, features

from backend.config import FRONTEND_ROOT

IMAGE_ROOT = (FRONTEND_ROOT / "images").resolve()
DEFAULT_OUTPUT_ROOT = (FRONTEND_ROOT / "images" / "variants").resolve()
DEFAULT_VARIANTS = {
    "thumbnail": 160,
    "card": 480,
    "detail": 960,
}
SUPPORTED_RASTER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
SKIPPED_EXTENSIONS = {".svg"}


@dataclass(frozen=True)
class SourceImage:
    input_value: str
    path: Path | None
    relative_path: str | None
    status: str
    reason: str


@dataclass(frozen=True)
class VariantPlan:
    name: str
    max_width: int | None
    output_path: Path | None
    output_relative_path: str | None
    format: str | None
    status: str
    reason: str
    width: int | None = None
    height: int | None = None


def is_absolute_url(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def is_data_url(value: str) -> bool:
    return str(value or "").strip().lower().startswith("data:")


def normalize_image_value(value: str | Path | None) -> str:
    return str(value or "").strip().replace("\\", "/")


def webp_supported() -> bool:
    try:
        return bool(features.check("webp"))
    except Exception:
        return False


def ensure_output_root(output_root: str | Path | None = None) -> Path:
    root = Path(output_root) if output_root else DEFAULT_OUTPUT_ROOT
    if not root.is_absolute():
        root = (FRONTEND_ROOT / root).resolve()
    else:
        root = root.resolve()
    try:
        root.relative_to(IMAGE_ROOT)
    except ValueError as exc:
        raise ValueError("output-root deve ficar dentro de frontend/images") from exc
    return root


def frontend_relative_image_path(value: str) -> str | None:
    image = normalize_image_value(value).lstrip("/")
    if not image:
        return None
    if image.startswith("frontend/images/"):
        return image.removeprefix("frontend/")
    if image.startswith("images/"):
        return image
    return None


def resolve_source_image_path(value: str | Path | None) -> SourceImage:
    image = normalize_image_value(value)
    if not image:
        return SourceImage(image, None, None, "erro", "caminho vazio")
    if is_absolute_url(image):
        return SourceImage(image, None, None, "ignorar", "URL externa ignorada")
    if is_data_url(image):
        return SourceImage(image, None, None, "erro", "data URL nao e arquivo local")

    raw_path = Path(str(value or ""))
    if raw_path.is_absolute():
        physical = raw_path.resolve()
        try:
            relative_path = physical.relative_to(FRONTEND_ROOT.resolve()).as_posix()
        except ValueError:
            return SourceImage(image, physical, None, "erro", "arquivo fora de frontend/images")
    else:
        relative_path = frontend_relative_image_path(image)
        if not relative_path:
            return SourceImage(image, None, None, "erro", "caminho fora de frontend/images")
        if ".." in Path(relative_path).parts:
            return SourceImage(image, None, relative_path, "erro", "path traversal bloqueado")
        physical = (FRONTEND_ROOT / relative_path).resolve()

    try:
        physical.relative_to(IMAGE_ROOT)
    except ValueError:
        return SourceImage(image, physical, None, "erro", "arquivo fora de frontend/images")

    try:
        relative_path = physical.relative_to(FRONTEND_ROOT.resolve()).as_posix()
    except ValueError:
        return SourceImage(image, physical, None, "erro", "arquivo fora do frontend")

    if not physical.is_file():
        return SourceImage(image, physical, relative_path, "erro", "arquivo local inexistente")

    extension = physical.suffix.lower()
    if extension in SKIPPED_EXTENSIONS:
        return SourceImage(image, physical, relative_path, "ignorar", "SVG nao possui variante raster nesta sprint")
    if extension not in SUPPORTED_RASTER_EXTENSIONS:
        return SourceImage(image, physical, relative_path, "erro", "formato de imagem nao suportado")

    return SourceImage(image, physical, relative_path, "ok", "imagem local valida")


def image_dimensions(path: Path) -> tuple[int, int]:
    try:
        with Image.open(path) as image:
            return image.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("arquivo de imagem invalido") from exc


def image_is_animated_gif(path: Path) -> bool:
    if path.suffix.lower() != ".gif":
        return False
    try:
        with Image.open(path) as image:
            return bool(getattr(image, "is_animated", False) and getattr(image, "n_frames", 1) > 1)
    except (UnidentifiedImageError, OSError, ValueError):
        return False


def variant_format_for(source_path: Path) -> tuple[str, str]:
    if webp_supported():
        return "WEBP", ".webp"
    extension = source_path.suffix.lower()
    if extension in {".jpg", ".jpeg"}:
        return "JPEG", ".jpg"
    if extension == ".png":
        return "PNG", ".png"
    if extension == ".webp":
        return "WEBP", ".webp"
    return "PNG", ".png"


def variant_output_path(
    source: SourceImage,
    variant_name: str,
    *,
    output_root: str | Path | None = None,
    extension: str = ".webp",
) -> Path:
    if not source.relative_path:
        raise ValueError("imagem sem caminho relativo")
    root = ensure_output_root(output_root)
    source_relative = Path(source.relative_path).relative_to("images")
    destination_dir = (root / source_relative.parent).resolve()
    output = (destination_dir / f"{source_relative.stem}-{variant_name}{extension}").resolve()
    try:
        output.relative_to(root)
    except ValueError as exc:
        raise ValueError("saida de variante fora do output-root") from exc
    return output


def scaled_dimensions(width: int, height: int, max_width: int) -> tuple[int, int]:
    if width <= max_width:
        return width, height
    ratio = max_width / width
    return max_width, max(1, round(height * ratio))


def build_variant_plan(
    source: SourceImage,
    *,
    output_root: str | Path | None = None,
    variants: dict[str, int] | None = None,
) -> list[VariantPlan]:
    variants = variants or DEFAULT_VARIANTS
    if source.status != "ok" or source.path is None:
        return [
            VariantPlan(
                name="original",
                max_width=None,
                output_path=None,
                output_relative_path=source.relative_path,
                format=None,
                status=source.status,
                reason=source.reason,
            )
        ]
    if image_is_animated_gif(source.path):
        return [
            VariantPlan(
                name="original",
                max_width=None,
                output_path=None,
                output_relative_path=source.relative_path,
                format=None,
                status="ignorar",
                reason="GIF animado nao recebe variantes nesta sprint",
            )
        ]

    width, height = image_dimensions(source.path)
    target_format, extension = variant_format_for(source.path)
    plans = [
        VariantPlan(
            name="original",
            max_width=None,
            output_path=None,
            output_relative_path=source.relative_path,
            format=None,
            status="mantido",
            reason="original preservado sem alteracao",
            width=width,
            height=height,
        )
    ]
    for name, max_width in variants.items():
        target_width, target_height = scaled_dimensions(width, height, max_width)
        output = variant_output_path(source, name, output_root=output_root, extension=extension)
        plans.append(
            VariantPlan(
                name=name,
                max_width=max_width,
                output_path=output,
                output_relative_path=output.relative_to(FRONTEND_ROOT).as_posix(),
                format=target_format,
                status="planejado",
                reason="variante planejada",
                width=target_width,
                height=target_height,
            )
        )
    return plans


def generate_variant(source_path: Path, plan: VariantPlan) -> str:
    if plan.name == "original":
        return "mantido"
    if plan.output_path is None or plan.max_width is None or plan.format is None:
        return "ignorado"
    if plan.output_path.exists():
        return "existente"

    plan.output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        image = image.copy()
        image.thumbnail((plan.max_width, max(plan.height or plan.max_width, 1)), Image.Resampling.LANCZOS)
        if plan.format == "JPEG" and image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        elif plan.format == "WEBP" and image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
        save_kwargs = {"quality": 82, "optimize": True} if plan.format in {"WEBP", "JPEG"} else {"optimize": True}
        image.save(plan.output_path, format=plan.format, **save_kwargs)
    return "gerado"


def plan_to_dict(plan: VariantPlan) -> dict[str, Any]:
    return {
        "name": plan.name,
        "max_width": plan.max_width,
        "width": plan.width,
        "height": plan.height,
        "format": plan.format,
        "status": plan.status,
        "reason": plan.reason,
        "output_path": plan.output_relative_path,
    }


def generate_variants_for_image(
    value: str | Path,
    *,
    apply: bool = False,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    source = resolve_source_image_path(value)
    plans = build_variant_plan(source, output_root=output_root)
    generated = []
    if apply and source.status == "ok" and source.path is not None:
        updated_plans = []
        for plan in plans:
            status = generate_variant(source.path, plan)
            updated_plans.append(
                VariantPlan(
                    name=plan.name,
                    max_width=plan.max_width,
                    output_path=plan.output_path,
                    output_relative_path=plan.output_relative_path,
                    format=plan.format,
                    status=status,
                    reason=plan.reason,
                    width=plan.width,
                    height=plan.height,
                )
            )
        plans = updated_plans
        generated = [plan.output_relative_path for plan in plans if plan.status == "gerado"]

    return {
        "input": source.input_value,
        "source_path": source.relative_path,
        "status": source.status,
        "reason": source.reason,
        "generated": generated,
        "variants": [plan_to_dict(plan) for plan in plans],
    }


def write_report(report: dict[str, Any], report_path: str | Path | None) -> None:
    if not report_path:
        return
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")