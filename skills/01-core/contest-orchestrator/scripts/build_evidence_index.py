#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a read-only, project-side index over existing contest evidence.

The index is a derived view, not a second source of truth.  It records the
presence, hashes, and small structural summaries of contracts and run
artifacts already produced by the workflow.  It never edits those inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except Exception:  # pragma: no cover - JSON-only installations remain usable
    yaml = None


CORE_NAMES = {
    "content_budget_plan": ("content_budget_plan.yaml", "content_budget_plan.yml", "content_budget_plan.json"),
    "model_contract": ("model_contract.yaml", "model_contract.yml", "model_contract.json"),
    "derivation_registry": ("derivation_registry.yaml", "derivation_registry.yml", "derivation_registry.json"),
    "modeling_solution_contract": (
        "modeling_solution_contract.yaml", "modeling_solution_contract.yml", "modeling_solution_contract.json"
    ),
    "model_blueprint": ("model_blueprint.yaml", "model_blueprint.yml", "model_blueprint.json"),
    "numeric_source_map": ("numeric_source_map.json",),
    "figure_registry": ("figure_registry.yaml", "figure_registry.yml", "figure_registry.json"),
    "citation_map": ("citation_map.json",),
    "run_manifest": ("run_manifest.yaml", "run_manifest.yml", "run_manifest.json"),
    "model_summary_cards": ("model_summary_cards.yaml", "model_summary_cards.yml", "model_summary_cards.json"),
    "result_interpretation_cards": ("result_interpretation_cards.yaml", "result_interpretation_cards.yml", "result_interpretation_cards.json"),
    "paper_narrative": ("paper_narrative.yaml", "paper_narrative.yml", "paper_narrative.json"),
    "validation_contract": ("validation_contract.yaml", "validation_contract.yml", "validation_contract.json"),
    "visual_evidence_packet": ("visual_evidence_packet.yaml", "visual_evidence_packet.yml", "visual_evidence_packet.json"),
}

HARNESS_SOURCES = {
    "H5": (
        "model_contract", "model_blueprint", "derivation_registry", "modeling_solution_contract",
        "run_manifest", "model_summary_cards", "result_interpretation_cards", "paper_narrative",
        "validation_contract", "visual_evidence_packet",
    ),
    "H7": ("figure_registry",),
}

