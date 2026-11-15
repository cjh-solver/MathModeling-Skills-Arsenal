/* Deterministic, evidence-based file ranking. Scores are not probabilities. */
const WorkbenchRanking = (() => {
  const categories = ['论文', '图表', '模型与结果', '数据与代码', '审查与交付', '其他'];
  const needsAttention = value => /pending|pause|block|fail|evidence_gap|stale/i.test(String(value || ''));
  function build(state, preferences = {}, contextNode = null) {
    const pins = new Set(preferences.pins || []);
    const views = preferences.views || {};
    const refs = new Map();
    const add = (path, patch) => {
      if (typeof path !== 'string' || !path) return;
      const item = refs.get(path) || { nodes: new Set(), artifacts: new Set(), categories: new Set(), urgent: [], main: [], inferredCategory: false };
      if (patch.node) item.nodes.add(patch.node);
      if (patch.node && patch.artifact) item.artifacts.add(patch.node);
      if (patch.category) item.categories.add(patch.category);
      if (patch.inferredCategory) item.inferredCategory = true;
      if (patch.urgent && !item.urgent.includes(patch.urgent)) item.urgent.push(patch.urgent);
      if (patch.main && !item.main.includes(patch.main)) item.main.push(patch.main);
      refs.set(path, item);
    };
    for (const node of state.nodes || []) {
      const nodeApprovals = (state.approvals || []).filter(a => a.gate === node.id);
      const approval = nodeApprovals[nodeApprovals.length - 1];
      const pending = needsAttention(node.status);
      const changed = approval?.digests?.status === 'issues';
      const urgent = pending ? `${node.id} 节点记录待处理` : changed ? `${node.id} 批准文件待核` : null;
      add(node.review, { node: node.id, artifact: true, category: '审查与交付', urgent });
      for (const item of node.evidence?.artifacts || []) add(item.path, { node: node.id, artifact: true, urgent: pending ? `${node.id} 节点记录待处理` : null });
      for (const item of [...(node.evidence?.inputs || []), ...(node.evidence?.required_outputs || []), ...(node.evidence?.related || [])]) add(item.path, { node: node.id });
      if (changed) for (const item of approval.digests.files || []) if (item.status !== 'matches') add(item.path, { node: node.id, urgent: `${node.id} 登记文件变化或待核` });
    }
    add(state.paper_pdf, { category: '论文', main: '项目登记的论文 PDF' });
    add(state.paper_source, { category: '论文', main: '项目登记的论文源文件' });
    for (const figure of state.figures || []) for (const path of [figure.png, figure.svg]) add(path, { category: '图表', main: '项目登记的图表' });
    for (const path of [state.question_sources?.models, state.question_sources?.results]) add(path, { category: '模型与结果', main: '项目登记的模型或结果材料' });
    for (const report of state.reports || []) add(report.path, { category: '审查与交付', inferredCategory: true, urgent: report.passed === false || report.error ? '历史报告记录未通过或待读取' : null });
    return (state.files || []).map(file => {
      const ref = refs.get(file.path) || { nodes: new Set(), artifacts: new Set(), categories: new Set(), urgent: [], main: [] };
      const inferred = new Set();
      const path = file.path.toLowerCase();
      if (/\.(png|jpe?g|svg)$/.test(path)) inferred.add('图表');
      if (/\.(py|ipynb|csv|xlsx?|zip)$/.test(path)) inferred.add('数据与代码');
      if (/\.(tex|bib)$/.test(path)) inferred.add('论文');
      const cats = ref.categories.size ? [...ref.categories] : inferred.size ? [...inferred] : ['其他'];
      const context = contextNode && ref.nodes.has(contextNode);
      const contextArtifact = contextNode && ref.artifacts.has(contextNode);
      const viewed = Number(views[file.path]) || 0;
      const tier = pins.has(file.path) ? 5 : ref.urgent.length ? 4 : context ? 3 : ref.main.length ? 2 : viewed ? 1 : 0;
      const reasons = pins.has(file.path) ? ['手动置顶'] : ref.urgent.length ? ref.urgent : contextArtifact ? [`${contextNode} 审查包或登记成果`] : context ? [`与 ${contextNode} 阶段有登记关联`] : ref.main.length ? ref.main : viewed ? ['最近查看'] : ['最近修改'];
      return { ...file, nodes: [...ref.nodes], categories: cats, categorySource: ref.categories.size ? ref.inferredCategory ? '按报告路径识别' : '项目登记' : inferred.size ? '按文件类型' : '未分类', tier, contextArtifact: !!contextArtifact, viewed, reasons };
    }).sort((a, b) => b.tier - a.tier || Number(b.contextArtifact) - Number(a.contextArtifact) || b.viewed - a.viewed || (b.modified || 0) - (a.modified || 0) || a.path.localeCompare(b.path));
  }
  function diverse(items) {
    const result = [];
    for (let tier = 5; tier >= 0; tier--) {
      const first = [], deferred = [], seen = new Set();
      for (const item of items.filter(value => value.tier === tier)) {
        const group = item.categories[0];
        if (tier >= 4 || !seen.has(group)) first.push(item);
        else deferred.push(item);
        seen.add(group);
      }
      result.push(...first, ...deferred);
    }
    return result;
  }
  return { build, diverse, categories, needsAttention };
})();
if (typeof module !== 'undefined') module.exports = WorkbenchRanking;

