# H6 验证协议

H6 在范围卡通过后读取本协议。验证只覆盖任务卡登记的范围，不重读 H5 全部推导和代码；L3 全局回流或用户明确要求时例外。

## 不改写 H5 的核验记录

新任务保持 H5 输入文件、H6 任务卡和既有批准原样。H6 在已有 `global_interface_check.yaml` 中登记 `verified_artifacts`，将独立核验结论绑定到原文件的路径与当前 SHA-256，不向已冻结文件回写签名：

```yaml
verified_artifacts:
  validation_contract: {path: validation_contract.yaml, sha256: <冻结输入哈希>}
  model_summary_cards: {path: model_summary_cards.yaml, sha256: <冻结输入哈希>}
  result_interpretation_cards: {path: result_interpretation_cards.yaml, sha256: <冻结输入哈希>}
  visual_evidence_packet: {path: visual_evidence_packet.yaml, sha256: <冻结输入哈希>}
```

四项均须与 H5 登记和 H6 任务卡的冻结输入一致。报告必须通过原有接口、逐问覆盖、当前独立 H6 实例、任务卡哈希与来源检查，之后检查器才在读取时提供已核验视图；文件原文保持原状态。图表、写作及交付继续检查完整科学内容与证据，`stale`、`evidence_gap` 或 `rejected` 的源文件不能据此放行。报告及其覆盖文件仍进入原有 H6 人工审查，核验记录不等于用户批准。

缺少任一绑定时补齐报告；来源、哈希、实例或任务不一致时阻断。不得刷新原任务输入哈希、修改旧审查包或补造历史批准来消除不一致。尚无独立绑定的历史项目继续读取原有 `status: verified` 和 H6 签名，不自动改写或迁移。

H7/H8 新任务同时冻结原材料和本核验记录作为输入。Harness 图表计划检查与独立的 `check_visual_evidence.py --stage solution/paper` 使用同一来源绑定规则；独立命令只检查视觉契约，不能替代完整 Harness 门禁或人工批准。

## 必查项

1. 按 `validation_contract.yaml` 核对关键结论与深度抽查锚点。
2. 核对跨问共享变量、单位、数据版本、字段、时间尺度、参数、约束、结论和来源。`global_interface_check.yaml` 的每个结构化 `interface_fields` 条目必须同时登记 `comparison_status`、项目相对 `source_path` 和与当前文件一致的 `source_sha256`；缺字段保持 `PAUSE`，来源不存在或哈希不一致为 `BLOCK`。
3. 核对 `paper_narrative.yaml` 的 `key_result` 与冻结结果一致。
4. 核对 `model_summary_cards.yaml`：每个小问均有唯一最终求解模型、决策变量及单位、参数/输入、边界或约束、求解接口和来源公式；逐项与推导、代码、结果和适用范围对齐。通过后将原文件的路径和哈希登记到独立核验记录。
5. 核对 `result_interpretation_cards.yaml`：事实、意义、解释依据和适用范围均有冻结证据；通过后登记独立核验绑定，不改写 H5 内容或签名字段。
6. 运行任务卡指定的专项检查：方法选择证据、代码注释质量和数值合理性。不得以 H5 自检替代。
7. 核验 `paper_material_readiness.yaml`，确认其证据引用、容量和 H6 签名一致。

## 输出与回流

- 通过：输出独立验证报告、含四项 `verified_artifacts` 绑定的 `global_interface_check.yaml` 和冻结清单；下游读取原材料及其核验记录。
- 不通过：逐项记录小问、字段、期望与实际证据、影响范围和建议回流节点；不修改上游材料。
- `targeted_recheck`：只报告变更材料及其受影响的下游证据；未受影响的冻结产物保持有效。

## 禁止事项

不得补写推导、重算模型、调整结果、代写论文或把验证过程写入论文和交付材料。
