#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert legacy figure_registry.json metadata to the v2 schema.

The migration preserves the recorded generator as `legacy_generator`; it never
pretends that a figure was produced by SciPilot or manually drawn.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def split_sources(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.replace("；", ",").split(",") if item.strip()]
    return []


def migrate(source: Path) -> dict:
    def unique_fields(pairs):
        record = {}
        for key, value in pairs:
            if key in record:
                raise ValueError(f"登记表存在重复字段: {key}")
            record[key] = value
        return record

    data = json.loads(source.read_text(encoding="utf-8"), object_pairs_hook=unique_fields)
    raw = data.get("figures", data) if isinstance(data, dict) else data
    if isinstance(raw, list):
        indexed = {}
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                raise ValueError(f"figures[{index}] 必须为对象")
            key = str(item.get("id", index))
            if key in indexed:
                raise ValueError(f"图件 ID 重复: {key}")
            indexed[key] = item
        raw = indexed
    if not isinstance(raw, dict):
        raise ValueError("图表登记表必须为对象或图件列表")
    figures = {}
    for key, item in raw.items():
        if not isinstance(item, dict):
            raise ValueError(f"{key}: 图件记录必须为对象")
        # Preserve recorded metadata; only fill structural fields and aliases.
        converted = dict(item)
        defaults = {
            "id": str(key),
            "kind": item.get("type", ""),
            "legacy_generator": item.get("generated_by", item.get("generator", "")),
            "generator": "",
            "source_files": split_sources(item.get("data_source", [])),
            "script": item.get("code", ""),
            "formats": [],
            "qa_status": "review",
            "qa_checks": [],
        }
        for field, value in defaults.items():
            converted.setdefault(field, value)
        if isinstance(converted["source_files"], str):
            converted["source_files"] = split_sources(converted["source_files"])
        figures[str(key)] = converted
    output = dict(data) if isinstance(data, dict) and "figures" in data else {}
    output.update(schema_version="2.0", figures=figures)
    output.setdefault("migrated_at", datetime.now(timezone.utc).isoformat())
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    try:
        output = migrate(source)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.check_only:
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    out = (args.out or source.with_name("figure_registry.v2.json")).resolve()
    if out == source or (out.exists() and out.samefile(source)):
        parser.error("迁移输出不能覆盖原始登记表，请指定另一个 --out 路径")
    if args.out is None and out.exists():
        parser.error("默认迁移候选已存在，请指定另一个 --out 路径")
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"迁移报告已写入: {out}")
    print("注意：legacy_generator 已保留；必须人工确认并补齐 generator、source_files 和 QA 后才能通过门禁。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