/* Explicit display translations; unknown project content stays unchanged. */
const QuestionLabels = (() => {
  const labels = {
    'satisfy hourly load and assess resource matching': '满足逐时负荷并评估资源匹配情况',
    'satisfy hourly load under budget and minimize surplus generation': '在预算约束下满足逐时负荷，最小化多余发电量',
    'satisfy hourly load with minimum generation and storage configuration': '满足逐时负荷，尽量减少发电与储能配置',
    'Q1 outputs baseline resource and capacity feasibility for Q2 and Q3': 'Q1 为 Q2、Q3 提供资源基线和容量可行性结果',
    'Q2 provides no-storage budget/dispatch baseline to Q3': 'Q2 为 Q3 提供无储能条件下的预算和调度基线',
    'final configuration and dispatch close the full resource-storage-load chain': '最终配置与调度衔接资源、储能和负荷',
    'hourly_load_kw': '逐时负荷（kW）',
    'hourly_wind_speed_mps': '逐时风速（m/s）',
    'hourly_irradiance_w_m2': '逐时辐照度（W/m²）',
    'wind_power_curve': '风电功率曲线',
    'pv_power_curve': '光伏功率曲线',
    'three_resource_curves': '三类资源曲线',
    'matching_relationship': '匹配关系',
    'wind_turbine_count': '风机数量',
    'pv_generator_count': '光伏发电设备数量',
    'Q1_resource_baseline': 'Q1 资源基线',
    'budget_cny': '预算（元）',
    'hourly_dispatch_strategy': '逐时调度策略',
    'hourly_surplus': '逐时多余发电量',
    'Q2_baseline': 'Q2 基线',
    'storage_unit_capacity_kwh': '单个储能单元容量（kWh）',
    'storage_unit_cost_cny': '单个储能单元成本（元）',
    'storage_unit_count': '储能单元数量',
    'hourly_charge_discharge_strategy': '逐时充放电策略',
    'hourly_state_of_charge': '逐时储能荷电状态',
  };
  const resultLabels = { wind_units: '风机数量', pv_units: '光伏设备数量', total_units: '设备总数', storage_units: '储能单元数量', cost_cny: '成本（元）', curtailment_kwh: '弃电量（kWh）' };
  const text = value => typeof value === 'string' ? (labels[value] || value) : value;
  const model = value => typeof value === 'string' && /^Q\d+-final-model$/i.test(value) ? `${value.split('-')[0]} 最终模型` : value;
  function result(value) {
    if (typeof value !== 'string') return value;
    return value.replace(/(^|;\s*)([A-Za-z_][A-Za-z0-9_]*)(?=\s*=)/g, (match, prefix, key) => prefix + (resultLabels[key] || key));
  }
  return { text, model, result };
})();
if (typeof module !== 'undefined') module.exports.QuestionLabels = QuestionLabels;