REQUIRED_BY_STAGE = {
    "blueprint": ("content_budget_plan",),
    "solution": ("model_contract", "derivation_registry", "modeling_solution_contract", "run_manifest"),
    "delivery": (
        "model_contract", "derivation_registry", "modeling_solution_contract", "run_manifest",
        "numeric_source_map", "figure_registry", "citation_map",
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def load_structured(path: Path) -> object:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".json":
        return json.loads(raw)
    if yaml is None:
        raise RuntimeError("读取 YAML 证据需要 PyYAML")
    try:
        return yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ValueError(str(exc)) from exc


def _candidate_paths(root: Path, names: tuple[str, ...], errors: list[str]) -> list[Path]:
    candidates: list[Path] = []
    search_roots = (root, root / "01_需求与规划", root / "03_文档", root / "paper", root / "05_输出与交付")
    for folder in search_roots:
        if not folder.is_dir():
            continue
        if not folder.resolve().is_relative_to(root):
            errors.append(f"证据目录不在项目根目录内: {folder.relative_to(root).as_posix()}")
            continue
        for name in names:
            candidate = folder / name
            if candidate.is_file():
                resolved = candidate.resolve()
                if not resolved.is_relative_to(root):
                    errors.append(f"证据来源不在项目根目录内: {candidate.relative_to(root).as_posix()}")
                elif resolved not in candidates:
                    candidates.append(resolved)
    return candidates


def registered_sources(root: Path, errors: list[str]) -> dict[str, Path | None]:
    """Resolve explicit Harness sources without borrowing conventional copies."""
    control_path = root / ".contest/harness_control.yaml"
    if not control_path.exists() and not control_path.is_symlink():
        return {}
    if not control_path.resolve().is_relative_to(root):
        errors.append("harness_control.yaml 不在项目根目录内")
        return {}
    try:
        control = load_structured(control_path)
        if not isinstance(control, dict):
            raise ValueError("控制记录必须为对象")
        if control.get("active_mode") != "full-contest-harness":
            return {}
        nodes = control.get("nodes")
        if not isinstance(nodes, dict):
            raise ValueError("nodes 必须为对象")
    except (OSError, ValueError, RuntimeError) as exc:
        errors.append(f"harness_control.yaml 无法读取: {exc}")
        return {}
    registered: dict[str, Path | None] = {}
    for node_id, fields in HARNESS_SOURCES.items():
        node = nodes.get(node_id, {})
        if not isinstance(node, dict):
            errors.append(f"harness_control.yaml: {node_id} 必须为对象")
            continue
        for kind in fields:
            reference = node.get(kind)
            if reference in (None, ""):
                continue
            registered[kind] = None
            raw = reference.get("path") if isinstance(reference, dict) else reference
            if not isinstance(raw, str) or not raw.strip() or Path(raw).is_absolute():
                errors.append(f"{node_id}.{kind}: 登记必须为项目相对路径")
                continue
            path = (root / raw).resolve()
            if not path.is_relative_to(root):
                errors.append(f"{node_id}.{kind}: 登记来源不在项目根目录内")
                continue
            registered[kind] = path
    return registered


def discover(root: Path, errors: list[str] | None = None,
             registered: dict[str, Path | None] | None = None) -> dict[str, list[Path]]:
    root = root.resolve()
    errors = errors if errors is not None else []
    registered = registered_sources(root, errors) if registered is None else registered
    found: dict[str, list[Path]] = {}
    for kind, names in CORE_NAMES.items():
        if kind in registered:
            found[kind] = [registered[kind]] if registered[kind] is not None else []
            continue
        candidates = _candidate_paths(root, names, errors)
        if candidates:
            found[kind] = candidates[:1]
    if "run_manifest" not in found:
        runs = root / ".contest/runs"
        if not runs.resolve().is_relative_to(root):
            errors.append("运行清单目录不在项目根目录内")
        else:
            manifests = sorted(runs.glob("*/run_manifest.json"))
            for path in manifests:
                if path.resolve().is_relative_to(root):
                    found.setdefault("run_manifest", []).append(path.resolve())
                else:
                    errors.append(f"运行清单不在项目根目录内: {path.relative_to(root).as_posix()}")
    return found


def summarize(kind: str, payload: object) -> dict:
    if not isinstance(payload, dict):
        return {"shape": type(payload).__name__}
    summary: dict[str, object] = {"keys": sorted(str(key) for key in payload)[:40]}
    if "status" in payload:
        summary["status"] = payload["status"]
    if kind == "model_contract":
        items = payload.get("subproblems", [])
        if isinstance(items, list):
            summary["subproblem_ids"] = [item.get("id") for item in items if isinstance(item, dict) and item.get("id")]
    elif kind == "derivation_registry":
        items = payload.get("formulas", payload.get("steps", []))
        if isinstance(items, list):
            summary["entry_count"] = len(items)
    elif kind == "modeling_solution_contract":
        items = payload.get("subproblems", [])
        if isinstance(items, list):
            summary["subproblem_ids"] = [item.get("id") for item in items if isinstance(item, dict) and item.get("id")]
    elif kind == "run_manifest":
        summary.update({"run_id": payload.get("run_id"), "status": payload.get("status"),
                        "exit_code": payload.get("exit_code"), "node_id": payload.get("node_id"),
                        "schema_version": payload.get("schema_version")})
    elif kind in {"model_summary_cards", "result_interpretation_cards"}:
        cards = payload.get("cards", [])
        if isinstance(cards, list):
            summary["subproblem_ids"] = list(dict.fromkeys(
                card["subproblem_id"] for card in cards if isinstance(card, dict)
                and isinstance(card.get("subproblem_id"), str) and card["subproblem_id"].strip()
            ))
            summary["card_ids"] = [card["card_id"] for card in cards if isinstance(card, dict)
                                   and isinstance(card.get("card_id"), str) and card["card_id"].strip()]
    elif kind == "content_budget_plan":
        summary["profile"] = payload.get("profile")
        summary["planning_contract"] = payload.get("planning_contract")
    return summary


def build(root: Path, stage: str, strict: bool, out: Path | None) -> tuple[dict, int]:
    root = root.resolve()
    errors: list[str] = []
    registered = registered_sources(root, errors)
    found = discover(root, errors, registered)
    warnings: list[str] = []
    sources: list[dict] = []
    kind_status: dict[str, str] = {}
    for kind, paths in found.items():
        if not paths:
            kind_status[kind] = "invalid"
            continue
        for path in paths:
            item = {"kind": kind, "path": rel(root, path), "sha256": None, "status": "present",
                    "registered": kind in registered}
            try:
                item["sha256"] = sha256(path)
                payload = load_structured(path)
                item["summary"] = summarize(kind, payload)
            except FileNotFoundError:
                item["status"] = "missing"
                errors.append(f"登记证据来源不存在: {item['path']}")
            except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                item["status"] = "invalid"
                item["error"] = str(exc)
                errors.append(f"{item['path']} 无法解析: {exc}")
            sources.append(item)
        statuses = {item["status"] for item in sources if item["kind"] == kind}
        kind_status[kind] = "missing" if "missing" in statuses else "invalid" if "invalid" in statuses else "present"
    for kind in REQUIRED_BY_STAGE[stage]:
        if kind not in found:
            (errors if strict else warnings).append(f"缺少证据来源: {kind}")
            kind_status[kind] = "missing"
    if stage in {"solution", "delivery"} and "run_manifest" in found:
        for item in sources:
            if item["kind"] != "run_manifest" or item["status"] != "present":
                continue
            record = item["summary"]
            h5_record = record.get("node_id") == "H5" or (item["registered"] and record.get("node_id") is None)
            h5_verified = h5_record and record.get("schema_version") == "1.0" and record.get("status") == "verified"
            if record.get("status") != "completed" and not h5_verified:
                (errors if strict else warnings).append(f"运行清单未成功完成: {item['path']}")
    index = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root),
        "stage": stage,
        "derived": True,
        "source_of_truth": "existing project contracts and run manifests",
        "kinds": kind_status,
        "sources": sources,
        "errors": errors,
        "warnings": warnings,
        # A warning means the derived view is incomplete even though the
        # non-strict command remains usable; callers must not treat it as a
        # successful evidence snapshot.
        "passed": not errors and not warnings,
    }
    destination = out.resolve() if out else root / ".contest" / "evidence_index.json"
    try:
        destination.relative_to(root)
    except ValueError:
        return {"passed": False, "errors": ["evidence index 输出必须位于项目根目录内"]}, 1
    protected = [root / ".contest/harness_control.yaml"] + [path for paths in found.values() for path in paths]
    for source in protected:
        if destination == source.resolve() or (destination.exists() and source.exists() and destination.samefile(source)):
            return {"passed": False, "errors": ["evidence index 输出不得覆盖证据来源或控制记录"]}, 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index, 0 if not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--stage", choices=tuple(REQUIRED_BY_STAGE), default="solution")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    payload, code = build(args.project_root, args.stage, args.strict, args.out)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
