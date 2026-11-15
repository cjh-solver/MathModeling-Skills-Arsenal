"""Local, read-only viewer for Harness contest records."""

import argparse
import csv
import hashlib
import json
import math
import mimetypes
import os
import re
import secrets
import tempfile
import threading
import webbrowser
import zipfile
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml

# CSV previews already reject files larger than 20 MB; allow individual fields
# up to the same bound so long fields can be safely truncated for display.
csv.field_size_limit(20 * 1024 * 1024)

try:
    import pymupdf as fitz
except ImportError:
    fitz = None
try:
    import docx
except ImportError:
    docx = None
try:
    import openpyxl
except ImportError:
    openpyxl = None

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
DEFAULT_PROJECT = None
LINKS_PATH = HERE / "data" / "role_links.json"
ID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
NODE_NAMES = {"H0": "启动", "H1": "题意理解", "H2": "规格冻结", "H3": "文献需求", "H4": "历史节点", "H5": "建模与求解", "H6": "独立验证", "H7": "图表", "H8": "论文", "H9": "交付审查"}
ROLE_NAMES = {"H1": "题意理解", "H5": "解题", "H6": "独立验证", "H7": "图表", "H8": "论文"}
CHAPTER_QUALITY_CHECKS = ("problem_answer", "model_and_derivation", "result_comparison", "interpretation", "continuity", "evidence_provenance")
CHAPTER_KINDS = {"modeling", "validation", "evaluation", "conclusion", "analysis", "front_matter", "appendix", "abstract"}


def valid_visual_slot(slot):
    """Apply the Harness chapter workflow's visual-slot requirements."""
    if not isinstance(slot, dict) or not isinstance(slot.get("slot_id"), str) or not slot["slot_id"]:
        return False
    representation = slot.get("representation")
    mode = representation.get("mode") if isinstance(representation, dict) else representation
    intent = slot.get("figure_intent")
    route = slot.get("generation_route") or (intent.get("generation_route") if isinstance(intent, dict) else None)
    return mode in ("figure", "table", "text") and (mode != "figure" or route in ("modelviz", "tikz-scientific-figures"))
HARNESS_SKILLS = [
    ("contest-orchestrator", "全流程主控"), ("math-model-selector", "模型选择"),
    ("data-science-stack", "数据与验证"), ("scipilot-figure-skill", "科研数据图"),
    ("modelviz", "数据图执行"), ("tikz-scientific-figures", "流程图与示意图"),
    ("academic-writing", "学术写作"), ("mathmodel-latex-skill", "论文排版"),
    ("bzd-review-paper", "论文评审"),
]
PREVIEW_EXTENSIONS = {".md", ".txt", ".yaml", ".yml", ".json", ".tex", ".csv", ".pdf", ".png", ".jpg", ".jpeg", ".svg", ".py", ".bib", ".docx", ".xlsx"}
LIST_EXTENSIONS = PREVIEW_EXTENSIONS | {".docx", ".xlsx", ".xls", ".py", ".ipynb", ".bib", ".zip"}
LINKS_LOCK = threading.Lock()


def json_safe(value, active=None):
    """Keep modeling values visible while emitting valid JSON."""
    if isinstance(value, float) and not math.isfinite(value):
        return "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
    if not isinstance(value, (dict, list, tuple)):
        return value
    active = set() if active is None else active
    if id(value) in active:
        raise ValueError("记录包含循环引用，无法显示")
    active.add(id(value))
    try:
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if isinstance(key, date):
                    output_key = key.isoformat()
                elif isinstance(key, str):
                    output_key = key
                elif key is None or isinstance(key, (bool, int, float)):
                    output_key = json.dumps(key, allow_nan=False)
                else:
                    raise ValueError("记录包含不支持的键类型，无法显示")
                if output_key in result:
                    raise ValueError("记录包含无法区分的键，无法显示")
                result[output_key] = json_safe(item, active)
            return result
        return [json_safe(item, active) for item in value]
    finally:
        active.remove(id(value))


class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        # Explicit fields must be unique; an explicit value may still override a
        # YAML merge, as supported by SafeLoader.
        keys = set()
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                continue
            key = self.construct_object(key_node, deep=deep)
            try:
                if key in keys:
                    raise ValueError(f"YAML 包含重复字段（第 {key_node.start_mark.line + 1} 行）")
                keys.add(key)
            except TypeError as error:
                raise ValueError("YAML 包含不支持的字段类型") from error
        return super().construct_mapping(node, deep=deep)


def read_yaml(path):
    try:
        with path.open(encoding="utf-8-sig") as file:
            value = yaml.load(file, Loader=UniqueKeyLoader)
        if not isinstance(value, dict):
            raise ValueError("内容不是有效的 YAML 对象")
        return value, None
    except (OSError, UnicodeError, yaml.YAMLError, ValueError) as error:
        return {}, str(error)


def recorded_timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.isoformat() if parsed.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def ref_path(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("path"), str):
        return value["path"]
    return None


def project_path(value):
    path = Path(value).expanduser().resolve(strict=True)
    if not path.is_dir():
        raise ValueError("项目路径不是文件夹")
    try:
        safe_file(path, ".contest/harness_control.yaml")
    except (OSError, ValueError) as error:
        raise ValueError("项目控制记录缺失、无法读取或不在项目内") from error
    return path


