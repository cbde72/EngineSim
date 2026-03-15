from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


def _read_structured_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding='utf-8')
    suffix = path.suffix.lower()
    if suffix in {'.yaml', '.yml'}:
        if yaml is None:
            raise RuntimeError('PyYAML is not installed. YAML plot config cannot be loaded.')
        data = yaml.safe_load(text) or {}
    elif suffix == '.json':
        data = json.loads(text)
    else:
        raise ValueError(f'Unsupported plot config format: {path.suffix}')
    if not isinstance(data, dict):
        raise ValueError(f'Plot config root must be a mapping: {path}')
    return data


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def resolve_plot_style(config_path: str | Path, raw_plot_style: dict | None = None) -> dict[str, Any]:
    raw_plot_style = dict(raw_plot_style or {})
    cfg_path = Path(config_path).resolve()
    cfg_dir = cfg_path.parent

    explicit = raw_plot_style.get('file') or raw_plot_style.get('path') or raw_plot_style.get('plot_style_file')
    candidates: list[Path] = []
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = (cfg_dir / p).resolve()
        candidates.append(p)
    else:
        candidates.extend((cfg_dir / name).resolve() for name in ('plot.yaml', 'plot.yml', 'plot.json'))

    loaded: dict[str, Any] = {}
    loaded_from: str | None = None
    for cand in candidates:
        if cand.exists():
            loaded = _read_structured_file(cand)
            loaded_from = str(cand)
            break

    inline = {k: v for k, v in raw_plot_style.items() if k not in {'file', 'path', 'plot_style_file'}}
    merged = _deep_merge(loaded, inline)
    if loaded_from:
        merged.setdefault('_meta', {})
        if isinstance(merged['_meta'], dict):
            merged['_meta']['loaded_from'] = loaded_from
    return merged


def dump_plot_style_yaml(data: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    if yaml is None:
        raise RuntimeError('PyYAML is not installed. YAML export is unavailable.')
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding='utf-8')
