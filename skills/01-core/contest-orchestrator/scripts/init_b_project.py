#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
init_b_project.py — B 题（优化决策类）项目初始化工具

从 templates/b_project_template/ 复制配置模板到新项目目录，
自动填充项目名称、日期等基本信息，生成 README。

用法:
  python scripts/init_b_project.py <项目目录> [--name "项目名称"] [--date "2026-09-XX"]

示例:
  python scripts/init_b_project.py "C:\Users\me\Workspace\2026国赛B题" --name "2026国赛B题"
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
TEMPLATE_DIR = SKILL_ROOT / "templates" / "b_project_template"


def init_project(project_dir: Path, name: str | None = None, date: str | None = None) -> dict:
    """从模板初始化 B 题项目，保留已有输入并拒绝覆盖现有文件。"""
    if not TEMPLATE_DIR.exists():
        raise RuntimeError(f"模板目录不存在: {TEMPLATE_DIR}")

    project_dir = project_dir.resolve()
    if project_dir.exists() and not project_dir.is_dir():
        raise NotADirectoryError(f"项目路径不是目录: {project_dir}")

    # Check every destination before writing, including directory/file conflicts
    # and links that would redirect generated files into an existing directory.
    template_paths = sorted(TEMPLATE_DIR.rglob("*"))
    conflicts = []
    for src in template_paths:
        dst = project_dir / src.relative_to(TEMPLATE_DIR)
        if dst.is_symlink() or dst.resolve() != dst:
            conflicts.append(dst.relative_to(project_dir).as_posix())
        elif dst.exists() and (src.is_file() or not dst.is_dir()):
            conflicts.append(dst.relative_to(project_dir).as_posix())
    readme_path = project_dir / "README.md"
    if readme_path.exists() or readme_path.is_symlink():
        conflicts.append("README.md")
    if conflicts:
        raise FileExistsError(
            "初始化不会覆盖已有文件或链接目录，请选择新目录或先处理冲突: "
            + ", ".join(conflicts)
        )

    project_dir.mkdir(parents=True, exist_ok=True)

    project_name = name or project_dir.name
    project_date = date or datetime.now().strftime("%Y-%m-%d")

    # 复制模板文件
    copied = []
    for src in template_paths:
        if src.is_file():
            rel = src.relative_to(TEMPLATE_DIR)
            dst = project_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation also protects a file created after preflight.
            with src.open("rb") as source, dst.open("xb") as target:
                shutil.copyfileobj(source, target)
            shutil.copystat(src, dst)
            copied.append(str(rel))
        elif src.is_dir():
            # Preserve empty template directories such as paper/ and figures/.
            (project_dir / src.relative_to(TEMPLATE_DIR)).mkdir(parents=True, exist_ok=True)

    # 替换模板中的占位符
    placeholders = {
        "PLACEHOLDER_PROJECT_NAME": project_name,
        "PLACEHOLDER_DATE": project_date,
        "2026-09-XX": project_date,
    }

    replaced = 0
    for relative_path in copied:
        yaml_file = project_dir / relative_path
        if yaml_file.suffix.lower() not in {".yaml", ".yml"}:
            continue
        try:
            text = yaml_file.read_text(encoding="utf-8")
            original = text
            for old, new in placeholders.items():
                if old in text:
                    text = text.replace(old, new)
                    replaced += 1
            if text != original:
                yaml_file.write_text(text, encoding="utf-8")
        except Exception:
            pass

    # 重算任务卡 SHA-256：占位符替换改变了任务卡内容，模板预置的哈希随之失效
    control_path = project_dir / ".contest" / "harness_control.yaml"
    if yaml is not None and control_path.is_file():
        try:
            control = yaml.safe_load(control_path.read_text(encoding="utf-8")) or {}
            control_text = control_path.read_text(encoding="utf-8")
            for record in control.get("dispatch_records") or []:
                if not isinstance(record, dict):
                    continue
                card_rel = record.get("task_card_path")
                old_sha = record.get("task_card_sha256")
                if not card_rel or not old_sha:
                    continue
                card_path = project_dir / card_rel
                if not card_path.is_file():
                    continue
                new_sha = hashlib.sha256(card_path.read_bytes()).hexdigest()
                if new_sha != old_sha:
                    control_text = control_text.replace(old_sha, new_sha)
            control_path.write_text(control_text, encoding="utf-8")
        except Exception:
            pass

    # Generate copyable PowerShell commands without expanding path contents.
    script_argument = (SKILL_ROOT / "scripts").as_posix().replace("'", "''")
    project_argument = project_dir.as_posix().replace("'", "''")
    # 生成 README
    readme = f"""# {project_name}

B 题（优化决策类）数学建模项目，基于 contest-orchestrator skill 模板初始化。

当前各阶段尚未开始，H4 已并入 H5。批准、派发、角色实例与状态历史为空；模型、结果、图表及验证文件均为待填写骨架。完成真实任务与人工审查后，再登记执行证据和批准记录。

## 项目结构

```
{project_dir.name}/
├── .contest/                    # 主控配置
│   ├── harness_control.yaml     # 节点状态、dispatch_records
│   ├── approval_log.yaml        # 用户批准日志
│   ├── status_history.yaml      # 状态转移历史
│   ├── reviews/                 # 各节点审查包（H2、H3、H5-H9）
│   └── task_cards/              # 各节点任务卡（H1, H5-H8）
├── paper/                       # 论文素材
├── figures/                     # 图表
├── results/                     # 结果文件
│   ├── input_manifest.yaml      # H9 输入清单
│   └── sensitivity_report.yaml  # 灵敏度/鲁棒性报告
├── run_manifest.yaml             # H5 可复现运行、正式记录与结果哈希
├── problem_profile.yaml         # 题型画像
├── model_blueprint.yaml         # 模型蓝图
├── model_contract.yaml          # 模型契约
├── validation_contract.yaml     # 验证契约
├── h6_verification_scope.yaml   # H6 验证范围卡
├── appendix_plan.yaml            # H8 附录覆盖与双层代码计划
├── paper_material_readiness.yaml # 论文素材准入
├── result_interpretation_cards.yaml # H5 核心结果解释卡
├── model_summary_cards.yaml      # H5→H6→H8 最终求解模型卡
├── paper_argument_blueprint.yaml # H8 论证蓝图
├── paper_author_brief.yaml       # H8 作者简报
├── chapter_writing_card.yaml     # H8 当前章节写作卡
├── paper_continuity_context.yaml # H8 轻量全文连续性包
├── evidence_gap_matrix.yaml     # 证据缺口矩阵
├── global_interface_check.yaml  # 全局接口检查
├── paper_claim_coverage.yaml    # 主张覆盖表
├── paper_narrative.yaml         # 论文叙事蓝图
├── visual_argument_plan.yaml    # H7 读者优先视觉论证计划
├── visual_evidence_packet.yaml  # H5→H6→H7 轻量视觉证据单元包
└── figure_registry.yaml         # 图表登记
```

## 快速开始

新项目默认使用 `visual_workflow: chapter_parallel`。由已登记的主控与角色完成实际任务，按当前证据取得用户批准；这些步骤不是自动批准授权。

1. **题意与规格（H1-H3）**：从真实题面确定全部小问、数据和约束，完成规格及文献需求确认；文献由用户提供或按约定收集，不补造来源。
2. **建模与求解（H5）**：H4 已并入 H5。唯一主解题实例先形成模型蓝图、契约和快速基线，再按实际问题选工具、求解、优化及冻结结果；记录 run_manifest.yaml、结果卡、模型卡和适用的灵敏度报告。设计材料是首次 H5 任务的产物，不先补造它们作为固定输入。
3. **独立核验（H6）**：用户批准 H5 后，由独立验证角色核验模型、结果和跨问接口，保留冻结原件并登记 global_interface_check.yaml。用户批准 H6 后才进入写作准备；普通正文或排版修改按实际影响处理。
4. **逐章写作准备（H8 角色）**：同一论文角色准备作者简报、摘要论证卡与全篇计划，经用户审查后按 writing_order 先写依赖满足的建模与求解章节。每次提交完整章节并由用户批准，才派发下一章；保留每章写作卡、冻结证据和真实任务记录。最终 chapter_order 是读者顺序，摘要最后写。
5. **图表并行（H7）**：章节批准后，论文角色才生成该章图表提示词，由用户亲自转交图表角色；图件制作与返修可和后续章节写作并行。图表按批准计划、专业路由和 QA 登记，保留各版提示词与选定图件。没有图件需求的章节明确记录即可。
6. **全文整合（H8C）**：全部章节批准且最终 H7 图件闭合后，同一登记论文角色按 chapter_order 整合原正文与选定图件，最后写摘要。复用原计划、各章写作卡和当前哈希，运行严格摘要检查并记录内容快照；旧报告或缺口不能替代当前证据。用户终审全文。
7. **完整交付（H9）**：运行 delivery_all.py --strict 完成完整交付检查，再按真实审查结果登记 H9 并取得用户最终批准。Harness 状态检查不能代替完整交付命令。

## 检查命令

以下 PowerShell 命令引用初始化时的实际技能目录和项目根，可在新项目目录运行。技能移动后按实际安装位置调整脚本路径。

```powershell
# 首次查看题意阶段的登记与缺口，后续按进度调整 --through
python '{script_argument}/check_harness_control.py' '{project_argument}' --through H1

# 题目条件覆盖检查
python '{script_argument}/check_problem_coverage.py' '{project_argument}'

# 题型画像路由
python '{script_argument}/route_problem_profile.py' '{project_argument}'

# 仅在最终交付时运行完整检查
python '{script_argument}/delivery_all.py' '{project_argument}' --strict
```

## 注意事项

- 所有 YAML 文件中的 SHA256 哈希需要在文件创建后重新计算
- 人工批准绑定真实审查包及文件哈希；受影响证据改变时按现有回流规则重新审查，不刷新历史批准冒充通过
- B 题（优化决策类）必须包含灵敏度/鲁棒性报告（P0-02 硬门禁）
- 详细配置说明见 contest-orchestrator/references/b_project_gotchas.md

初始化日期: {project_date}
"""
    with readme_path.open("x", encoding="utf-8") as target:
        target.write(readme)

    return {
        "project_dir": str(project_dir),
        "project_name": project_name,
        "project_date": project_date,
        "files_copied": len(copied),
        "placeholders_replaced": replaced,
        "status": "success",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="B 题（优化决策类）项目初始化工具")
    parser.add_argument("project_dir", help="新项目目录路径")
    parser.add_argument("--name", default=None, help="项目名称（默认使用目录名）")
    parser.add_argument("--date", default=None, help="项目日期（默认今天，格式 YYYY-MM-DD）")
    args = parser.parse_args()

    try:
        result = init_project(Path(args.project_dir), args.name, args.date)
        print(f"=== B 题项目初始化完成 ===")
        print(f"  项目目录: {result['project_dir']}")
        print(f"  项目名称: {result['project_name']}")
        print(f"  项目日期: {result['project_date']}")
        print(f"  复制文件: {result['files_copied']} 个")
        print(f"  替换占位符: {result['placeholders_replaced']} 处")
        print(f"\n下一步: 阅读 {result['project_dir']}/README.md")
        return 0
    except Exception as exc:
        print(f"初始化失败: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