def safe_file(project, name):
    target = (project / name).resolve(strict=True)
    if not target.is_relative_to(project) or not target.is_file():
        raise ValueError("文件不在当前项目中")
    if target.suffix.lower() not in PREVIEW_EXTENSIONS:
        raise ValueError("暂不支持预览此文件类型")
    if target.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("文件超过 20 MB，无法在工作台预览")
    return target


def unique_json_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON 存在重复字段")
        result[key] = value
    return result


def load_links(path=LINKS_PATH):
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_json_fields)
        if not isinstance(data, dict):
            raise ValueError("角色登记文件格式错误，原记录未修改")
        return data
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError, ValueError) as error:
        raise ValueError(f"角色登记文件无法读取：{error}") from error


def save_link(project, role, thread_id, path=LINKS_PATH, source="manual", title=None):
    role = role.strip()
    thread_id = thread_id.strip()
    if not role or len(role) > 80:
        raise ValueError("角色名称必须为 1–80 个字符")
    if not ID_PATTERN.fullmatch(thread_id):
        raise ValueError("会话 ID 格式不正确，请填写真实 Codex 会话 ID")
    with LINKS_LOCK:
        data = load_links(path)
        key = str(project)
        project_links = data.setdefault(key, {})
        if not isinstance(project_links, dict):
            raise ValueError("角色登记格式错误；为保护记录未进行写入")
        current_links(project_links)
        old = project_links.get(role, [])
        if isinstance(old, str):
            old = [{"thread_id": old, "registered_at": None}]
        if not isinstance(old, list) or any(not isinstance(item, dict) or not isinstance(item.get("thread_id"), str) for item in old):
            raise ValueError("该角色的历史登记格式错误；为保护记录未进行写入")
        if not old or old[-1]["thread_id"].lower() != thread_id.lower():
            old.append({"thread_id": thread_id, "registered_at": datetime.now(timezone.utc).isoformat(), "source": source, "title": title})
        project_links[role] = old
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
            tmp = Path(file.name)
            json.dump(data, file, ensure_ascii=False, indent=2)
        try:
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)


def current_links(data):
    """Read old string links and new append-only histories without inventing identities."""
    links = {}
    histories = {}
    if not isinstance(data, dict):
        raise ValueError("角色登记格式错误")
    for name, value in data.items():
        history = [{"thread_id": value, "registered_at": None}] if isinstance(value, str) else value
        if not isinstance(history, list) or any(not isinstance(item, dict) or not isinstance(item.get("thread_id"), str) for item in history):
            raise ValueError("角色登记历史格式错误")
        if history:
            latest = history[-1]["thread_id"]
            if not ID_PATTERN.fullmatch(latest):
                raise ValueError("角色登记中包含无效的会话 ID")
            links[name] = latest
            histories[name] = history
    return links, histories


def list_files(project):
    """List useful project artifacts without descending into runtimes or dependencies."""
    files = []
    incomplete = False
    excluded = {".git", "node_modules", ".venv", "__pycache__", ".runtime"}
    def scan_error(_error):
        nonlocal incomplete
        incomplete = True

    for root, dirs, names in os.walk(project, followlinks=False, onerror=scan_error):
        directory = Path(root)
        dirs[:] = sorted(d for d in dirs if d not in excluded and not (directory / d).is_symlink())
        if len(directory.relative_to(project).parts) >= 4:
            incomplete = incomplete or bool(dirs)
            dirs[:] = []
        for name in sorted(names):
            item = directory / name
            if item.is_symlink() or item.suffix.lower() not in LIST_EXTENSIONS:
                continue
            try:
                stat = item.stat()
                if len(files) >= 1500:
                    return files, True
                files.append({"path": item.relative_to(project).as_posix(), "modified": stat.st_mtime, "previewable": item.suffix.lower() in PREVIEW_EXTENSIONS and stat.st_size <= 20 * 1024 * 1024})
            except OSError:
                incomplete = True
                continue
    return files, incomplete


def discover_projects(workspace=WORKSPACE):
    """Find candidate Harness roots without walking dependency or temporary trees."""
    candidates = []
    try:
        roots = [workspace] + [p for p in workspace.iterdir() if p.is_dir() and not p.name.startswith((".", "_")) and not p.is_symlink()]
        collection = workspace / "07_数模项目"
        if collection.is_dir():
            roots.extend(p for p in collection.iterdir() if p.is_dir() and not p.name.startswith((".", "_")) and not p.is_symlink())
        for path in roots:
            if (path / ".contest" / "harness_control.yaml").is_file():
                candidates.append({"name": path.name, "path": str(path)})
    except OSError:
        pass
    return sorted(candidates, key=lambda item: item["name"].casefold())


def read_project_yaml(project, relative):
    if not isinstance(relative, str) or not relative:
        return {}, "未登记"
    try:
        return read_yaml(safe_file(project, relative))
    except (OSError, ValueError) as error:
        return {}, str(error)


def project_file_exists(project, relative):
    try:
        path = Path(relative)
        if path.is_absolute():
            return False
        target = (project / path).resolve(strict=True)
        return target.is_relative_to(project) and target.is_file()
    except (OSError, TypeError, ValueError):
        return False


