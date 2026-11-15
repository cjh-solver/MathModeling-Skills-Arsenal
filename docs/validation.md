# 验证结果与适用边界

## 检查的含义

本仓库的测试检查流程契约和工具行为，例如未批准就派发下一章、遗漏冻结输入、修改已批准正文、使用旧图件版本时应被拒绝。这些检查不能证明模型精度、获奖概率、长篇论文质量或某一宿主的真实多角色调用已发生。

`examples/chapter-parallel` 使用可复算的合成线性数据，其误差为零源于数据构造方式。示例中的正文、交接提示词不构成真实比赛记录或自动生成质量评测。

## 2026-11-15 维护检查

公开版 CUMCM 排版适配器已在本机用 XeLaTeX 编译三个模板及布局冒烟样例，并用合成 SVG 验证 Inkscape 转换链路。设置环境变量 `CUMCM_RUN_LATEX_TESTS=1` 可启用额外的 XeLaTeX 路径兼容测试；CI 默认只检查源码契约。这些检查不代表真实论文或特定比赛规则已通过交付审核。

在 Windows、Python 3.13 环境下，公开仓库的 Harness 106 项、MathorCup 140 项测试通过；工作台 Python 28 项和 Node.js 33 项测试通过。仓库检查和合成数据示例通过。GitHub Actions 的实时结果以[工作流页面](https://github.com/cjh-solver/MathModeling-Skills-Arsenal/actions/workflows/validate.yml)为准。

公开包不包含私有的决策和写作经验库：相应检索器在文件缺失时返回空记录，不能把空库当成已获得经验。版本标识已统一，一次性维护脚本已隔离到历史归档。健康检查识别仓库的分类目录，这只证明包在仓库中，不证明宿主已安装或能调用它们。完整发布仍需独立的真实项目闭环和其他发布检查。

## 2026-11-01 历史记录

同步前的维护环境为 Windows、Python 3.13：MathorCup 140 项、Harness 106 项相关测试通过；严格 smoke 和机理、优化、预测三类 replay 通过。完整检查点运行 617 项，其中 616 项通过，一项原有一致性检查失败；其后新增两项返修链测试由最终 MathorCup 套件覆盖。

这些是当时的维护检查，不是本届比赛的重训、正式论文编译或提交验证。公开副本当时的复查结果记录在 [public-validation.json](public-validation.json)；其中日期与数量是历史快照，不自动代表最新运行结果。

## 已知发布阻碍

- 主控包含未发布的开发改动，版本标识为 4.18；统一标识不代表已完成新版本发布。
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
