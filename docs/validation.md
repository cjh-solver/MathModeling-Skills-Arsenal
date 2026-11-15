# 验证结果与适用边界

## 检查的含义

本仓库的测试检查流程契约和工具行为，例如未批准就派发下一章、遗漏冻结输入、修改已批准正文、使用旧图件版本时应被拒绝。这些检查不能证明模型精度、获奖概率、长篇论文质量或某一宿主的真实多角色调用已发生。

`examples/chapter-parallel` 使用可复算的合成线性数据，其误差为零源于数据构造方式。示例中的正文、交接提示词不构成真实比赛记录或自动生成质量评测。

## 2026-11-15 维护检查

公开版 CUMCM 排版适配器已在本机用 XeLaTeX 编译三个模板及布局冒烟样例，并用合成 SVG 验证 Inkscape 转换链路。CI 检查模板与布局命令的契约；这些检查不代表真实论文或特定比赛规则已通过交付审核。

在 Windows、Python 3.13 环境下，公开仓库的 Harness 106 项、MathorCup 140 项测试通过；工作台 Python 28 项和 Node.js 33 项测试通过。仓库检查和合成数据示例通过。GitHub Actions 的实时结果以[工作流页面](https://github.com/cjh-solver/MathModeling-Skills-Arsenal/actions/workflows/validate.yml)为准。

完整严格检查仍未通过：版本登记不一致、15 个脚本尚未分类，且部分未发布的私有引用缺失。健康检查现已识别仓库的分类目录，不再把仓库中存在的技能包误报为缺失；这只证明包在仓库中，不证明宿主已安装或能调用它们。需要逐项处理剩余问题后才能评价完整发布状态。

## 2026-11-01 历史记录

同步前的维护环境为 Windows、Python 3.13：MathorCup 140 项、Harness 106 项相关测试通过；严格 smoke 和机理、优化、预测三类 replay 通过。完整检查点运行 617 项，其中 616 项通过，一项原有一致性检查失败；其后新增两项返修链测试由最终 MathorCup 套件覆盖。

这些是当时的维护检查，不是本届比赛的重训、正式论文编译或提交验证。公开副本当时的复查结果记录在 [public-validation.json](public-validation.json)；其中日期与数量是历史快照，不自动代表最新运行结果。

## 已知发布阻碍

- 主控 `VERSION` 与 manifest 登记 4.18，SKILL 元数据为 4.19，发布登记尚未统一。本次更新不提升稳定版版本号。
- 15 个历史维护脚本尚未在技能内部 registry 分类；严格检查还会指出部分私有引用缺失。
- 因此，针对相关流程的 CI 通过不等于完整发布检查通过；`test_current_skill_passes_strict_consistency_audit` 记录了版本与分类问题。
- 临时工程代理与用户可直接进入的长期角色会话不是同一能力。MathorCup 本次独立工程审查代理因工作区额度限制未完成最终审查；本地测试不冒充独立签署。

## 本地复现

```bash
python -m pip install pyyaml
python scripts/check_repository.py
python examples/chapter-parallel/calculate.py
cd skills/01-core/contest-orchestrator
python -m unittest discover -s tests -p 'test_mathorcup*.py'
python -m unittest discover -s tests -p 'test_harness*.py'

# 完整检查：目前预期会报告上面的既有一致性阻碍。
python -m unittest discover -s tests -p 'test_*.py'
python scripts/skill_health_check.py . --strict --smoke
python scripts/replay_profiles.py --strict
```

科研绘图需要真实数据、语义与视觉 QA；LaTeX 交付还需要真实编译、字体、SVG 转换和引用检查。仅源码检查或测试夹具中的 PDF 不能被称作可提交论文。