def node_evidence(project, raw, node_id):
    """Read only explicitly recorded task inputs, requested outputs and review evidence."""
    task_path = ref_path(raw.get("task_card"))
    review_path = ref_path(raw.get("review_packet"))
    task, task_error = read_project_yaml(project, task_path)
    review, review_error = read_project_yaml(project, review_path)
    if task.get("node_id") not in (None, node_id):
        task, task_error = {}, "任务卡节点不匹配"
    if review.get("node_id") not in (None, node_id):
        review, review_error = {}, "审查包节点不匹配"

    def entries(value):
        result = []
        for entry in value[:100] if isinstance(value, list) else []:
            path = ref_path(entry)
            if not path:
                continue
            try:
                target = (project / path).resolve(strict=True)
                if not target.is_relative_to(project) or not target.is_file():
                    raise ValueError("不在项目中")
                present = True
                previewable = target.suffix.lower() in PREVIEW_EXTENSIONS and target.stat().st_size <= 20 * 1024 * 1024
            except (OSError, ValueError):
                present, previewable = False, False
            result.append({"path": path, "present": present, "previewable": previewable})
        return result

    related_fields = ("problem_statement", "original_problem_file", "unified_problem_package",
                      "literature_request", "literature_agent_prompt", "literature_sources",
                      "model_contract", "model_blueprint", "model_summary_cards", "validation_contract",
                      "global_interface_check", "figure_registry", "paper_source")
    related = []
    for field in related_fields:
        if path := ref_path(raw.get(field)):
            for item in entries([path]):
                related.append({**item, "field": field})

    return {"task_path": task_path, "task_error": task_error, "review_path": review_path,
            "review_error": review_error, "objective": task.get("objective"),
            "inputs": entries(task.get("inputs")), "required_outputs": entries(task.get("required_outputs")),
            "artifacts": entries(review.get("important_artifacts")), "related": related,
            "review_summary": review.get("summary"), "requested_decision": review.get("requested_decision"),
            "next_node": review.get("proposed_next_node")}


def question_associations(project, question, nodes, dispatch_records, figure_cards, model_cards, result_cards, model_path, figure_path):
    """Resolve recorded coverage and references without attributing file authorship."""
    materials, stages, role_assignments = [], [], []

    def add_material(path, source, relation):
        if not isinstance(path, str) or not path:
            return
        try:
            target = (project / path).resolve(strict=True)
            if not target.is_relative_to(project) or not target.is_file():
                return
            previewable = target.suffix.lower() in PREVIEW_EXTENSIONS and target.stat().st_size <= 20 * 1024 * 1024
        except (OSError, ValueError):
            return
        item = {"path": path, "source": source, "relation": relation, "previewable": previewable}
        if item not in materials:
            materials.append(item)

    if any(isinstance(card, dict) and card.get("subproblem_id") == question for card in model_cards):
        add_material(model_path, model_path, "模型卡明确登记小问；文件包含其他小问")
    for card in result_cards:
        if isinstance(card, dict) and card.get("subproblem_id") == question:
            add_material(ref_path(card.get("evidence")), "结果解释卡", "结果卡明确登记的证据")
    for figure in figure_cards:
        if not isinstance(figure, dict):
            continue
        explicit = figure.get("subproblem_id") == question
        figure_id = figure.get("figure_id")
        candidate = isinstance(figure_id, str) and re.fullmatch(r"H\d+-" + re.escape(question), figure_id, re.IGNORECASE)
        if explicit or candidate:
            relation = "图表记录明确关联小问" if explicit else "可能相关：图表编号包含小问编号"
            for value in (figure.get("png"), figure.get("svg")):
                add_material(ref_path(value), figure_path or "图表登记", relation)

    records = dispatch_records if isinstance(dispatch_records, list) else []
    for node_id, raw in nodes.items():
        if node_id not in NODE_NAMES or not isinstance(raw, dict):
            continue
        task_path = ref_path(raw.get("task_card"))
        task, error = read_project_yaml(project, task_path)
        if error or task.get("node_id") != node_id:
            continue
        coverage = task.get("covered_subproblems")
        if not isinstance(coverage, list) or question not in coverage:
            continue
        stages.append({"id": node_id, "name": NODE_NAMES[node_id], "source": task_path})
        for record in records:
            if not isinstance(record, dict) or record.get("node_id") != node_id:
                continue
            if not task.get("task_id") or record.get("task_id") != task.get("task_id") or record.get("task_card_path") != task_path:
                continue
            owner = record.get("owner_role")
            if task.get("owner_role") and task.get("owner_role") != owner:
                continue
            if isinstance(owner, str) and owner:
                assignment = {"name": owner, "node": node_id, "task_id": record["task_id"], "source": task_path}
                if assignment not in role_assignments:
                    role_assignments.append(assignment)
    return {"materials": materials, "stages": stages, "roles": role_assignments}


def read_report(project, relative, title):
    try:
        target = safe_file(project, relative)
        with target.open(encoding="utf-8-sig") as file:
            data = json.load(file, object_pairs_hook=unique_json_fields)
        if not isinstance(data, dict):
            raise ValueError("报告不是对象")
        passed = data.get("passed")
        return {"title": title, "path": relative, "passed": passed if isinstance(passed, bool) else None,
                "issues": [str(item) for item in data.get("issues", [])[:20]] if isinstance(data.get("issues"), list) else [],
                "modified": target.stat().st_mtime, "error": None}
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as error:
        return {"title": title, "path": relative, "passed": None, "issues": [], "modified": None, "error": str(error)}


def validate_office_archive(path):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > 10000 or sum(item.file_size for item in entries) > 150 * 1024 * 1024:
            raise ValueError("文档解压后的内容过大，无法预览")


