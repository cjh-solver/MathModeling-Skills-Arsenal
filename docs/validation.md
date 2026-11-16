# 验证结果与适用边界

## 检查的含义

本仓库的测试检查流程契约和工具行为，例如未批准就派发下一章、遗漏冻结输入、修改已批准正文、使用旧图件版本时应被拒绝。这些检查不能证明模型精度、获奖概率、长篇论文质量或某一宿主的真实多角色调用已发生。

`examples/chapter-parallel` 使用可复算的合成线性数据，其误差为零源于数据构造方式。示例中的正文、交接提示词不构成真实比赛记录或自动生成质量评测。

## 2026-11-17 安装副本核对

核对发现，版本号相同并不代表安装副本已包含仓库里的全部修复。此次补齐维护环境安装副本中遗漏的 5 个回归用例及对应实现：增量复核不得跳过更早的失效节点，非法变更卡须返回错误，论文草稿准入在控制记录或批准日志缺失时须保持阻塞。对齐后，`validation_router.py` 和 `check_harness_control.py` 的 Python 语法树与公开版一致；用户数据和项目批准记录未参与同步。

以下差异需按用途处理，不能用测试总数或整目录覆盖代替核对：

| 差异 | 处理方式 |
|---|---|
| `test_public_experience_optional.py` | 公开包专用：验证私有经验库缺失时的冷启动行为；未安装此用例不等于运行时修复遗漏 |
| `test_figure_registry.py` | 安装副本与公开版分别包含退役生成器拒绝、现行 TikZ 来源正反例；需要结合各自的历史兼容政策判断 |
| `check_core_execution.py`、`delivery_gate.py`、`figure_registry.py` | 历史图表兼容规则仍有差异；当前 Harness 的现行图表要求不能由历史兼容入口替代 |
| `public_sync.py`、`skill_health_check.py` | 公开化路径适配不同，不能把公开版示例占位符直接覆盖到安装副本 |

在仓库技能目录和安装副本目录分别运行以下用例，可复核本次对齐的行为：

```text
python -m unittest discover -s tests -p "test_incremental_verification.py"
python -m unittest discover -s tests -p "test_harness_writer_preparation.py"
```

维护更新时，先比较受影响函数、模板与回归用例，再将缺失修复合入安装副本并在该副本运行相同的相关测试。公共 CI 通过只证明公开仓库对应提交；本机版本标识、较少的测试数量、换行符或 BOM 差异均不能单独证明安装副本是否完整。

## 2026-11-15 维护检查

公开版 CUMCM 排版适配器已在本机用 XeLaTeX 编译三个模板及布局冒烟样例，并用合成 SVG 验证 Inkscape 转换链路。设置环境变量 `CUMCM_RUN_LATEX_TESTS=1` 可启用额外的 XeLaTeX 路径兼容测试；CI 默认只检查源码契约。这些检查不代表真实论文或特定比赛规则已通过交付审核。

在 Windows、Python 3.13 环境下，公开仓库的 Harness 106 项、MathorCup 140 项测试通过；工作台 Python 28 项和 Node.js 33 项测试通过。仓库检查和合成数据示例通过。GitHub Actions 的实时结果以[工作流页面](https://github.com/cjh-solver/MathModeling-Skills-Arsenal/actions/workflows/validate.yml)为准。

公开包不包含私有的决策和写作经验库：相应检索器在文件缺失时返回空记录，不能把空库当成已获得经验。版本标识已统一，一次性维护脚本已隔离到历史归档。健康检查识别仓库的分类目录，这只证明包在仓库中，不证明宿主已安装或能调用它们。完整发布仍需独立的真实项目闭环和其他发布检查。

## 2026-11-01 历史记录

同步前的维护环境为 Windows、Python 3.13：MathorCup 140 项、Harness 106 项相关测试通过；严格 smoke 和机理、优化、预测三类 replay 通过。完整检查点运行 617 项，其中 616 项通过，一项原有一致性检查失败；其后新增两项返修链测试由最终 MathorCup 套件覆盖。

这些是当时的维护检查，不是本届比赛的重训、正式论文编译或提交验证。公开副本当时的复查结果记录在 [public-validation.json](public-validation.json)；其中日期与数量是历史快照，不自动代表最新运行结果。

## 已知发布阻碍

- 主控版本标识为 4.19 开发版；完整发布检查尚未完成，统一标识不代表稳定版发布。
- 私有经验库不随公开包发布；没有本地经验时采用冷启动，不能声称已检索到私有经验。
- 公开论文模板已对齐主控的章节契约；图表计划和模板测试使用现行 TikZ 路由，并支持从分类目录检查 starter。公开包不含 `math-modeling`、`latex-paper-en`、`mineru-parse` 和 `word-document`；适配器测试可通过 `MATH_SKILL_EXTERNAL_ROOT` 指定本机平铺技能目录来验证这些外部技能。未提供该目录时，缺失技能仍明确报错；本机通过不代表这些技能已包含在公开包中。
- 临时工程代理与用户可直接进入的长期角色会话不是同一能力。MathorCup 本次独立工程审查代理因工作区额度限制未完成最终审查；本地测试不冒充独立签署。

## 本地复现

```bash
python -m pip install pyyaml
python scripts/check_repository.py
python examples/chapter-parallel/calculate.py
cd skills/01-core/contest-orchestrator
# 可选：指向本机已有的外部技能目录，不修改或安装该目录。
export MATH_SKILL_EXTERNAL_ROOT="/path/to/installed/skills"
python -m unittest discover -s tests -p 'test_mathorcup*.py'
python -m unittest discover -s tests -p 'test_harness*.py'

# 完整检查：检查通过仍不等于正式竞赛闭环或稳定版发布。
python -m unittest discover -s tests -p 'test_*.py'
python scripts/skill_health_check.py . --strict --smoke
python scripts/replay_profiles.py --strict
```

科研绘图需要真实数据、语义与视觉 QA；LaTeX 交付还需要真实编译、字体、SVG 转换和引用检查。仅源码检查或测试夹具中的 PDF 不能被称作可提交论文。