def digest_status(project, entries):
    """Compare recorded file hashes only; this does not validate approvals or gates."""
    if not isinstance(entries, dict):
        return {"status": "unrecorded", "files": []}
    results = []
    for number, (name, expected) in enumerate(entries.items()):
        item = {"path": str(name), "status": "unverified"}
        if number >= 100:
            item["status"] = "limit"
        elif not isinstance(name, str) or Path(name).is_absolute():
            item["status"] = "unverified"
        elif not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
            item["status"] = "invalid_digest"
        else:
            try:
                target = (project / name).resolve(strict=True)
                if not target.is_relative_to(project) or not target.is_file():
                    raise ValueError("outside")
                if target.stat().st_size > 100 * 1024 * 1024:
                    item["status"] = "limit"
                else:
                    digest = hashlib.sha256()
                    with target.open("rb") as file:
                        for chunk in iter(lambda: file.read(1024 * 1024), b""):
                            digest.update(chunk)
                    item["status"] = "matches" if digest.hexdigest().lower() == expected.lower() else "changed"
            except FileNotFoundError:
                item["status"] = "missing"
            except (OSError, ValueError, TypeError):
                item["status"] = "unverified"
        results.append(item)
    statuses = {item["status"] for item in results}
    summary = "matches" if statuses == {"matches"} else "issues" if statuses else "unrecorded"
    return {"status": summary, "files": results}


def build_state(project, links_path=LINKS_PATH):
    control_path = project / ".contest" / "harness_control.yaml"
    control, error = read_project_yaml(project, ".contest/harness_control.yaml")
    if error:
        raise ValueError(f"无法读取控制记录：{error}")
    if control.get("active_mode") != "full-contest-harness":
        raise ValueError("此项目未声明 full-contest-harness 模式")
    nodes = control.get("nodes") if isinstance(control.get("nodes"), dict) else {}
    result_nodes = []
    for key in ["H0", "H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "H9"]:
        raw = nodes.get(key)
        if not isinstance(raw, dict) or (key == "H4" and raw.get("status") == "merged"):
            continue
        invocations = raw.get("skill_invocations") if isinstance(raw.get("skill_invocations"), list) else []
        result_nodes.append({"id": key, "name": NODE_NAMES[key], "status": str(raw.get("status") or "unknown"), "review": ref_path(raw.get("review_packet")), "owner": raw.get("owner_role"), "evidence": node_evidence(project, raw, key), "skills": [{"name": entry.get("skill"), "completed": entry.get("completed"), "not_applicable": entry.get("not_applicable"), "reason": entry.get("reason"), "evidence": ref_path(entry.get("evidence_ref"))} for entry in invocations if isinstance(entry, dict)]})
    instances = control.get("agent_instances") if isinstance(control.get("agent_instances"), dict) else {}
    links_error = None
    try:
        links, histories = current_links(load_links(links_path).get(str(project), {}))
    except ValueError as error:
        links, histories, links_error = {}, {}, str(error)
    roles = [{"name": "主控", "node": "H0", "instance_id": None, "thread_id": links.get("主控")}]
    for key, name in ROLE_NAMES.items():
        instance = instances.get(key, {})
        node = nodes.get(key, {})
        instance_id = instance.get("agent_instance_id") if isinstance(instance, dict) else None
        if not instance_id and isinstance(node, dict):
            instance_id = node.get("agent_instance_id")
        roles.append({"name": name, "node": key, "instance_id": instance_id, "thread_id": links.get(name)})
    known_instances = {item["instance_id"] for item in roles if item["instance_id"]}
    records = control.get("dispatch_records", [])
    if isinstance(records, list):
        for record in records:
            if not isinstance(record, dict):
                continue
            instance_id = record.get("agent_instance_id")
            if not isinstance(instance_id, str) or not instance_id or instance_id in known_instances:
                continue
            name = str(record.get("owner_role") or "辅助角色") + " · " + instance_id
            roles.append({"name": name, "node": record.get("node_id"), "instance_id": instance_id, "thread_id": links.get(name)})
            known_instances.add(instance_id)
    for name, thread_id in links.items():
        if name not in {item["name"] for item in roles}:
            roles.append({"name": name, "node": None, "instance_id": None, "thread_id": thread_id})
    registry_path = project / ".contest" / "agent_registry.yaml"
    registry, registry_error = read_project_yaml(project, ".contest/agent_registry.yaml") if registry_path.exists() else ({}, "记录缺失")
    instances_in_registry = registry.get("instances") if isinstance(registry.get("instances"), list) else []
    if not registry_error and not isinstance(registry.get("instances"), list):
        registry_error = "角色实例列表未登记或格式错误"
    elif not registry_error and any(not isinstance(entry, dict) for entry in instances_in_registry):
        registry_error = "角色实例列表包含格式错误的条目"
    for entry in instances_in_registry:
        if not isinstance(entry, dict):
            continue
        instance_id = entry.get("agent_instance_id")
        role = next((r for r in roles if instance_id and r.get("instance_id") == instance_id), None)
        if role is None:
            name = str(entry.get("role") or "未命名角色")
            if name in {r["name"] for r in roles}:
                name += " · " + str(instance_id or entry.get("client_thread_id") or "待核")
            role = {"name": name, "node": None, "instance_id": instance_id, "thread_id": None}
            roles.append(role)
        role["registry_status"] = entry.get("status")
        role["registry_accessible"] = entry.get("user_accessible")
        role["registry_thread_id"] = entry.get("thread_id") if isinstance(entry.get("thread_id"), str) and ID_PATTERN.fullmatch(entry["thread_id"]) else None
        role["registry_source"] = ".contest/agent_registry.yaml"
        if not links_error and not role["thread_id"] and role["registry_thread_id"]:
            role["thread_id"] = role["registry_thread_id"]
            role["link_source"] = "project_registry"
    for role in roles:
        role["history"] = histories.get(role["name"], [])
        if role.get("thread_id") and not role.get("link_source"):
            role["link_source"] = (role["history"][-1].get("source") if role["history"] else None) or "manual"
        role["dispatches"] = [{"task_id": record.get("task_id"), "node": record.get("node_id"), "model": record.get("model"), "reasoning_effort": record.get("reasoning_effort"), "task_card_path": record.get("task_card_path")} for record in records if isinstance(record, dict) and role.get("instance_id") and record.get("agent_instance_id") == role["instance_id"]] if isinstance(records, list) else []
    approvals_path = project / ".contest" / "approval_log.yaml"
    approvals, approval_error = read_project_yaml(project, ".contest/approval_log.yaml") if approvals_path.exists() else ({}, "记录缺失")
    approvals_list = approvals.get("approvals", [])
    if "approvals" not in approvals and not approval_error:
        approval_error = "批准记录列表未登记"
    elif not isinstance(approvals_list, list):
        approvals_list = []
        approval_error = approval_error or "批准记录列表格式错误"
    elif any(not isinstance(item, dict) or
             any(not isinstance(item.get(field), str) or not item[field].strip()
                 for field in ("gate", "decision"))
             for item in approvals_list):
        approval_error = approval_error or "批准记录包含格式错误的条目"
    scope = control.get("problem_scope") if isinstance(control.get("problem_scope"), dict) else {}
    subproblems = scope.get("subproblems", [])
    h7 = nodes.get("H7") if isinstance(nodes.get("H7"), dict) else {}
    preparation = h7.get("writer_preparation") if isinstance(h7.get("writer_preparation"), dict) else {}
    plan_ref = preparation.get("writing_plan") if isinstance(preparation.get("writing_plan"), dict) else {}
    plan_path = plan_ref.get("path")
    plan, plan_error = read_project_yaml(project, plan_path)
    plan_hash = digest_status(project, {plan_path: plan_ref.get("sha256")}) if isinstance(plan_path, str) else {"status": "unrecorded", "files": []}
    writing_plan = {"path": plan_path, "review_packet": ref_path(preparation.get("plan_review_packet")), "error": plan_error, "hash": plan_hash["status"],
                    "chapter_order": plan.get("chapter_order"), "writing_order": plan.get("writing_order"),
                    "central_thesis": plan.get("central_thesis"), "reader_journey": plan.get("reader_journey")}
    chapter_items = preparation.get("chapters", [])
    chapters = []
    if isinstance(chapter_items, list):
        for item in chapter_items:
            if not isinstance(item, dict):
                continue
            draft = item.get("draft") if isinstance(item.get("draft"), dict) else {}
            revisions = item.get("visual_prompts") if isinstance(item.get("visual_prompts"), list) else []
            prompts = []
            for revision in revisions:
                if not isinstance(revision, dict):
                    continue
                ref = revision.get("prompt") if isinstance(revision.get("prompt"), dict) else {}
                prompt_path = ref.get("path")
                prompt_hash = digest_status(project, {prompt_path: ref.get("sha256")}) if isinstance(prompt_path, str) else {"status": "unrecorded"}
                visual_ref = revision.get("visual_plan") if isinstance(revision.get("visual_plan"), dict) else {}
                visual_path = visual_ref.get("path")
                visual_hash = digest_status(project, {visual_path: visual_ref.get("sha256")}) if isinstance(visual_path, str) else {"status": "unrecorded"}
                visual_plan, visual_error = read_project_yaml(project, visual_path)
                revision_id = revision.get("revision_id")
                slots = visual_plan.get("slots")
                chapter_id = item.get("chapter_id")
                plan_binding = not visual_error and isinstance(chapter_id, str) and bool(chapter_id.strip()) and isinstance(revision_id, str) and bool(revision_id.strip()) and (
                    visual_plan.get("chapter_id") == item.get("chapter_id") and
                    visual_plan.get("revision_id") == revision_id and
                    visual_plan.get("draft") == draft and isinstance(slots, list) and bool(slots) and
                    all(valid_visual_slot(slot) for slot in slots)
                )
                prompts.append({"revision": revision.get("revision_id"), "path": prompt_path,
                                "hash": prompt_hash["status"], "sha256": ref.get("sha256"), "visual_plan_path": visual_path,
                                "visual_plan_hash": visual_hash["status"], "plan_binding": plan_binding,
                                "prepared_at": recorded_timestamp(revision.get("prepared_at")), "supersedes": revision.get("supersedes")})
            draft_path = draft.get("path")
            draft_hash = digest_status(project, {draft_path: draft.get("sha256")}) if isinstance(draft_path, str) else {"status": "unrecorded"}
            quality = item.get("quality_review") if isinstance(item.get("quality_review"), dict) else {}
            quality_path = quality.get("path")
            quality_hash = digest_status(project, {quality_path: quality.get("sha256")}) if isinstance(quality_path, str) else {"status": "unrecorded"}
            quality_data, quality_error = read_project_yaml(project, quality_path)
            definitions = plan.get("chapters") if isinstance(plan.get("chapters"), list) else []
            matching_definitions = [entry for entry in definitions if isinstance(entry, dict) and entry.get("chapter_id") == item.get("chapter_id")]
            kind = matching_definitions[0].get("kind") if len(matching_definitions) == 1 else None
            checks = quality_data.get("checks")
            draft_sha = draft.get("sha256")
            quality_ready = (
                not quality_error and plan_hash["status"] == "matches" and isinstance(kind, str) and kind in CHAPTER_KINDS and
                draft_hash["status"] == "matches" and isinstance(draft_sha, str) and
                quality_data.get("status") == "ready" and quality_data.get("draft_sha256") == draft_sha.lower() and
                isinstance(checks, dict) and all(
                    checks.get(key) == "PASS" or (isinstance(checks.get(key), dict) and
                    checks[key].get("status") == "not_applicable" and bool(checks[key].get("reason")))
                    for key in CHAPTER_QUALITY_CHECKS
                ) and (kind != "modeling" or checks.get("model_and_derivation") == "PASS")
            )
            chapters.append({"id": str(item.get("chapter_id") or "未命名章节"), "draft": draft_path, "draft_hash": draft_hash["status"],
                             "draft_completed_at": recorded_timestamp(item.get("draft_completed_at")),
                             "quality_review": quality_path, "quality_hash": quality_hash["status"], "quality_ready": quality_ready,
                             "review_packet": ref_path(item.get("review_packet")), "visuals_required": item.get("visuals_required"),
                             "prompt_revisions": len(prompts), "prompts": prompts})
    h1 = nodes.get("H1") if isinstance(nodes.get("H1"), dict) else {}
    h3 = nodes.get("H3") if isinstance(nodes.get("H3"), dict) else {}
    h5 = nodes.get("H5") if isinstance(nodes.get("H5"), dict) else {}
    profile_path = ref_path(h1.get("unified_problem_package"))
    model_path = ref_path(h5.get("model_summary_cards"))
    result_path = ref_path(h5.get("result_interpretation_cards"))
    figure_path = ref_path(h7.get("figure_registry"))
    profile, profile_error = read_project_yaml(project, profile_path)
    models, models_error = read_project_yaml(project, model_path)
    interpretations, interpretations_error = read_project_yaml(project, result_path)
    figures, figures_error = read_project_yaml(project, figure_path)
    question_details = profile.get("questions") if isinstance(profile.get("questions"), dict) else {}
    model_cards = models.get("cards") if isinstance(models.get("cards"), list) else []
    result_cards = interpretations.get("cards") if isinstance(interpretations.get("cards"), list) else []
    figure_cards = figures.get("figures") if isinstance(figures.get("figures"), list) else []
    question_views = []
    for question in subproblems if isinstance(subproblems, list) else []:
        if not isinstance(question, str):
            continue
        detail = question_details.get(question) if isinstance(question_details.get(question), dict) else {}
        objectives = profile.get("objectives") if isinstance(profile.get("objectives"), dict) else {}
        question_views.append({
            "id": question, "objective": objectives.get(question), "inputs": detail.get("inputs"),
            "outputs": detail.get("outputs"), "interface": detail.get("cross_question_interface"),
            "models": [{"id": str(card.get("card_id") or "未命名"), "result": card.get("result"), "solver_interface": card.get("solver_interface")} for card in model_cards if isinstance(card, dict) and card.get("subproblem_id") == question],
            "interpretations": [{"id": card.get("id"), "fact": card.get("fact"), "meaning": card.get("meaning"), "boundary": card.get("boundary"), "evidence": card.get("evidence"), "verification": card.get("verification")} for card in result_cards if isinstance(card, dict) and card.get("subproblem_id") == question],
            "associations": question_associations(project, question, nodes, records, figure_cards, model_cards, result_cards, model_path, figure_path),
        })
    figure_views = []
    for figure in figure_cards:
        if not isinstance(figure, dict):
            continue
        sources = figure.get("source_files") if isinstance(figure.get("source_files"), list) else []
        figure_views.append({"id": str(figure.get("figure_id") or "未命名"), "png": ref_path(figure.get("png")), "svg": ref_path(figure.get("svg")), "source_files": [path for source in sources if (path := ref_path(source))], "caption": figure.get("caption_claim") or figure.get("claim"), "location": figure.get("paper_location"), "qa_status": figure.get("qa_status")})
    skill_root = Path.home() / ".agents" / "skills"
    skills = [{"name": name, "purpose": purpose, "available": (skill_root / name / "SKILL.md").is_file()} for name, purpose in HARNESS_SKILLS]
    files, truncated = list_files(project)
    h8 = nodes.get("H8") if isinstance(nodes.get("H8"), dict) else {}
    paper_source = ref_path(h8.get("paper_source"))
    paper_pdf = str(Path(paper_source).with_suffix(".pdf")).replace("\\", "/") if paper_source else None
    if not paper_pdf or not project_file_exists(project, paper_pdf):
        paper_pdf = None
    literature = [{"name": name, "path": ref_path(h3.get(field))} for field, name in [("literature_request", "文献需求"), ("literature_agent_prompt", "外部文献角色提示词"), ("literature_sources", "用户回传的结构化文献")]]
    reports = [read_report(project, path, title) for path, title in
               [("paper/compile_report.json", "论文编译报告"), ("paper/delivery_gate_report.json", "历史交付检查报告")]
               if project_file_exists(project, path)]
    return {
        "project": str(project), "name": project.name, "available_projects": discover_projects(),
        "run_id": control.get("harness_run_id"), "mode": control.get("active_mode"),
        "authorization_mode": approvals.get("authorization_mode"),
        "visual_workflow": control.get("visual_workflow") or "未记录（历史流程）",
        "chapters": chapters, "writing_plan": writing_plan, "paper_source": paper_source, "paper_pdf": paper_pdf, "reports": reports,
        "nodes": result_nodes, "roles": roles, "registry_error": registry_error, "role_links_error": links_error,
        "literature": literature, "subproblems": subproblems if isinstance(subproblems, list) else [],
        "question_views": question_views,
        "question_sources": {"profile": profile_path, "profile_error": profile_error,
                             "models": model_path, "models_error": models_error,
                             "results": result_path, "results_error": interpretations_error},
        "figures": figure_views, "figure_source": figure_path, "figure_error": figures_error,
        "skills": skills, "capabilities": {"pdf_preview": fitz is not None, "docx_preview": docx is not None, "xlsx_preview": openpyxl is not None},
        "approvals": [
            {"gate": a.get("gate"), "decision": a.get("decision"),
             "timestamp": recorded_timestamp(a.get("timestamp")),
             "digests": digest_status(project, a.get("artifact_digests"))}
            for a in approvals_list if isinstance(a, dict)
        ],
        "approval_error": approval_error,
        "approval_note": "哈希对比仅检查登记文件的当前内容，不能证明批准真实性或替代 Harness 门禁。",
        "files": files, "files_truncated": truncated, "source": str(control_path),
    }


class Handler(BaseHTTPRequestHandler):
    project = DEFAULT_PROJECT
    links_path = LINKS_PATH
    token = secrets.token_urlsafe(32)

    def respond(self, status, data, content_type="application/json; charset=utf-8"):
        body = json.dumps(json_safe(data), ensure_ascii=False, default=str, allow_nan=False).encode("utf-8") if isinstance(data, (dict, list)) else data
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def local_host(self):
        hosts = self.headers.get_all("Host", [])
        port = self.server.server_port
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if port == 80:
            allowed.update({"127.0.0.1", "localhost"})
        return len(hosts) == 1 and hosts[0].lower() in allowed

    def do_GET(self):
        if not self.local_host():
            return self.respond(403, {"error": "仅允许通过本机地址访问工作台"})
        url = urlsplit(self.path)
        try:
            params = parse_qs(url.query)
            requested = params.get("project", [""])[0]
            project = project_path(requested) if requested else self.project
            if url.path == "/api/bootstrap":
                return self.respond(200, {"token": self.token, "available_projects": discover_projects()})
            if project is None and url.path.startswith("/api/"):
                raise ValueError("尚未选择项目，请点击右上角加号添加已有项目")
            if url.path == "/api/state":
                state = build_state(project, self.links_path)
                state["token"] = self.token
                return self.respond(200, state)
            if url.path in {"/api/pdf-info", "/api/pdf-page"}:
                if fitz is None:
                    raise ValueError("缺少 PyMuPDF，无法生成页面预览")
                target = safe_file(project, params.get("path", [""])[0])
                if target.suffix.lower() != ".pdf":
                    raise ValueError("文件不是 PDF")
                try:
                    with fitz.open(target) as document:
                        if document.needs_pass:
                            raise ValueError("无法预览加密 PDF")
                        if url.path == "/api/pdf-info":
                            return self.respond(200, {"pages": len(document)})
                        page_number = int(params.get("page", ["1"])[0])
                        if page_number < 1 or page_number > len(document):
                            raise ValueError("PDF 页码超出范围")
                        page = document.load_page(page_number - 1)
                        if page.rect.width > 5000 or page.rect.height > 5000:
                            raise ValueError("PDF 页面尺寸过大")
                        return self.respond(200, page.get_pixmap(matrix=fitz.Matrix(1.25, 1.25), alpha=False).tobytes("png"), "image/png")
                except (RuntimeError, fitz.FileDataError) as error:
                    raise ValueError(f"PDF 读取失败：{error}") from error
            if url.path == "/api/document":
                target = safe_file(project, params.get("path", [""])[0])
                if target.suffix.lower() == ".csv":
                    rows = None
                    for encoding in ("utf-8-sig", "gb18030"):
                        try:
                            with target.open(encoding=encoding, newline="") as file:
                                reader = csv.reader(file)
                                rows = [[value[:5000] for value in row[:20]] for _, row in zip(range(30), reader)]
                            break
                        except UnicodeDecodeError:
                            continue
                    if rows is None:
                        raise ValueError("无法识别 CSV 编码")
                    return self.respond(200, {"type": "csv", "rows": rows, "note": f"最多显示前 30 行、20 列，每个单元格最多显示 5000 字符；读取编码：{encoding}。"})
                if target.suffix.lower() == ".docx":
                    if docx is None:
                        raise ValueError("缺少 python-docx，无法预览 Word 文件")
                    validate_office_archive(target)
                    try:
                        document = docx.Document(target)
                    except SyntaxError as error:
                        raise ValueError("文档内容格式错误，无法预览") from error
                    paragraphs, tables, blocks = [], [], []
                    for element in document.element.body.iterchildren():
                        if element.tag == docx.oxml.ns.qn("w:p") and len(paragraphs) < 300:
                            text = docx.text.paragraph.Paragraph(element, document).text[:5000]
                            paragraphs.append(text)
                            blocks.append({"type": "paragraph", "text": text})
                        elif element.tag == docx.oxml.ns.qn("w:tbl") and len(tables) < 10:
                            table = docx.table.Table(element, document)
                            rows = [[cell.text[:5000] for cell in row.cells[:20]] for row in table.rows[:30]]
                            tables.append(rows)
                            blocks.append({"type": "table", "rows": rows})
                    return self.respond(200, {"type": "docx", "paragraphs": paragraphs, "tables": tables, "blocks": blocks, "note": "最多显示前 300 段及前 10 个表格，每表前 30 行、20 列，每段或单元格最多 5000 字符；图片、公式和原排版可能无法完整呈现。"})
                if target.suffix.lower() == ".xlsx":
                    if openpyxl is None:
                        raise ValueError("缺少 openpyxl，无法预览 Excel 文件")
                    validate_office_archive(target)
                    try:
                        workbook = openpyxl.load_workbook(target, read_only=True, data_only=False, keep_links=False)
                    except SyntaxError as error:
                        raise ValueError("文档内容格式错误，无法预览") from error
                    try:
                        sheets = [sheet.title for sheet in workbook.worksheets]
                        if not sheets:
                            raise ValueError("Excel 文件没有可预览的数据工作表")
                        sheet_name = params.get("sheet", [""])[0] or sheets[0]
                        if sheet_name in workbook.sheetnames and sheet_name not in sheets:
                            raise ValueError("图表工作表暂不支持预览")
                        if sheet_name not in sheets:
                            raise ValueError("未找到指定工作表")
                        sheet = workbook[sheet_name]
                        raw_rows = list(sheet.iter_rows(max_row=30, max_col=20, values_only=True))
                        actual_width = max((index for row in raw_rows for index, value in enumerate(row, 1) if value is not None), default=1)
                        width = max(min(sheet.max_column or 1, 20), actual_width)
                        rows = [[str(value)[:5000] if value is not None else "" for value in row[:width]] for row in raw_rows]
                        note = "最多显示前 30 行、20 列，每个单元格最多显示 5000 字符；公式以原文显示，不重新计算。"
                        if len(sheets) != len(workbook.sheetnames):
                            note += "图表工作表不在预览列表中。"
                        return self.respond(200, {"type": "xlsx", "sheets": sheets, "sheet": sheet_name, "rows": rows, "note": note})
                    except SyntaxError as error:
                        raise ValueError("文档内容格式错误，无法预览") from error
                    finally:
                        workbook.close()
                raise ValueError("不支持此文档类型")
            if url.path == "/api/file":
                name = params.get("path", [""])[0]
                target = safe_file(project, name)
                mime = mimetypes.guess_type(target.name)[0] or "text/plain"
                if target.suffix.lower() in {".yaml", ".yml", ".tex", ".md", ".py", ".bib"}:
                    mime = "text/plain; charset=utf-8"
                # SVG may contain active script; render it as plain text instead.
                if target.suffix.lower() == ".svg":
                    mime = "text/plain; charset=utf-8"
                return self.respond(200, target.read_bytes(), mime)
            static = {"/": ("index.html", "text/html; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8"), "/details.css": ("details.css", "text/css; charset=utf-8"), "/theme.css": ("theme.css", "text/css; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/ranking.js": ("ranking.js", "text/javascript; charset=utf-8")}
            if url.path in static:
                name, mime = static[url.path]
                return self.respond(200, (HERE / "static" / name).read_bytes(), mime)
            return self.respond(404, {"error": "未找到"})
        except (OSError, ValueError, TypeError, KeyError, csv.Error, zipfile.BadZipFile) as error:
            return self.respond(400, {"error": str(error)})

    def do_POST(self):
        if not self.local_host():
            return self.respond(403, {"error": "仅允许通过本机地址访问工作台"})
        try:
            origin = self.headers.get("Origin", "")
            expected = f"http://127.0.0.1:{self.server.server_port}"
            if origin != expected or self.headers.get("X-Workbench-Token") != self.token:
                return self.respond(403, {"error": "请求来源或令牌无效"})
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 8192:
                raise ValueError("请求大小无效")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("请求内容必须是对象")
            if self.path == "/api/project":
                candidate = project_path(body.get("path", ""))
                build_state(candidate, self.links_path)
            elif self.path == "/api/role-link":
                project = project_path(body.get("project", ""))
                save_link(project, body.get("role", ""), body.get("thread_id", ""), self.links_path)
            else:
                return self.respond(404, {"error": "未找到"})
            return self.respond(200, {"ok": True})
        except (ValueError, TypeError, OSError, json.JSONDecodeError) as error:
            return self.respond(400, {"error": str(error)})


def main():
    parser = argparse.ArgumentParser(description="Local Harness workbench")
    parser.add_argument("--project", default=None)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="Open the workbench in the default browser")
    args = parser.parse_args()
    Handler.project = project_path(args.project) if args.project else None
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Harness workbench: http://127.0.0.1:{server.server_port}/", flush=True)
    if args.open:
        webbrowser.open(f"http://127.0.0.1:{server.server_port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
