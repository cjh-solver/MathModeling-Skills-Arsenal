const pages = [
  ['overview', 'home', '比赛总览', '让比赛进度、角色和成果一目了然。'],
  ['flow', 'flow', '比赛流程', '展示项目控制记录中的节点与审批记录。'],
  ['roles', 'users', '角色会话', '登记可由你直接访问的 Codex 会话。'],
  ['questions', 'checklist', '小问管理', '查看项目已登记的小问与相关资料。'],
  ['literature', 'book', '资料与文献', '查看项目文件与已提供的文献资料。'],
  ['artifacts', 'chart', '图表与成果', '浏览图表、结果、代码与项目文件。'],
  ['paper', 'file', '论文工作区', '查看已有论文文件、图表和章节材料。'],
  ['skills', 'spark', 'Skills 与规则', '查看 Harness 运行记录中的流程信息。'],
  ['delivery', 'shield', '交付检查', '查看已有交付材料和 H9 节点记录。'],
];
const iconPaths = {
  home: '<path d="M3 10.5 12 3l9 7.5M5.5 9.5V21h13V9.5M9.5 21v-7h5v7"/>',
  flow: '<rect x="9" y="2.5" width="6" height="5" rx="1.3"/><rect x="2" y="16.5" width="6" height="5" rx="1.3"/><rect x="16" y="16.5" width="6" height="5" rx="1.3"/><path d="M12 7.5v4m-7 5v-3a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v3"/>',
  users: '<circle cx="9" cy="8" r="3.25"/><path d="M2.5 20v-1.5a6.5 6.5 0 0 1 13 0V20M16 5.2a3.1 3.1 0 0 1 0 5.8M17 14a5 5 0 0 1 4.5 5v1"/>',
  checklist: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="m8 12 2.5 2.5L16.5 8"/>',
  book: '<path d="M12 6c-2-2-5-2.4-9-1v14c4-1.4 7-1 9 1m0-14c2-2 5-2.4 9-1v14c-4-1.4-7-1-9 1m0-14v14"/>',
  chart: '<path d="M3 21h18M5 18v-5h3v5M10.5 18V8h3v10M16 18V4h3v14"/>',
  file: '<path d="M6 3h8l4 4v14H6zM14 3v5h4M9 12h6M9 16h6"/>',
  spark: '<path d="m12 3 1.8 5.6L19.5 10l-5.7 1.7L12 17.5l-1.8-5.8L4.5 10l5.7-1.4L12 3ZM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z"/>',
  shield: '<path d="M12 2.5 20 6v5.5c0 4.8-3.2 7.7-8 10-4.8-2.3-8-5.2-8-10V6l8-3.5Z"/><path d="m8.5 12 2.2 2.2 4.8-5"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>',
  alert: '<circle cx="12" cy="12" r="9"/><path d="M12 7v6m0 3h.01"/>',
  crown: '<path d="m3 7 4.5 4L12 4l4.5 7L21 7l-2 11H5L3 7Zm2 14h14"/>',
  trophy: '<path d="M7 3h10v4c0 5-2 7-5 7S7 12 7 7V3Zm0 2H3v2c0 3 2 5 5 5m9-7h4v2c0 3-2 5-5 5M12 14v4m-4 3h8m-6-3h4"/>',
  flag: '<path d="M5 21V4m0 1c5-3 8 3 14 0v10c-6 3-9-3-14 0"/>',
  calculate: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8M8 11h1m3 0h1m3 0h.1M8 15h1m3 0h1m3 0h.1M8 18h1m3 0h4"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/>',
  pencil: '<path d="M4 20h4l11-11-4-4L4 16v4Zm9-13 4 4M12 20h8"/>',
  solve: '<circle cx="12" cy="12" r="3"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4m0-14.2-1.4 1.4M6.3 17.7l-1.4 1.4"/><circle cx="12" cy="12" r="7"/>',
};
const icon = (name) => `<svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${iconPaths[name] || iconPaths.file}</svg>`;
const sectionIcons = { '需要关注': 'alert', '小问进度': 'layers', '角色会话': 'users', '论文与图表': 'file', '最近成果': 'layers', '成果中心': 'layers' };
const statusNames = { approved: '记录为已批准', completed: '记录为已完成', frozen: '记录为已冻结', review_pending: '待审查', evidence_gap: '证据缺口', stale: '记录已过期', not_started: '未开始', pending: '待处理', paused: '已暂停', pause: '已暂停', blocked: '已阻塞', failed: '失败', draft: '草稿', unknown: '未知', merged: '已合并' };
let state = null;
let current = 'overview';
let resultTab = 'recommended';
let resultCategory = '全部';
let resultExpanded = false;
let contextNode = null;
let selectedQuestion = null;
let selectedRole = null;
let selectedLibraryFile = null;
let selectedArtifact = null;
let selectedSkill = null;
let selectedDeliveryFile = null;
let artifactStage = '全部';
let libraryDirectory = '全部';
let catalogQuery = '';
let questionQuery = '';
let syncSnapshot = '';
let syncCandidate = '';
let syncGeneration = 0;
let syncBusy = false;
let switchGeneration = 0;
let selectedProjectInMemory = null;
function selectedProjectPath() {
  if (selectedProjectInMemory !== null) return selectedProjectInMemory;
  try { return sessionStorage.getItem('harness-workbench-project'); }
  catch { return null; }
}
const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const display = (value) => value === null || value === undefined || value === '' ? '未登记' : typeof value === 'object' ? JSON.stringify(value) : String(value);
const status = (value) => statusNames[String(value).toLowerCase()] || String(value || '未知');
const pillClass = (value) => ['approved', 'completed'].includes(String(value).toLowerCase()) ? '' : WorkbenchRanking.needsAttention(value) ? 'amber' : 'muted';
const badge = (value) => `<span class="pill ${pillClass(value)}">${esc(status(value))}</span>`;
const head = (title, detail = '') => `<div class="section-head"><h2>${sectionIcons[title] ? icon(sectionIcons[title]) : ''}${esc(title)}</h2>${detail ? `<small>${esc(detail)}</small>` : ''}</div>`;
const empty = (text) => `<div class="empty">${esc(text)}</div>`;
const fileLink = (path, label = '查看') => `<button class="row-action" data-file="${esc(path)}">${esc(label)} ↗</button>`;

function fileDisplayName(path) {
  const name = String(path || '').split(/[\\/]/).pop();
  const names = {
    'paper.pdf': '论文.pdf', 'paper.tex': '论文源文件.tex', 'appendices.tex': '论文附录.tex',
    'references.bib': '参考文献.bib', 'problem_statement.md': '题目说明.md',
    'problem_profile.yaml': '题目信息.yaml', 'model_summary_cards.yaml': '模型总结.yaml',
    'result_interpretation_cards.yaml': '结果解释.yaml', 'figure_registry.yaml': '图表清单.yaml',
    'compile_report.json': '论文编译报告.json', 'delivery_gate_report.json': '交付检查报告.json',
    'minimum_validation_report.yaml': '基础验证报告.yaml', 'literature_request.yaml': '文献需求.yaml',
    'literature_sources.yaml': '文献来源.yaml', 'paper_narrative.yaml': '论文结构.yaml',
    'paper_argument_blueprint.yaml': '论文论证蓝图.yaml', 'paper_author_brief.yaml': '论文写作简报.yaml',
    'paper_material_readiness.yaml': '论文材料准备情况.yaml', 'chapter_writing_card.yaml': '章节写作卡.yaml',
    'paper_continuity_context.yaml': '论文衔接信息.yaml', 'paper_claim_coverage.yaml': '论文主张覆盖.yaml',
  };
  const review = name.match(/^(H[0-9])_review_packet\.yaml$/i);
  return names[name.toLowerCase()] || (review ? `${review[1].toUpperCase()} 审查包.yaml` : name);
}

function fileIcon(path) {
  const name = String(path || '').split(/[\\/]/).pop();
  const match = name.match(/\.([a-z0-9]{1,8})$/i);
  const ext = match ? match[1].toLowerCase() : '';
  const kinds = {
    pdf: ['PDF', 'pdf'], yaml: ['YAML', 'config'], yml: ['YML', 'config'], json: ['JSON', 'config'],
    png: ['PNG', 'image'], jpg: ['JPG', 'image'], jpeg: ['JPEG', 'image'], svg: ['SVG', 'vector'],
    gif: ['GIF', 'image'], webp: ['WEBP', 'image'], doc: ['DOC', 'document'], docx: ['DOCX', 'document'],
    xls: ['XLS', 'sheet'], xlsx: ['XLSX', 'sheet'], csv: ['CSV', 'sheet'], tsv: ['TSV', 'sheet'],
    md: ['MD', 'text'], txt: ['TXT', 'text'], tex: ['TEX', 'text'], py: ['PY', 'code'],
    ipynb: ['IPYNB', 'code'], js: ['JS', 'code'], html: ['HTML', 'code'], css: ['CSS', 'code'],
  };
  const [label, kind] = kinds[ext] || ['', 'generic'];
  return `<span class="file-icon file-icon--${kind}" aria-hidden="true"><svg viewBox="0 0 40 46" fill="none"><path d="M12 3h15l9 9v27a4 4 0 0 1-4 4H12a4 4 0 0 1-4-4V7a4 4 0 0 1 4-4Z" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"/><path d="M27 3v5a4 4 0 0 0 4 4h5" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"/></svg>${label ? `<span class="file-icon-label">${label}</span>` : ''}</span>`;
}

function nav() {
  $('#nav').innerHTML = pages.map(([id, iconName, label]) => `<button class="nav-item ${current === id ? 'active' : ''}" data-page="${id}" ${current === id ? 'aria-current="page"' : ''}><span class="nav-icon">${icon(iconName)}</span>${label}</button>`).join('');
}

function closeMobileNav() {
  $('.sidebar').classList.remove('mobile-open');
  $('#nav-toggle').setAttribute('aria-expanded', 'false');
  $('#nav-toggle').setAttribute('aria-label', '展开导航');
}
$('#nav-toggle').addEventListener('click', () => {
  const open = $('.sidebar').classList.toggle('mobile-open');
  $('#nav-toggle').setAttribute('aria-expanded', String(open));
  $('#nav-toggle').setAttribute('aria-label', open ? '收起导航' : '展开导航');
});

document.addEventListener('pointermove', (event) => {
  if (event.pointerType !== 'mouse' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const button = event.target.closest('.nav-item, .role-select');
  if (!button) return;
  const bounds = button.getBoundingClientRect();
  button.style.setProperty('--pointer-x', `${event.clientX - bounds.left}px`);
  button.style.setProperty('--pointer-y', `${event.clientY - bounds.top}px`);
});

function rows(files, limit = 8) {
  if (!files.length) return empty('项目中暂未找到可预览的相关文件。');
  return files.slice(0, limit).map((file) => `<div class="row">${fileIcon(file.path)}<div class="row-main"><div class="row-title">${esc(fileDisplayName(file.path))}</div><div class="row-meta">${esc(file.path)}</div></div>${file.previewable !== false ? fileLink(file.path) : '<span class="row-meta">暂不支持预览</span>'}</div>`).join('');
}

function roles(list = state.roles, compact = false) {
  return list.map((role) => {
    const source = role.link_source === 'project_registry' ? '项目登记' : role.link_source === 'verified_codex_thread_lookup' ? 'Codex 查询确认' : '手动登记';
    const conflict = role.registry_thread_id && role.thread_id && role.registry_thread_id !== role.thread_id;
    const access = role.registry_accessible === false ? '项目记录为不可访问' : '可访问性待核';
    const dispatches = role.dispatches || [];
    const roleIcons = { '主控': 'crown', '题意理解': 'book', '解题': 'solve', '独立验证': 'shield', '图表': 'chart', '论文': 'file' };
    const label = conflict ? '会话登记不一致' : role.thread_id ? access : '会话未登记';
    return `<div class="role-entry"><div class="role-line"><span class="role-icon">${icon(roleIcons[role.name] || 'users')}</span><div class="role-label"><div class="row-title">${esc(role.name)}</div>${!compact || label !== '可访问性待核' ? `<div class="role-status">${esc(label)}</div>` : ''}</div>${role.thread_id ? `<a class="role-open" href="codex://threads/${esc(role.thread_id)}" aria-label="尝试打开${esc(role.name)}会话">打开会话 <span aria-hidden="true">›</span></a>` : `<button class="role-open" data-role="${esc(role.name)}">登记会话 <span aria-hidden="true">›</span></button>`}</div><details class="role-details"><summary>会话信息</summary><div class="role-detail-content"><div>${role.instance_id ? `角色实例：${esc(role.instance_id)}` : '角色实例未登记'}<br>${role.thread_id ? `当前会话：${esc(role.thread_id)} · ${source}` : '当前会话未登记'}${role.registry_status ? `<br>项目登记状态：${esc(role.registry_status)}` : ''}${conflict ? `<br>项目登记会话：${esc(role.registry_thread_id)}（与当前登记不同）` : ''}</div>${role.history?.length > 1 ? `<details class="history"><summary>查看登记历史</summary>${role.history.map(h => `<div>${esc(h.thread_id)} · ${esc(h.registered_at || '时间未记录')}</div>`).join('')}</details>` : ''}${dispatches.length ? `<details class="history"><summary>查看 ${dispatches.length} 次派发记录</summary>${dispatches.map(d => `<div>${esc(d.node || '节点未知')} · ${esc(d.task_id || '任务未知')} · ${esc(d.model || '模型未记录')} / ${esc(d.reasoning_effort || '强度未记录')} ${d.task_card_path ? fileLink(d.task_card_path, '任务卡') : ''}</div>`).join('')}</details>` : ''}${role.thread_id ? `<button class="row-action" data-role="${esc(role.name)}">更新登记</button>` : ''}</div></details></div>`;
  }).join('') || empty('暂无已登记角色。');
}

function rolePage() {
  const list = state.roles || [];
  const chosen = list.find(role => role.name === selectedRole) || list[0];
  if (chosen) selectedRole = chosen.name;
  const roleIcons = { '主控': 'crown', '题意理解': 'book', '解题': 'solve', '独立验证': 'shield', '图表': 'chart', '论文': 'file' };
  const descriptions = { '主控': '统筹任务、进度与角色协作。', '题意理解': '梳理题目、约束和问题结构。', '解题': '建立模型并进行求解分析。', '独立验证': '独立核查模型、结果和结论。', '图表': '整理和展示项目图表。', '论文': '撰写、整理论文材料。' };
  const description = role => descriptions[role.name] || '项目中登记的角色。';
  const iconName = role => roleIcons[role.name] || 'users';
  const conflict = role => role.registry_thread_id && role.thread_id && role.registry_thread_id !== role.thread_id;
  const roleStatus = role => conflict(role) ? '会话登记不一致' : !role.thread_id ? '会话未登记' : role.registry_accessible === false ? '项目记录为不可访问' : '可访问性待核';
  const sourceName = role => role.link_source === 'project_registry' ? '项目角色登记' : role.link_source === 'verified_codex_thread_lookup' ? 'Codex 查询登记' : role.thread_id ? '工作台手动登记' : '未登记';
  const action = role => role.thread_id ? `<a class="role-open" href="codex://threads/${esc(role.thread_id)}" aria-label="尝试打开${esc(role.name)}会话">打开会话 ›</a>` : `<button class="role-open" data-role="${esc(role.name)}">登记会话 ›</button>`;
  const rows = list.map(role => `<div class="role-table-row${chosen?.name === role.name ? ' selected' : ''}"><button class="role-select" data-select-role="${esc(role.name)}" aria-pressed="${chosen?.name === role.name}"><span class="role-table-icon">${icon(iconName(role))}</span><strong>${esc(role.name)}</strong></button><span class="role-description">${esc(description(role))}</span><span class="role-state">${esc(roleStatus(role))}</span><div class="role-table-action">${action(role)}</div></div>`).join('');
  const selectedNode = chosen && state.nodes.find(node => node.id === chosen.node);
  const history = chosen?.history || [];
  const dispatches = chosen?.dispatches || [];
  const details = chosen ? `<aside class="card role-detail-panel"><div class="role-detail-header"><span class="role-detail-icon">${icon(iconName(chosen))}</span><div><h2>${esc(chosen.name)}</h2><p>${esc(description(chosen))}</p></div></div><section class="role-detail-section"><h3>${icon('layers')}对应阶段</h3><p>${selectedNode ? `${esc(selectedNode.id)} · ${esc(selectedNode.name)}` : '未记录对应阶段'}</p></section><section class="role-detail-section"><h3>${icon('users')}当前会话</h3>${chosen.thread_id ? `<div class="role-session-card"><strong>${esc(roleStatus(chosen))}</strong><p>会话 ID：${esc(chosen.thread_id)}</p>${action(chosen)}<button class="row-action" data-role="${esc(chosen.name)}">更新登记</button></div>` : `<div class="role-session-card"><p>会话未登记</p>${action(chosen)}</div>`}</section><section class="role-detail-section"><h3>${icon('file')}记录来源</h3><p>${esc(sourceName(chosen))}</p>${chosen.instance_id ? `<p>角色实例：${esc(chosen.instance_id)}</p>` : ''}${chosen.registry_status ? `<p>项目登记状态：${esc(chosen.registry_status)}</p>` : ''}${conflict(chosen) ? `<p>项目登记会话：${esc(chosen.registry_thread_id)}（与当前登记不一致）</p>` : ''}</section><details class="role-history"><summary>派发历史（${dispatches.length} 条）</summary>${dispatches.length ? dispatches.map(d => `<div class="role-history-item"><p>${esc(d.node || '节点未知')} · ${esc(d.task_id || '任务未知')}</p><p>${esc(d.model || '模型未记录')} / ${esc(d.reasoning_effort || '强度未记录')}</p>${d.task_card_path ? fileLink(d.task_card_path, '任务卡') : ''}</div>`).join('') : '<p>暂无派发记录。</p>'}</details>${history.length ? `<details class="role-history"><summary>会话登记历史（${history.length} 条）</summary>${history.map(item => `<div class="role-history-item"><p>${esc(item.thread_id)}</p><p>${esc(item.registered_at || '时间未记录')}</p></div>`).join('')}</details>` : ''}</aside>` : '';
  return `<div class="role-workspace"><div class="role-notice">${icon('alert')}<span>会话登记不代表可访问；角色实例 ID 与 Codex 会话 ID 分别记录。</span></div><div class="role-layout"><section class="card role-list-panel"><div class="role-list-heading"><h2>角色会话</h2><button class="button primary" id="add-role">＋ 登记角色</button></div><div class="role-table-head"><span>角色</span><span>常见职责</span><span>状态</span><span>会话入口</span></div>${rows || empty('暂无角色登记。')}</section>${details}</div></div>`;
}

function tracker() {
  const selected = current === 'flow' ? (state.nodes.find(n => n.id === contextNode) || state.nodes.find(n => WorkbenchRanking.needsAttention(n.status)) || state.nodes[0])?.id : null;
  const attention = current === 'overview' ? state.nodes.find(n => WorkbenchRanking.needsAttention(n.status))?.id : null;
  const stageIcons = { H0: 'flag', H1: 'file', H2: 'flow', H3: 'solve', H4: 'book', H5: 'calculate', H6: 'search', H7: 'chart', H8: 'pencil', H9: 'layers' };
  return `<div class="tracker">${state.nodes.map((node) => { const issue = gateNeedsReview(node); const highlighted = node.id === attention; return `<div class="track-item"><button type="button" class="track-button${highlighted ? ' track-attention' : ''}" data-node="${esc(node.id)}" ${current === 'flow' ? `aria-pressed="${node.id === selected}"` : ''} aria-label="查看 ${esc(node.id)} ${esc(node.name)} 阶段详情" title="${esc(status(node.status))}${issue ? '；批准记录或文件待核' : ''}"><span class="stage-icon">${icon(stageIcons[node.id] || 'file')}</span><span class="track-text"><span class="track-code">${esc(node.id)}</span><span class="track-name">${esc(node.name)}${issue ? ' · 待核' : ''}</span></span>${highlighted ? `<span class="track-status">${esc(status(node.status))}</span><span class="track-detail" aria-hidden="true">查看阶段详情 ›</span>` : `<span class="track-dot ${issue ? 'review_pending' : esc(node.status)}" aria-hidden="true"></span>`}</button></div>`; }).join('')}</div>`;
}

function evidenceRows(items, fallback) {
  if (!items?.length) return empty(fallback);
  return items.map(item => `<div class="evidence-row">${fileIcon(item.path)}<div class="evidence-info"><div class="row-title">${esc(fileDisplayName(item.path))}</div><div class="row-meta">${esc(item.path)}<br>${item.field ? `控制记录字段：${esc(item.field)} · ` : ''}${item.present ? '文件存在（内容未核验）' : '文件缺失或无法访问'}</div></div>${item.previewable ? fileLink(item.path, '查看') : ''}</div>`).join('');
}

function nodeContent(node) {
  const evidence = node.evidence || {};
  const approvals = state.approvals.filter(item => item.gate === node.id);
  return `<div class="node-overview"><div>${badge(node.status)}${gateNeedsReview(node) ? '<span class="pill amber">批准或文件待核</span>' : ''}</div><p>负责人：${esc(display(node.owner))} · 阶段更新时间：未登记</p><p>${esc(evidence.objective || '阶段目标未在任务卡中登记。')}</p></div>
    <div class="node-grid"><section class="node-section"><h3>${icon('book')} 阶段输入</h3><p class="subdued">来源：${esc(evidence.task_path || '任务卡未登记')}${evidence.task_error ? `（${esc(evidence.task_error)}）` : ''}</p>${evidenceRows(evidence.inputs, '任务卡中未登记输入。')}</section>
    <section class="node-section"><h3>${icon('checklist')} 任务要求输出</h3><p class="subdued">来源：${esc(evidence.task_path || '任务卡未登记')}；文件存在不代表已验收。</p>${evidenceRows(evidence.required_outputs, '任务卡中未登记要求输出。')}</section>
    <section class="node-section"><h3>${icon('layers')} 审查包登记成果</h3><p class="subdued">来源：${esc(evidence.review_path || '未登记')}${evidence.review_error ? `（${esc(evidence.review_error)}）` : ''}</p>${evidenceRows(evidence.artifacts, '审查包中未登记成果。')}</section>
    <section class="node-section"><h3>${icon('shield')} 审查与批准</h3><p class="subdued">审查摘要：${esc(evidence.review_summary || '未登记')}<br>审查包建议：${esc(evidence.requested_decision || '未登记')} · 建议后续节点：${esc(evidence.next_node || '未登记')}</p>${approvals.length ? approvals.map(approvalRow).join('') : empty('未找到该阶段的批准记录。')}<p class="hint">批准记录来自项目文件；哈希一致不能证明批准真实性或代替 Harness 门禁。</p>${node.review ? fileLink(node.review, '查看审查包') : ''}</section></div>
    <section class="node-section node-related"><h3>${icon('file')} 其他关联文件</h3><p class="subdued">来源：控制记录；这里不推断输入或输出归属。</p>${evidenceRows(evidence.related, '控制记录未登记关联文件。')}</section>
    <p class="path">来源：${esc(state.source)}；输入与成果来源分别见上述任务卡和审查包。</p>`;
}

function openNode(id) {
  const node = state.nodes.find(item => item.id === id);
  if (!node) return;
  contextNode = id;
  if (current === 'flow') {
    const currentContent = document.querySelector('.flow-columns');
    const updated = document.createElement('template');
    updated.innerHTML = flow();
    const nextContent = updated.content.querySelector('.flow-columns');
    if (currentContent && nextContent) currentContent.replaceWith(nextContent);
    document.querySelectorAll('.tracker [data-node]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.node === id)));
    return;
  }
  $('#node-title').textContent = `${node.id} · ${node.name}`;
  $('#node-body').innerHTML = nodeContent(node);
  $('#node-dialog').showModal();
}

function gateNeedsReview(node) {
  const approval = [...state.approvals].reverse().find(item => item.gate === node.id);
  if (approval?.digests?.status === 'issues') return true;
  return node.status === 'approved' && /^H[2-9]$/.test(node.id) && (!approval || approval.decision !== 'approved' || approval.digests?.status !== 'matches');
}

function projectCard() {
  const authorization = state.authorization_mode === 'autonomous_replay_authorized_by_user' ? '用户授权的自动回放；此授权只属于该项目，不代表正式比赛批准。' : state.authorization_mode ? `批准记录的授权模式：${state.authorization_mode}；该设置只属于此项目。` : '';
  const replayBadge = state.authorization_mode === 'autonomous_replay_authorized_by_user' ? '<span class="pill amber">授权回放</span>' : '';
  return `<section class="card project-card"><div class="project-top"><div class="project-heading"><span class="project-icon">${icon(current === 'overview' ? 'trophy' : 'layers')}</span><div class="project-identity"><div class="project-title-line"><h2>${esc(state.name)}</h2><div class="project-badges"><span class="pill">Harness 模式</span>${replayBadge}</div></div></div></div></div>${tracker()}<details class="project-source"><summary>项目来源与状态说明</summary><p>运行标识：${esc(state.run_id || '未记录')} · 流程：${esc(state.visual_workflow)}</p>${authorization ? `<p>${esc(authorization)}</p>` : ''}<p>节点状态来自项目文件，不代表实时运行状态，也不等同于批准或交付通过；文件哈希对比不证明批准真实性。</p><p>已登记会话的可访问性尚未自动验证；登记不代表角色在线。</p><button class="row-action" data-page="roles">查看角色登记详情 ›</button><p class="path">${esc(state.source)}</p></details></section>`;
}

function paperFigureSummary() {
  const available = new Set(state.files.map(file => file.path));
  const pdf = state.paper_pdf;
  const figures = (state.figures || []).filter(f => f.png && available.has(f.png)).slice(0, 2);
  const query = pdf ? `path=${encodeURIComponent(pdf)}&project=${encodeURIComponent(state.project)}&page=1` : '';
  const paper = pdf && state.capabilities?.pdf_preview ? `<button class="paper-thumb" data-file="${esc(pdf)}"><img loading="lazy" src="/api/pdf-page?${query}" alt="论文第一页预览"></button>` : '<div class="paper-thumb placeholder">暂无 PDF 预览</div>';
  const charts = figures.map(f => `<button class="summary-chart" data-file="${esc(f.png)}"><img loading="lazy" src="${fileUrl(f.png)}" alt="${esc(f.id)}"><span>${esc(f.id)}</span></button>`).join('');
  return `<section class="card">${head('论文与图表')}<div class="summary-content">${paper}<div class="summary-copy"><div class="row-title">${esc(pdf || '论文 PDF 未登记')}</div><div class="row-meta">源文件和 PDF 的一致性需核验</div><button class="row-action" data-page="paper">进入论文工作区 ↗</button></div><div class="summary-charts">${charts || '<span class="row-meta">暂无登记图表</span>'}</div></div></section>`;
}

function preferenceKey() { return `harness-results:${state.project}`; }
function resultPreferences() {
  try {
    const value = JSON.parse(localStorage.getItem(preferenceKey()) || '{}');
    return { pins: Array.isArray(value.pins) ? value.pins.filter(p => typeof p === 'string') : [], views: value.views && typeof value.views === 'object' && !Array.isArray(value.views) ? value.views : {} };
  } catch { return { pins: [], views: {} }; }
}
function saveResultPreferences(value) {
  try { localStorage.setItem(preferenceKey(), JSON.stringify(value)); return true; }
  catch { alert('浏览器无法保存本地偏好，请检查浏览器存储设置。'); return false; }
}
function resultPanel() {
  const prefs = resultPreferences();
  const ranked = WorkbenchRanking.build(state, prefs, contextNode);
  const newest = [...ranked].sort((a, b) => (b.modified || 0) - (a.modified || 0) || a.path.localeCompare(b.path));
  let list = resultTab === 'recommended' ? WorkbenchRanking.diverse(ranked) : newest;
  if (resultTab === 'categories' && resultCategory !== '全部') list = list.filter(item => item.categories.includes(resultCategory));
  if (resultTab === 'recommended') {
    const groups = new Map();
    list = list.filter(item => {
      if (item.tier !== 4) return true;
      const group = item.reasons.join(' ').match(/H\d+/)?.[0] || '历史报告';
      if (groups.has(group)) { groups.get(group).members.push(item); return false; }
      item.members = []; groups.set(group, item); return true;
    });
  }
  const mustShow = resultTab === 'recommended' ? list.filter(item => item.tier >= 4).length : 0;
  const visible = resultExpanded ? list : list.slice(0, Math.max(4, mustShow + (mustShow && list.length > mustShow ? 1 : 0)));
  const tabs = [['recommended', '推荐查看'], ['recent', '最近更新'], ['categories', '分类浏览']];
  const controls = `<div class="result-tabs" role="group" aria-label="成果视图">${tabs.map(([id, label]) => `<button class="result-tab ${resultTab === id ? 'active' : ''}" data-result-tab="${id}" aria-pressed="${resultTab === id}">${label}</button>`).join('')}</div>`;
  const actions = `<div class="result-toolbar-actions">${list.length > visible.length ? '<button class="result-tool" data-result-expand>查看全部</button>' : resultExpanded && list.length > 4 ? '<button class="result-tool" data-result-collapse>收起</button>' : ''}<button class="result-tool" data-result-clear-views ${Object.keys(prefs.views).length ? '' : 'disabled title="暂无最近查看记录"'}>清除最近查看</button><button class="result-tool" data-result-clear-pins ${prefs.pins.length ? '' : 'disabled title="暂无置顶成果"'}>清除置顶</button></div>`;
  const categoryFilter = resultTab === 'categories' ? `<label class="result-filter">选择分类 <select id="result-category">${['全部', ...WorkbenchRanking.categories].map(c => `<option${c === resultCategory ? ' selected' : ''}>${esc(c)}</option>`).join('')}</select></label>` : '';
  const row = item => {
    const pinned = prefs.pins.includes(item.path);
    const date = item.modified ? new Date(item.modified * 1000).toLocaleString('zh-CN') : '时间未知';
    const explanation = resultTab === 'recommended' ? item.reasons.join(' · ') : resultTab === 'recent' ? `修改时间：${date}` : `${item.categories.join('、')} · ${item.categorySource} · 修改时间：${date}`;
    return `<div class="row">${fileIcon(item.path)}<div class="row-main"><div class="row-title">${esc(fileDisplayName(item.path))}</div><div class="row-meta">${esc(item.path)}<br>${esc(explanation)}</div></div><div class="result-actions"><button class="result-pin ${pinned ? 'active' : ''}" data-result-pin="${esc(item.path)}" aria-label="${pinned ? '取消置顶' : '置顶'} ${esc(item.path)}" aria-pressed="${pinned}">${pinned ? '已置顶' : '置顶'}</button>${item.previewable !== false ? fileLink(item.path) : `<button class="row-action" data-copy-path="${esc(item.path)}">复制路径</button>`}</div></div>`;
  };
  const rows = visible.map(item => `${row(item)}${item.members?.length ? `<details class="result-group"><summary>同类待核材料 ${item.members.length} 项</summary>${item.members.map(row).join('')}</details>` : ''}`).join('');
  return `<section class="card" id="result-panel">${head('成果中心')}<div class="result-toolbar">${controls}${actions}</div>${categoryFilter}<details class="result-info"><summary>排序与分类说明</summary><p>${resultTab === 'recommended' ? `依据待核记录、阶段关联、项目登记及本地使用记录排序${contextNode ? ` · 当前阶段：${esc(contextNode)}` : ''}。` : resultTab === 'recent' ? '严格按文件修改时间排序。' : '优先依据项目登记分类，其余按文件类型识别。'}</p></details>${rows || empty('当前没有可展示的文件。')}${state.files_truncated ? '<p class="hint">扫描受到数量、深度或读取限制，列表可能不完整。</p>' : ''}</section>`;
}

function overview() {
  const pending = state.nodes.filter((n) => WorkbenchRanking.needsAttention(n.status));
  const changed = state.nodes.filter(gateNeedsReview);
  const reportIssues = (state.reports || []).filter(report => report.passed === false || report.error);
  const pendingRows = pending.map(n => `<div class="row"><span class="row-icon">${icon('alert')}</span><div class="row-main"><div class="row-title">${esc(n.id)} · ${esc(n.name)}</div><div class="row-meta">${esc(status(n.status))} · 来源：节点记录</div></div><button class="row-action" data-node="${esc(n.id)}">查看详情 ›</button></div>`).join('');
  const changedRow = changed.length ? `<div class="row"><span class="row-icon">${icon('shield')}</span><div class="row-main"><div class="row-title">${changed.map(n => esc(n.id)).join('、')} 批准文件待核</div><div class="row-meta">登记文件变化或批准记录待核 · 以 Harness 门禁为准</div></div><button class="row-action" data-page="flow">查看流程 ›</button></div>` : '';
  const reportRows = reportIssues.length ? `<div class="row"><span class="row-icon">${icon('file')}</span><div class="row-main"><div class="row-title">历史报告需核对</div><div class="row-meta">${reportIssues.map(report => esc(report.title)).join('、')} · 不是新检查</div></div><button class="row-action" data-page="paper">查看报告 ›</button></div>` : '';
  const attention = `<section class="card attention-card">${head('需要关注')}${pendingRows || changedRow || reportRows ? pendingRows + changedRow + reportRows : empty('项目记录中没有标记需要关注的事项。')}</section>`;
  return `<div class="overview-layout"><div class="overview-project">${projectCard()}</div><div class="overview-columns"><div class="stack">${attention}${resultPanel()}</div><div class="stack"><section class="card">${head('角色会话')}${roles(state.roles, true)}</section></div><div class="stack overview-paper">${paperFigureSummary()}</div></div></div>`;
}

function approvalRow(approval) {
  const states = {matches: '哈希一致', changed: '文件已变化', missing: '文件缺失', unverified: '无法核验', limit: '超过核验限制', invalid_digest: '登记哈希无效'};
  const digest = approval.digests || {status: 'unrecorded', files: []};
  const summary = digest.status === 'matches' ? '登记文件的哈希一致' : digest.status === 'issues' ? '登记文件有变化或无法核验' : '未登记可核验的哈希';
  return `<div class="approval"><div class="row"><div class="row-main"><div class="row-title">${esc(approval.gate)}</div><div class="row-meta">记录决定：${esc(approval.decision || '未记录')} · ${summary}</div></div><span class="pill ${digest.status === 'matches' ? '' : 'amber'}">${digest.status === 'matches' ? '一致' : '待核'}</span></div>${digest.files?.length ? `<details class="history"><summary>查看文件对比</summary>${digest.files.map(file => `<div>${esc(file.path)} · ${esc(states[file.status] || file.status)}</div>`).join('')}</details>` : ''}</div>`;
}

function chapterRows() {
  if (!state.chapters.length) return empty('尚未登记章节。');
  return state.chapters.map(c => {
    const approval = [...state.approvals].reverse().find(a => a.gate === `H7_CHAPTER:${c.id}`);
    const decision = approval ? `批准记录：${approval.decision || '未记录'}${approval.digests?.status === 'issues' ? '（文件变化或待核）' : ''}` : '未找到章节批准记录';
    const visual = c.visuals_required === false ? '记录为不需要图表' : c.visuals_required === true ? '记录为需要图表' : '图表需求未记录';
    const draftCovered = c.draft && approval?.digests?.files?.some(file => file.path === c.draft && file.status === 'matches');
    const transferReady = approval?.decision === 'approved' && approval?.digests?.status === 'matches' && draftCovered && c.draft_hash === 'matches';
    return `<div class="row">${fileIcon(c.draft)}<div class="row-main"><div class="row-title">${esc(c.id)}</div><div class="row-meta">正文：${esc(c.draft || '未登记')} · ${esc(decision)}<br>${visual} · 提示词版本：${c.prompt_revisions}</div>${c.prompts?.length ? `<details class="history"><summary>查看图表提示词版本</summary>${c.prompts.map((p, index) => { const ready = transferReady && index === c.prompts.length - 1 && p.hash === 'matches' && p.visual_plan_hash === 'matches'; return `<div>${esc(p.revision || '版本未登记')} · ${esc(p.path || '文件未登记')} ${p.path ? fileLink(p.path, '查看') : ''}${ready ? `<button class="row-action" data-copy-file="${esc(p.path)}">复制供手动转交</button>` : '<span> · 非最新版本或批准、提示词、视觉计划的哈希待核</span>'}</div>`; }).join('')}</details>` : ''}</div>${c.draft ? fileLink(c.draft) : ''}</div>`;
  }).join('');
}

function writingPlan() {
  const plan = state.writing_plan || {};
  const order = (value) => Array.isArray(value) ? value.map(display).join(' → ') : '未登记';
  const hash = plan.hash === 'matches' ? '已登记哈希与文件一致' : plan.hash === 'issues' ? '计划文件变化或待核' : '计划哈希未登记';
  return `<div class="model-block"><b>全篇计划</b><p class="subdued">写作顺序：${esc(order(plan.writing_order))}<br>论文顺序：${esc(order(plan.chapter_order))}<br>全文主张：${esc(display(plan.central_thesis))}<br>计划文件：${esc(plan.path || '未登记')} · ${hash} ${plan.path ? fileLink(plan.path, '查看计划') : ''}</p></div>`;
}

function flow() {
  const chapterView = state.visual_workflow === 'chapter_parallel' ? `<section class="card">${head('逐章写作与并行图表', '来源：H7 章节和批准记录')}<div class="notice">每章需经用户批准后才准备转交图表提示词；图表可与后续章节并行。批准记录和文件对比不能替代 Harness 门禁。</div>${writingPlan()}${chapterRows()}</section>` : '';
  const selected = state.nodes.find(n => n.id === contextNode) || state.nodes.find(n => WorkbenchRanking.needsAttention(n.status)) || state.nodes[0];
  if (!selected) return `<div class="stack flow-workspace"><div class="overview-project">${projectCard()}</div>${empty('项目没有可展示的阶段记录。')}</div>`;
  const evidence = selected.evidence || {};
  const approvals = state.approvals.filter(item => item.gate === selected.id);
  const taskSource = evidence.task_path || '任务卡未登记';
  const card = (title, symbol, description, content) => `<section class="flow-panel"><h3>${icon(symbol)}${title}</h3>${description ? `<p class="flow-source">${description}</p>` : ''}${content}</section>`;
  const inputs = card('输入材料', 'book', `来源：${esc(taskSource)}${evidence.task_error ? `（${esc(evidence.task_error)}）` : ''}`, evidenceRows(evidence.inputs, '任务卡中未登记输入。'));
  const outputs = card('任务要求与输出', 'checklist', `来源：${esc(taskSource)}；文件存在不代表已验收。`, evidenceRows(evidence.required_outputs, '任务卡中未登记要求输出。'));
  const artifacts = card('审查包登记成果', 'layers', `来源：${esc(evidence.review_path || '未登记')}${evidence.review_error ? `（${esc(evidence.review_error)}）` : ''}`, evidenceRows(evidence.artifacts, '审查包中未登记成果。'));
  const review = card('审查与批准记录', 'shield', '', `<p class="flow-review-summary">审查摘要：${esc(evidence.review_summary || '未登记')}</p><p class="flow-source">审查包建议：${esc(evidence.requested_decision || '未登记')} · 建议后续节点：${esc(evidence.next_node || '未登记')}</p>${approvals.length ? approvals.map(approvalRow).join('') : empty('未找到该阶段的批准记录。')}<p class="flow-source">批准记录来自项目文件；哈希一致不能证明批准真实性或代替 Harness 门禁。</p>${selected.review ? fileLink(selected.review, '查看审查包') : ''}`);
  const related = card('相关角色', 'users', '来源：阶段控制记录', `<div class="flow-owner"><span class="row-icon">${icon('users')}</span><div><strong>阶段负责人</strong><p>${esc(display(selected.owner))}</p></div></div>`);
  const files = card('阶段关联文件', 'file', '来源：控制记录；不推断输入或输出归属。', evidenceRows(evidence.related, '控制记录未登记关联文件。'));
  const note = card('状态说明', 'alert', '', `<p class="flow-review-summary">${gateNeedsReview(selected) ? '批准记录或登记文件待核，请依据实际记录和 Harness 门禁处理。' : '阶段状态来自项目记录；不代表实时运行状态或最终交付通过。'}</p>`);
  const allApprovals = `<details class="card flow-all-approvals"><summary>查看全部阶段批准记录</summary>${state.approval_error ? empty(`无法读取批准记录：${state.approval_error}`) : state.approvals.length ? state.approvals.map(approvalRow).join('') : empty('未找到批准条目。')}<div class="notice">${esc(state.approval_note)}</div></details>`;
  return `<div class="stack flow-workspace"><div class="overview-project">${projectCard()}</div><div class="flow-columns"><section class="card flow-detail" tabindex="-1"><div class="flow-heading"><span class="flow-stage-code">${esc(selected.id)}</span><h2>阶段：${esc(selected.name)}</h2>${badge(selected.status)}${gateNeedsReview(selected) ? '<span class="pill amber">批准或文件待核</span>' : ''}</div><div class="flow-overview"><span class="flow-overview-icon">${icon('file')}</span><div><h3>阶段概况</h3><p>${esc(evidence.objective || '阶段目标未在任务卡中登记。')}</p></div><div class="flow-overview-owner"><span>阶段负责人</span><strong>${esc(display(selected.owner))}</strong></div></div><div class="flow-panel-grid">${inputs}${outputs}${artifacts}${review}</div><details class="flow-source-details"><summary>查看阶段数据来源</summary><p>${esc(state.source)}</p></details></section><aside class="flow-side">${related}${files}${note}</aside></div>${chapterView}${allApprovals}</div>`;
}

function filePage(title, predicate, explanation) {
  const files = state.files.filter((file) => predicate(file.path.toLowerCase()));
  return `<section class="card">${head(title, `找到 ${files.length} 个文件`)}<p class="subdued" style="margin-bottom:15px">${esc(explanation)}</p>${files.length ? `<label class="file-search">按路径筛选<input type="search" data-file-search placeholder="输入文件名或路径"></label><div class="file-grid">${files.map((file) => file.previewable !== false ? `<button class="file-button" data-file="${esc(file.path)}" data-search-text="${esc(`${file.path} ${fileDisplayName(file.path)}`.toLowerCase())}">${fileIcon(file.path)}<div class="file-type">${esc(file.path.split('.').pop().toUpperCase())}　↗</div><div class="file-name">${esc(fileDisplayName(file.path))}</div><div class="file-original">${esc(file.path)}</div></button>` : `<div class="file-button" data-search-text="${esc(`${file.path} ${fileDisplayName(file.path)}`.toLowerCase())}">${fileIcon(file.path)}<div class="file-type">${esc(file.path.split('.').pop().toUpperCase())} · 暂不支持预览</div><div class="file-name">${esc(fileDisplayName(file.path))}</div><div class="file-original">${esc(file.path)}</div><button class="row-action" data-copy-path="${esc(file.path)}">复制完整路径</button></div>`).join('')}</div><p class="file-no-match" hidden>没有匹配的文件。</p>` : empty('项目中暂未找到相关文件。')}${state.files_truncated ? '<p class="hint">扫描受到数量、深度或读取限制，列表可能不完整。</p>' : ''}</section>`;
}

function questionPage() {
  const questions = state.question_views || [];
  const source = state.question_sources || {};
  const selected = questions.find(q => q.id === selectedQuestion) || questions[0];
  if (selected) selectedQuestion = selected.id;
  const searchText = q => `${q.id} ${display(q.objective)} ${display(QuestionLabels.text(q.objective))}`.toLowerCase();
  const list = questions.map(q => `<button class="question-option${q.id === selectedQuestion ? ' active' : ''}" data-question="${esc(q.id)}" data-question-search-text="${esc(searchText(q))}" aria-pressed="${q.id === selectedQuestion}" ${searchText(q).includes(questionQuery) ? '' : 'hidden'}><span class="question-radio" aria-hidden="true"></span><span class="question-option-copy"><strong>${esc(q.id)}</strong><span>${esc(display(QuestionLabels.text(q.objective)))}</span></span></button>`).join('');
  const values = value => Array.isArray(value) ? (value.length ? value.map(item => display(QuestionLabels.text(item))).join('、') : '未登记') : display(QuestionLabels.text(value));
  const sourceRow = (label, path, error) => `<div class="question-source-row"><span>${label}：${esc(path || '未登记')}${error ? `（${esc(error)}）` : ''}</span>${path ? fileLink(path, '查看') : ''}</div>`;
  const sources = `<details class="question-sources"><summary>数据来源与说明</summary><p>只展示明确登记的关联；结果尚未由工作台验证。</p>${sourceRow('问题信息', source.profile, source.profile_error)}${sourceRow('模型总结卡', source.models, source.models_error)}${sourceRow('结果解释卡', source.results, source.results_error)}</details>`;
  if (!selected) return `<div class="question-layout"><section class="card question-list"><h2>小问列表</h2>${empty('控制记录中未登记可识别的小问。')}${sources}</section><section class="card question-detail">${empty('暂无可展示的小问详情。')}</section></div>`;
  const associations = selected.associations || {};
  const models = selected.models || [];
  const interpretations = selected.interpretations || [];
  const block = (title, iconName, content) => `<section class="question-section"><h3>${icon(iconName)}${title}</h3>${content}</section>`;
  const modelsContent = models.length ? models.map(model => `<div class="question-item"><span class="question-item-icon">${icon('solve')}</span><div><strong>${esc(QuestionLabels.model(model.id))}</strong><p>结果：${esc(display(QuestionLabels.result(model.result)))}</p></div></div>`).join('') : '<p class="question-empty">尚未登记模型</p>';
  const results = interpretations.length ? interpretations.map(item => `<div class="question-item"><span class="question-item-icon">${icon('chart')}</span><div><strong>${esc(display(item.fact))}</strong><p>含义：${esc(display(item.meaning))}</p><p>边界：${esc(display(item.boundary))}</p><p>验证记录：${esc(display(item.verification))}</p></div></div>`).join('') : '<p class="question-empty">尚未登记结果解释</p>';
  const materials = associations.materials || [];
  const material = materials.length ? materials.map(item => `<div class="question-item">${fileIcon(item.path)}<div class="question-item-copy"><strong>${esc(fileDisplayName(item.path))}</strong><p>${esc(item.relation)}</p><p>来源：${esc(item.source || '未登记')} · ${esc(item.path)}</p></div>${item.previewable ? fileLink(item.path) : `<button class="row-action" data-copy-path="${esc(item.path)}">复制路径</button>`}</div>`).join('') : '<p class="question-empty">未识别到已登记的关联材料</p>';
  const stages = (associations.stages || []).map(stage => `<div class="question-item"><span class="question-item-icon">${icon('flag')}</span><div class="question-item-copy"><strong>${esc(stage.id)} · ${esc(stage.name)}</strong><p>覆盖小问 · 来源：${esc(stage.source)}</p></div><button class="row-action" data-node="${esc(stage.id)}">查看</button></div>`).join('') || '<p class="question-empty">未识别阶段与小问的关联</p>';
  const assigned = (associations.roles || []).map(role => `<div class="question-item"><span class="question-item-icon">${icon('users')}</span><div class="question-item-copy"><strong>${esc(role.name)}</strong><p>${esc(role.node)} 任务负责人 · 来源：任务卡和控制记录中的派发记录</p><p>任务卡：${esc(role.source)} · 任务：${esc(role.task_id)}；不代表文件作者</p></div></div>`).join('') || '<p class="question-empty">未识别角色与小问的关联</p>';
  return `<div class="question-layout"><aside class="card question-list"><label class="question-search"><span class="sr-only">搜索小问</span>${icon('search')}<input type="search" data-question-search placeholder="搜索小问名称或关键词" value="${esc(questionQuery)}"></label><div class="question-options">${list}<p class="question-empty question-no-match" ${questions.some(q => searchText(q).includes(questionQuery)) ? 'hidden' : ''}>没有匹配的小问</p></div>${sources}</aside><article class="card question-detail"><div class="question-panel-head"><h2>${esc(selected.id)}</h2><span class="question-readonly">只读</span></div>${block('问题描述', 'file', `<div class="question-description">${esc(display(QuestionLabels.text(selected.objective)))}</div>`)}${block('输入与输出', 'layers', `<div class="question-io"><div><span>输入</span><p>${esc(values(selected.inputs))}</p></div><div><span>输出</span><p>${esc(values(selected.outputs))}</p></div><div><span>跨问接口</span><p>${esc(display(QuestionLabels.text(selected.interface)))}</p></div></div>`)}${block('已登记模型', 'solve', modelsContent)}${block('结果解释', 'chart', results)}<details class="question-original"><summary>查看原始记录</summary><pre>${esc(JSON.stringify(selected, null, 2))}</pre></details></article><aside class="card question-related"><div class="question-panel-head"><h2>${icon('layers')}关联信息</h2></div>${block('关联材料', 'file', material)}${block('关联阶段', 'flag', stages)}${block('关联角色', 'users', assigned)}</aside></div>`;
}

function figureGallery() {
  const figures = state.figures || [];
  const cards = figures.map(f => `<article class="figure-card">${f.png ? `<button class="figure-preview" data-file="${esc(f.png)}"><img src="${fileUrl(f.png)}" alt="${esc(f.id)} 预览"></button>` : '<div class="figure-placeholder">暂无 PNG 预览</div>'}<div class="figure-info"><strong>${esc(f.id)}</strong><p>${esc(f.caption || '图表论点未登记')}</p><div class="row-meta">论文位置：${esc(f.location || '未登记')}<br>质量记录：${esc(f.qa_status || '未登记')}（未由工作台核验）</div><div class="figure-links">${f.png ? fileLink(f.png, 'PNG') : ''}${f.svg ? fileLink(f.svg, 'SVG 源') : ''}${f.source_files.map(path => fileLink(path, path.split('/').pop())).join('')}</div></div></article>`).join('');
  return `<section class="card">${head('已登记图表', `来源：${state.figure_source || '未登记'}`)}${state.figure_error ? `<p class="subdued">图表登记读取情况：${esc(state.figure_error)}</p>` : ''}${figures.length ? `<div class="figure-grid">${cards}</div>` : empty('未找到图表登记记录；下方仍可浏览项目文件。')}</section>`;
}

function skillsPage() {
  const invoked = state.nodes.flatMap(node => (node.skills || []).map(skill => ({...skill, node: node.id})));
  const skills = [...(state.skills || [])];
  for (const item of invoked) if (item.name && !skills.some(skill => skill.name === item.name)) skills.push({name: item.name, purpose: '项目调用记录中的技能', available: null});
  const chosen = skills.find(skill => skill.name === selectedSkill) || skills[0];
  selectedSkill = chosen?.name || null;
  const localStatus = skill => skill.available === true ? '入口存在' : skill.available === false ? '入口缺失' : '入口未检查';
  const list = skills.map(skill => `<button class="skill-option${skill.name === selectedSkill ? ' active' : ''}" data-select-skill="${esc(skill.name)}" aria-pressed="${skill.name === selectedSkill}"><span class="skill-icon">${icon(skill.name.includes('figure') || skill.name === 'modelviz' ? 'chart' : skill.name.includes('writing') || skill.name.includes('latex') ? 'file' : 'spark')}</span><span class="skill-copy"><strong>${esc(skill.purpose)}</strong><small>${esc(skill.name)}</small></span><span class="skill-state">${esc(localStatus(skill))}</span></button>`).join('');
  const calls = chosen ? invoked.filter(item => item.name === chosen.name) : [];
  const callRows = calls.length ? calls.map(call => `<div class="skill-call"><strong>${esc(call.node)}</strong><span>${call.not_applicable ? `记录为不适用：${esc(call.reason || '原因未记录')}` : call.completed === true ? '记录为已完成' : '完成情况未记录'}</span>${call.evidence && state.files.some(file => file.path === call.evidence && file.previewable !== false) ? fileLink(call.evidence, '查看证据') : ''}${call.evidence ? `<small>证据：${esc(call.evidence)}</small>` : ''}</div>`).join('') : '<p class="skill-empty">项目记录中没有该技能的调用条目。</p>';
  const detail = chosen ? `<section class="card skill-detail"><div class="skill-panel-title"><h2>${icon('layers')}技能概览</h2></div><div class="skill-detail-head"><span class="skill-icon large">${icon('spark')}</span><div><h3>${esc(chosen.purpose)}</h3><p>${esc(chosen.name)}</p></div><span class="skill-state">${esc(localStatus(chosen))}</span></div><div class="skill-block"><h3>${icon('file')}能力说明</h3><p>${esc(chosen.purpose)}</p></div><div class="skill-block"><h3>${icon('flow')}项目调用记录</h3>${callRows}</div><details class="skill-note"><summary>状态与来源说明</summary><p>入口状态仅检查本机技能入口文件；调用记录来自项目控制文件，均不代表工作台已核验执行或门禁通过。</p></details></section>` : `<section class="card skill-detail">${empty('没有可展示的技能。')}</section>`;
  const evidence = state.nodes.filter(node => node.review).map(node => `<div class="skill-evidence"><span>${esc(node.id)} 审查包</span>${state.files.some(file => file.path === node.review && file.previewable !== false) ? fileLink(node.review, '查看') : '<span>未找到文件</span>'}</div>`).join('');
  const rules = `<aside class="card skill-rules"><div class="skill-panel-title"><h2>${icon('flow')}项目流程与记录</h2></div><div class="skill-rule"><h3>${icon('layers')}工作流</h3><p>模式：${esc(state.mode)}<br>流程：${esc(state.visual_workflow)}</p></div><div class="skill-rule"><h3>${icon('shield')}验证与批准</h3><p>阶段审查、独立验证和人工批准以 Harness 门禁及项目记录为准。</p></div><div class="skill-rule"><h3>${icon('file')}已登记审查包</h3>${evidence || '<p>未登记审查包。</p>'}</div></aside>`;
  return `<div class="skills-layout"><section class="card skill-list"><div class="skill-panel-title"><h2>${icon('spark')}常用技能与项目记录</h2></div><p class="skill-list-intro">本机入口检查与项目调用记录</p><div class="skill-options">${list || empty('没有可展示的技能。')}</div></section>${detail}${rules}</div>`;
}

function reportSection() {
  const reports = state.reports || [];
  return `<section class="card">${head('已有检查报告', '文件记录，不是实时检查')}${reports.length ? reports.map(report => `<div class="row">${fileIcon(report.path)}<div class="row-main"><div class="row-title">${esc(report.title)}</div><div class="row-meta">${report.passed === true ? '记录为通过' : report.passed === false ? '记录为未通过' : '结果待核'} · ${report.modified ? `文件时间：${esc(new Date(report.modified * 1000).toLocaleString('zh-CN'))}` : '时间未知'}<br>${esc(report.path)}${report.error ? `<br>${esc(report.error)}` : ''}</div>${report.issues?.length ? `<details class="history"><summary>查看记录的 ${report.issues.length} 个问题</summary>${report.issues.map(issue => `<div>${esc(issue)}</div>`).join('')}</details>` : ''}</div>${fileLink(report.path, '查看报告')}</div>`).join('') : empty('未发现可识别的报告；不代表检查已通过。')}</section>`;
}

function deliveryPage() {
  const h9 = state.nodes.find(node => node.id === 'H9');
  const h6 = state.nodes.find(node => node.id === 'H6');
  const candidates = [
    {title: '论文文件', path: state.paper_pdf, detail: '同名 PDF 与源文件的一致性待核'},
    {title: '图表清单', path: state.figure_source, detail: '图表登记记录'},
    {title: '独立验证审查包', path: h6?.review, detail: 'H6 阶段记录'},
    {title: 'H9 审查包', path: h9?.review, detail: '交付阶段记录'},
    ...(state.reports || []).map(report => ({title: report.title, path: report.path, detail: report.error ? '报告读取待核' : report.passed === true ? '历史记录为通过' : report.passed === false ? '历史记录为未通过' : '历史结果待核'})),
  ];
  const rows = candidates.map(item => ({...item, file: state.files.find(file => file.path === item.path)}));
  const available = rows.filter(item => item.file);
  const selected = available.find(item => item.path === selectedDeliveryFile) || available[0];
  selectedDeliveryFile = selected?.path || null;
  const list = rows.map(item => `<div class="delivery-row${item.path && item.path === selectedDeliveryFile ? ' active' : ''}"><span class="delivery-row-icon">${item.path ? fileIcon(item.path) : icon('file')}</span><div class="delivery-row-copy"><strong>${esc(item.title)}</strong><p>${esc(item.detail)}</p><small>${esc(item.path || '未登记')}</small></div>${item.file ? `<button class="row-action" data-delivery-file="${esc(item.path)}" aria-pressed="${item.path === selectedDeliveryFile}">查看</button>` : '<span class="delivery-missing">未找到</span>'}</div>`).join('');
  return `<div class="delivery-layout"><div class="stack delivery-main"><section class="delivery-overview"><span class="delivery-status-icon">${icon('shield')}</span><div><span>H9 交付节点记录</span><h2>${esc(h9 ? status(h9.status) : '未登记')}</h2></div><div class="delivery-overview-source"><strong>项目记录</strong><p>${esc(state.name)}</p><p>状态取自控制记录，不代表最终交付通过。</p></div></section><section class="card delivery-list"><div class="catalog-heading"><h2>${icon('checklist')}交付材料与历史报告</h2></div>${list}<details class="catalog-note"><summary>查看全部交付与审查材料</summary>${filePage('交付与审查材料', path => /delivery|交付|h9|审查/.test(path), '只展示项目中已有材料。')}</details></section></div>${selected ? catalogDetail(selected.file, null) : `<aside class="card catalog-detail"><div class="catalog-heading"><h2>证据查看</h2></div>${empty('没有可查看的已登记文件。')}</aside>`}</div>`;
}

function paperPage() {
  const pdf = state.files.find(file => file.path === state.paper_pdf);
  const source = state.files.find(file => file.path === state.paper_source);
  const chapters = state.chapters || [];
  const chapterList = chapters.length ? chapters.map(chapter => `<div class="paper-list-row"><span class="paper-list-icon">${icon('file')}</span><div class="paper-list-copy"><strong>${esc(chapter.id)}</strong><span>${chapter.draft ? esc(chapter.draft) : '正文文件未登记'}</span></div>${chapter.draft ? fileLink(chapter.draft) : ''}</div>`).join('') : '<p class="paper-empty">项目中未登记逐章写作记录。</p>';
  const paperFiles = [source, pdf].filter(Boolean).map(file => `<div class="paper-list-row">${fileIcon(file.path)}<div class="paper-list-copy"><strong>${esc(fileDisplayName(file.path))}</strong><span>${esc(file.path)}</span></div>${fileLink(file.path)}</div>`).join('');
  const figures = (state.figures || []).filter(figure => figure.png && state.files.some(file => file.path === figure.png));
  const figureList = figures.length ? `<div class="paper-figure-grid">${figures.map(figure => `<button class="paper-figure" data-file="${esc(figure.png)}"><img loading="lazy" src="${fileUrl(figure.png)}" alt="${esc(figure.id)}"><span>${esc(figure.id)}</span></button>`).join('')}</div>` : '<p class="paper-empty">项目未登记可预览的图表。</p>';
  const reports = state.reports || [];
  const reportList = reports.length ? reports.map(report => `<div class="paper-list-row"><span class="paper-list-icon">${icon('file')}</span><div class="paper-list-copy"><strong>${esc(report.title)}</strong><span>${report.passed === true ? '记录为通过' : report.passed === false ? '记录为未通过' : '结果待核'}${report.modified ? ` · ${esc(new Date(report.modified * 1000).toLocaleDateString('zh-CN'))}` : ''}</span></div>${fileLink(report.path)}</div>`).join('') : '<p class="paper-empty">未发现可识别的历史报告。</p>';
  const literature = (state.literature || []).filter(item => typeof item.path === 'string');
  const sources = literature.length ? literature.map(item => `<div class="paper-list-row"><span class="paper-list-icon">${icon('book')}</span><div class="paper-list-copy"><strong>${esc(item.name)}</strong><span>${esc(item.path)}</span></div>${fileLink(item.path)}</div>`).join('') : '<p class="paper-empty">项目未登记文献交接资料。</p>';
  const details = state.visual_workflow === 'chapter_parallel' ? `<details class="card paper-extra"><summary>逐章写作记录</summary>${writingPlan()}${chapterRows()}</details>` : '';
  const viewer = pdf ? `<div class="paper-viewer-heading"><div class="paper-viewer-title">${fileIcon(pdf.path)}<div><h2>论文 PDF 预览</h2><span>${esc(pdf.path)}</span></div></div><span class="paper-readonly">只读</span></div><div id="paper-pdf"></div><details class="paper-viewer-note"><summary>预览说明与源文件</summary><p>PDF 与已登记论文源文件的内容一致性尚未由工作台核验，不代表已通过最终审查。</p><div class="paper-viewer-actions">${fileLink(pdf.path, '打开 PDF')}${source ? fileLink(source.path, '查看 LaTeX 源文件') : ''}</div></details>` : `<div class="paper-viewer-heading"><h2>论文 PDF 预览</h2><span class="paper-readonly">只读</span></div>${empty('未找到已登记论文源文件的同名 PDF。')}`;
  return `<div class="stack paper-workspace"><div class="paper-columns"><aside class="card paper-nav"><div class="paper-panel-heading"><h2>${icon('book')}论文目录与章节</h2></div>${chapterList}<div class="paper-panel-heading paper-subheading"><h2>${icon('file')}论文文件</h2></div>${paperFiles || '<p class="paper-empty">论文源文件和 PDF 未登记或未找到。</p>'}</aside><section class="card paper-viewer">${viewer}</section><aside class="paper-side"><section class="card"><div class="paper-panel-heading"><h2>${icon('chart')}项目登记图表</h2><span>${figures.length} 张</span></div>${figureList}</section><section class="card"><div class="paper-panel-heading"><h2>${icon('shield')}历史检查报告</h2></div>${reportList}<p class="paper-footnote">报告为历史记录，不表示已执行新的检查。</p></section><section class="card"><div class="paper-panel-heading"><h2>${icon('book')}文献交接资料</h2></div>${sources}</section></aside></div>${details}<details class="paper-all-files"><summary>查看全部论文文件</summary>${filePage('论文文件', p => /(^|\/)(paper|论文)(\/|_|\.)/.test(p) || /chapter|appendix/.test(p), '可预览已有 PDF 和论文源文件；当前不提供编辑或编译。')}</details></div>`;
}

function literaturePage() {
  const references = new Set((state.literature || []).map(item => item.path).filter(path => typeof path === 'string'));
  const files = state.files.filter(file => references.has(file.path) || /(^|\/)(01_input|input|references|literature|文献|资料)(\/|_)/i.test(file.path) || /problem_statement|problem_profile|literature/i.test(file.path));
  const directoryOf = path => path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : '项目根目录';
  const directoryLabel = name => ({'全部': '全部资料', '01_input': '题目与附件', 'input': '输入资料', 'references': '参考资料', 'references/warmup': '参考资料 / 准备记录', '.contest/delivery_reports': '交付检查记录', 'results': '结果文件'}[name] || name);
  const directories = [...new Set(files.map(file => directoryOf(file.path)))].sort((a, b) => a.localeCompare(b, 'zh-CN'));
  if (libraryDirectory !== '全部' && !directories.includes(libraryDirectory)) libraryDirectory = '全部';
  const filtered = files.filter(file => libraryDirectory === '全部' || directoryOf(file.path) === libraryDirectory);
  let selected = filtered.find(file => file.path === selectedLibraryFile) || filtered[0];
  selectedLibraryFile = selected?.path || null;
  const directoryList = ['全部', ...directories].map(name => `<button class="catalog-folder${libraryDirectory === name ? ' active' : ''}" data-library-directory="${esc(name)}" title="${esc(name)}" aria-pressed="${libraryDirectory === name}">${icon(name === '全部' ? 'layers' : 'book')}<span>${esc(directoryLabel(name))}</span><small>${name === '全部' ? files.length : files.filter(file => directoryOf(file.path) === name).length}</small></button>`).join('');
  const rows = filtered.map(file => catalogRow(file, selectedLibraryFile, 'library')).join('');
  return `<div class="catalog-layout library-layout"><aside class="card catalog-directories"><div class="catalog-heading"><h2>${icon('book')}资料目录</h2></div><div class="catalog-folders">${directoryList}</div><details class="catalog-note"><summary>资料来源说明</summary><p>仅浏览项目内已有资料；文献获取与全文处理由用户及指定角色负责。</p></details></aside><section class="card catalog-list"><div class="catalog-heading"><h2>文件列表</h2><span>${filtered.length} 项</span></div><label class="catalog-search">${icon('search')}<span class="sr-only">搜索资料</span><input type="search" data-catalog-search placeholder="搜索文件名或路径" value="${esc(catalogQuery)}"></label><div class="catalog-list-header"><span>文件名称</span><span>更新时间</span><span>操作</span></div><div class="catalog-rows">${rows || empty('当前目录没有可展示的文件。')}</div><p class="catalog-no-match" ${!filtered.length || filtered.some(file => `${file.path} ${fileDisplayName(file.path)}`.toLowerCase().includes(catalogQuery)) ? 'hidden' : ''}>没有匹配的文件。</p>${state.files_truncated ? '<p class="hint">扫描受到数量、深度或读取限制，列表可能不完整。</p>' : ''}</section>${catalogDetail(selected, null)}</div>`;
}

function catalogRow(file, selected, kind) {
  const search = `${file.path} ${fileDisplayName(file.path)}`.toLowerCase();
  const date = file.modified ? new Date(file.modified * 1000).toLocaleString('zh-CN') : '时间未知';
  return `<div class="catalog-row${file.path === selected ? ' active' : ''}" data-catalog-row data-catalog-text="${esc(search)}" ${search.includes(catalogQuery) ? '' : 'hidden'}><button class="catalog-select" data-catalog-select="${esc(file.path)}" data-catalog-kind="${kind}" aria-pressed="${file.path === selected}">${fileIcon(file.path)}<span><strong>${esc(fileDisplayName(file.path))}</strong><small>${esc(file.path)}</small></span></button><span class="catalog-date">${esc(date)}</span>${file.previewable !== false ? fileLink(file.path) : `<button class="row-action" data-copy-path="${esc(file.path)}">复制路径</button>`}</div>`;
}

function catalogDetail(file, ranking) {
  if (!file) return `<aside class="card catalog-detail"><div class="catalog-heading"><h2>文件详情</h2></div>${empty('请选择一个文件。')}</aside>`;
  const date = file.modified ? new Date(file.modified * 1000).toLocaleString('zh-CN') : '时间未知';
  const ext = file.path.split('.').pop().toUpperCase();
  const figure = (state.figures || []).find(item => item.png === file.path || item.svg === file.path);
  const pinned = ranking && resultPreferences().pins.includes(file.path);
  return `<aside class="stack catalog-detail"><section class="card"><div class="catalog-heading"><h2>${icon('file')}文件信息</h2><span>只读</span></div><div class="catalog-detail-name">${fileIcon(file.path)}<strong>${esc(fileDisplayName(file.path))}</strong></div><dl class="catalog-meta"><div><dt>原始路径</dt><dd>${esc(file.path)}</dd></div><div><dt>文件类型</dt><dd>${esc(ext)}</dd></div><div><dt>更新时间</dt><dd>${esc(date)}</dd></div>${figure?.caption ? `<div><dt>图表说明</dt><dd>${esc(figure.caption)}</dd></div>` : ''}${figure?.qa_status ? `<div><dt>质量记录</dt><dd>${esc(figure.qa_status)} · 工作台未核验</dd></div>` : ''}${ranking ? `<div><dt>分类依据</dt><dd>${esc(ranking.categories.join('、'))} · ${esc(ranking.categorySource)}</dd></div><div><dt>推荐依据</dt><dd>${esc(ranking.reasons.join(' · '))}</dd></div>` : ''}</dl><div class="catalog-detail-action">${file.previewable !== false ? fileLink(file.path, '打开文件') : `<button class="row-action" data-copy-path="${esc(file.path)}">复制完整路径</button>`}${ranking ? `<button class="row-action" data-result-pin="${esc(file.path)}" aria-pressed="${!!pinned}">${pinned ? '取消置顶' : '置顶'}</button>` : ''}</div></section><section class="card catalog-preview-card"><div class="catalog-heading"><h2>${icon('book')}文件预览</h2></div><div id="catalog-preview" data-preview-path="${esc(file.path)}">${file.previewable === false ? '<p class="paper-empty">文件超过 20 MB 或类型不支持，无法预览；可复制路径后打开。</p>' : '正在加载预览…'}</div></section></aside>`;
}

function artifactPage() {
  const ranked = WorkbenchRanking.build(state, resultPreferences(), contextNode);
  const list = resultTab === 'recommended' ? WorkbenchRanking.diverse(ranked) : [...ranked].sort((a, b) => (b.modified || 0) - (a.modified || 0) || a.path.localeCompare(b.path));
  const filtered = list.filter(file => (resultCategory === '全部' || file.categories.includes(resultCategory)) && (artifactStage === '全部' || file.nodes.includes(artifactStage)));
  const selected = filtered.find(file => file.path === selectedArtifact) || filtered[0];
  selectedArtifact = selected?.path || null;
  const tabs = [['recommended', '推荐查看'], ['recent', '最近更新'], ['categories', '分类浏览']];
  const controls = `<div class="result-tabs" role="group" aria-label="成果视图">${tabs.map(([id, label]) => `<button class="result-tab ${resultTab === id ? 'active' : ''}" data-result-tab="${id}" aria-pressed="${resultTab === id}">${label}</button>`).join('')}</div>`;
  const rows = filtered.map(file => catalogRow(file, selectedArtifact, 'artifact')).join('');
  return `<div class="catalog-layout artifact-layout"><section class="card catalog-list artifact-list"><div class="catalog-heading"><h2>${icon('layers')}成果中心</h2><span>${filtered.length} 项</span></div>${controls}<div class="catalog-filters"><label class="catalog-search">${icon('search')}<span class="sr-only">搜索成果</span><input type="search" data-catalog-search placeholder="搜索文件名或路径" value="${esc(catalogQuery)}"></label><label class="catalog-category"><span class="sr-only">成果分类</span><select id="result-category">${['全部', ...WorkbenchRanking.categories].map(category => `<option${category === resultCategory ? ' selected' : ''}>${esc(category)}</option>`).join('')}</select></label><label class="catalog-category"><span class="sr-only">登记关联阶段</span><select id="artifact-stage"><option value="全部">全部阶段</option>${state.nodes.map(node => `<option value="${esc(node.id)}"${node.id === artifactStage ? ' selected' : ''}>${esc(node.id)} · ${esc(node.name)}</option>`).join('')}</select></label></div><div class="catalog-list-header"><span>成果名称与类型</span><span>更新时间</span><span>操作</span></div><div class="catalog-rows">${rows || empty('当前筛选没有可展示的文件。')}</div><p class="catalog-no-match" ${!filtered.length || filtered.some(file => `${file.path} ${fileDisplayName(file.path)}`.toLowerCase().includes(catalogQuery)) ? 'hidden' : ''}>没有匹配的文件。</p><details class="catalog-note"><summary>排序与分类说明</summary><p>${resultTab === 'recommended' ? '依据待核记录、阶段关联、项目登记及本地使用记录排序。' : '按文件修改时间排序。'}分类优先采用项目登记，其余按文件类型识别；阶段筛选仅依据已登记的文件关联。</p></details>${state.files_truncated ? '<p class="hint">扫描受到数量、深度或读取限制，列表可能不完整。</p>' : ''}</section>${catalogDetail(selected, selected)}</div>`;
}

function render() {
  document.body.dataset.view = current;
  nav();
  const page = pages.find(([id]) => id === current);
  $('#page-title').textContent = page[2]; $('#page-subtitle').textContent = page[3];
  if (!state) return;
  $('#project-search').title = state.name ? `当前项目：${state.name}` : '搜索已有项目';
  const files = (title, predicate, explanation) => filePage(title, predicate, explanation);
  const views = {
    overview,
    flow,
    roles: rolePage,
    questions: questionPage,
    literature: literaturePage,
    artifacts: artifactPage,
    paper: paperPage,
    skills: skillsPage,
    delivery: deliveryPage,
  };
  $('#content').innerHTML = views[current]();
  if (current === 'paper' && $('#paper-pdf')) renderPdf($('#paper-pdf'), state.paper_pdf);
  const catalogPreview = $('#catalog-preview');
  if (catalogPreview) {
    const file = state.files.find(item => item.path === catalogPreview.dataset.previewPath);
    if (file?.previewable !== false) renderCatalogPreview(catalogPreview, file?.path);
  }
}

async function refresh() {
  const generation = ++syncGeneration;
  try {
    const selected = selectedProjectPath();
    const response = await fetch(`/api/state${selected ? `?project=${encodeURIComponent(selected)}` : ''}`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    if (generation !== syncGeneration) return;
    if (state?.project && state.project !== result.project) { contextNode = null; resultExpanded = false; resultCategory = '全部'; artifactStage = '全部'; selectedQuestion = null; selectedRole = null; selectedSkill = null; selectedDeliveryFile = null; selectedLibraryFile = null; selectedArtifact = null; libraryDirectory = '全部'; catalogQuery = ''; questionQuery = ''; }
    state = result; syncSnapshot = JSON.stringify(result); syncCandidate = ''; $('#error').hidden = true; render();
    syncStatus('已同步');
    if (!$('#project-search-panel').hidden) showProjects();
  } catch (error) {
    if (generation !== syncGeneration) return;
    syncStatus('同步失败');
    $('#error').textContent = `${error.message}。请通过“搜索项目”选择可用项目。`;
    $('#error').hidden = false;
    if (!state?.project) $('#content').innerHTML = '<div class="empty">当前项目无法读取。</div>';
    if (!state) {
      try {
        const bootstrap = await fetch('/api/bootstrap');
        if (bootstrap.ok) { state = { ...await bootstrap.json(), project: '' }; if (!$('#project-search-panel').hidden) showProjects(); }
      } catch { /* The service itself is unreachable; keep the visible error. */ }
    }
  }
}

function syncStatus(label) {
  const statusElement = $('#sync-status');
  if (!statusElement) return;
  if (label !== '同步失败') statusElement.removeAttribute('title');
  statusElement.textContent = label === '已同步' ? `${label} ${new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})}` : label;
  const refreshButton = $('#refresh');
  refreshButton.title = `刷新项目 · ${statusElement.textContent}`;
  refreshButton.setAttribute('aria-label', refreshButton.title);
  refreshButton.dataset.syncState = label === '同步失败' ? 'error' : label === '检测到变化' || label === '更新待应用' ? 'pending' : 'ok';
}

function syncInteractionInProgress() {
  const active = document.activeElement;
  return Boolean(document.querySelector('dialog[open], #content details[open]') || (active && active.matches('input, textarea, select, [contenteditable="true"]')));
}

async function checkSync() {
  if (syncBusy || document.hidden || !state?.project) return;
  syncBusy = true;
  const generation = syncGeneration;
  const project = state.project;
  try {
    const response = await fetch(`/api/state?project=${encodeURIComponent(project)}`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || '无法读取项目');
    if (generation !== syncGeneration || state?.project !== project) return;
    const snapshot = JSON.stringify(result);
    if (snapshot === syncSnapshot) { syncCandidate = ''; syncStatus('已同步'); return; }
    if (snapshot !== syncCandidate) { syncCandidate = snapshot; syncStatus('检测到变化'); return; }
    if (syncInteractionInProgress()) { syncStatus('更新待应用'); return; }
    state = result;
    syncSnapshot = snapshot;
    syncCandidate = '';
    $('#error').hidden = true;
    const scrollPosition = window.scrollY;
    render();
    window.scrollTo(0, scrollPosition);
    syncStatus('已同步');
  } catch (error) {
    if (generation === syncGeneration) { syncCandidate = ''; syncStatus('同步失败'); $('#refresh').title = `刷新项目 · 同步失败：${error.message}`; }
  } finally { syncBusy = false; }
}

async function post(path, body) {
  const send = () => fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Workbench-Token': state.token }, body: JSON.stringify(body) });
  let response = await send();
  if (response.status === 403) {
    const bootstrap = await fetch('/api/bootstrap');
    if (bootstrap.ok) {
      state.token = (await bootstrap.json()).token;
      response = await send();
    }
  }
  const result = await response.json();
  if (!response.ok) throw new Error(result.error);
}

function fileUrl(path) {
  return `/api/file?path=${encodeURIComponent(path)}&project=${encodeURIComponent(state.project)}`;
}

async function renderPdf(container, path) {
  container.textContent = '正在加载 PDF…';
  const query = `path=${encodeURIComponent(path)}&project=${encodeURIComponent(state.project)}`;
  try {
    const response = await fetch(`/api/pdf-info?${query}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    if (!data.pages) throw new Error('PDF 没有可预览页面');
    let page = 1;
    container.innerHTML = `<div class="pdf-toolbar"><button class="pdf-previous">上一页</button><span></span><button class="pdf-next">下一页</button></div><div class="pdf-canvas"><img alt="PDF 页面预览"><p class="pdf-page-error" role="status" hidden>PDF 页面无法读取，文件可能已变动或损坏。</p></div>`;
    const image = container.querySelector('img');
    const label = container.querySelector('.pdf-toolbar span');
    const previous = container.querySelector('.pdf-previous');
    const next = container.querySelector('.pdf-next');
    const pageError = container.querySelector('.pdf-page-error');
    image.addEventListener('error', () => { image.hidden = true; pageError.hidden = false; });
    const update = () => { pageError.hidden = true; image.hidden = false; label.textContent = `${page} / ${data.pages}`; previous.disabled = page === 1; next.disabled = page === data.pages; image.src = `/api/pdf-page?${query}&page=${page}`; };
    previous.addEventListener('click', () => { if (page > 1) { page--; update(); } });
    next.addEventListener('click', () => { if (page < data.pages) { page++; update(); } });
    update();
  } catch (error) {
    container.textContent = `PDF 预览不可用：${error.message}。`;
    const link = document.createElement('a');
    link.href = fileUrl(path); link.target = '_blank'; link.rel = 'noopener'; link.textContent = '在新标签页打开原文件';
    container.append(link);
  }
}

async function renderDocument(container, path, sheet = '') {
  container.textContent = '正在读取文档预览…';
  const query = `path=${encodeURIComponent(path)}&project=${encodeURIComponent(state.project)}&sheet=${encodeURIComponent(sheet)}`;
  try {
    const response = await fetch(`/api/document?${query}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    const table = (rows) => `<div class="table-scroll"><table>${rows.map(row => `<tr>${row.map(cell => `<td>${esc(cell)}</td>`).join('')}</tr>`).join('')}</table></div>`;
    if (data.type === 'xlsx') {
      container.innerHTML = `<div class="document-toolbar"><label>工作表 <select>${data.sheets.map(name => `<option ${name === data.sheet ? 'selected' : ''} value="${esc(name)}">${esc(name)}</option>`).join('')}</select></label><span>${esc(data.note)}</span></div>${table(data.rows)}`;
      container.querySelector('select').addEventListener('change', event => renderDocument(container, path, event.target.value));
    } else if (data.type === 'csv') {
      container.innerHTML = `<div class="document-toolbar"><span>${esc(data.note)}</span></div>${table(data.rows)}`;
    } else {
      const blocks = Array.isArray(data.blocks) ? data.blocks : [...data.paragraphs.map(text => ({type: 'paragraph', text})), ...data.tables.map(rows => ({type: 'table', rows}))];
      container.innerHTML = `<div class="notice">${esc(data.note)}</div><div class="document-text">${blocks.map(block => block.type === 'paragraph' ? `<p>${esc(block.text)}</p>` : table(block.rows)).join('')}</div>`;
    }
  } catch (error) { container.textContent = `文档预览不可用：${error.message}`; }
}

function previewImage(path, alt) {
  const image = document.createElement('img');
  image.alt = alt;
  image.addEventListener('error', () => {
    const message = document.createElement('p');
    message.textContent = '图片无法读取，文件可能已移动或损坏。';
    image.replaceWith(message);
  }, { once: true });
  image.src = fileUrl(path);
  return image;
}

async function renderCatalogPreview(container, path) {
  if (!path) return;
  if (/\.pdf$/i.test(path)) return renderPdf(container, path);
  if (/\.(docx|xlsx|csv)$/i.test(path)) return renderDocument(container, path);
  if (/\.(png|jpe?g)$/i.test(path)) {
    container.replaceChildren(previewImage(path, fileDisplayName(path)));
    return;
  }
  try {
    const response = await fetch(fileUrl(path));
    if (!response.ok) throw new Error('文件无法读取');
    const text = await response.text();
    const pre = document.createElement('pre');
    pre.textContent = text.length > 40000 ? `${text.slice(0, 40000)}\n\n（预览已截断）` : text;
    container.replaceChildren(pre);
  } catch (error) { container.textContent = `预览不可用：${error.message}`; }
}

async function openFile(path) {
  const dialog = $('#file-dialog');
  $('#file-title').textContent = path;
  const body = $('#file-body'); body.replaceChildren();
  const url = fileUrl(path);
  dialog.showModal();
  const prefs = resultPreferences();
  prefs.views[path] = Date.now();
  const recent = Object.entries(prefs.views).sort((a, b) => b[1] - a[1]).slice(0, 100);
  prefs.views = Object.fromEntries(recent);
  try { localStorage.setItem(preferenceKey(), JSON.stringify(prefs)); } catch { /* Opening files does not depend on browser storage. */ }
  if (/\.pdf$/i.test(path)) { const viewer = document.createElement('div'); body.append(viewer); renderPdf(viewer, path); }
  else if (/\.(docx|xlsx|csv)$/i.test(path)) { const viewer = document.createElement('div'); body.append(viewer); renderDocument(viewer, path); }
  else if (/\.(png|jpe?g)$/i.test(path)) { body.append(previewImage(path, path)); }
  else {
    const pre = document.createElement('pre');
    pre.textContent = '正在读取文件…';
    body.append(pre);
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error('文件不存在或无法读取');
      const text = await response.text();
      pre.textContent = text.length > 40000 ? `${text.slice(0, 40000)}\n\n（预览已截断）` : text;
      if (text.length > 40000) {
        const expand = document.createElement('button');
        expand.className = 'row-action';
        expand.textContent = '展开完整内容';
        expand.addEventListener('click', () => { pre.textContent = text; expand.remove(); }, { once: true });
        pre.after(expand);
      }
    } catch (error) {
      pre.textContent = `文件预览不可用：${error.message}`;
    }
  }
}

document.addEventListener('click', (event) => {
  const page = event.target.closest('[data-page]');
  const role = event.target.closest('[data-role]');
  const file = event.target.closest('[data-file]');
  const close = event.target.closest('[data-close]');
  const project = event.target.closest('[data-project-path]');
  const copyPath = event.target.closest('[data-copy-path]');
  const copyFile = event.target.closest('[data-copy-file]');
  const node = event.target.closest('[data-node]');
  const resultTabButton = event.target.closest('[data-result-tab]');
  const pin = event.target.closest('[data-result-pin]');
  const question = event.target.closest('[data-question]');
  const roleSelection = event.target.closest('[data-select-role]');
  const catalogSelection = event.target.closest('[data-catalog-select]');
  const directorySelection = event.target.closest('[data-library-directory]');
  const skillSelection = event.target.closest('[data-select-skill]');
  const deliverySelection = event.target.closest('[data-delivery-file]');
  if (page) { if (current !== page.dataset.page) catalogQuery = ''; current = page.dataset.page; closeMobileNav(); render(); }
  if (node) openNode(node.dataset.node);
  if (question) { const y = window.scrollY; selectedQuestion = question.dataset.question; render(); [...document.querySelectorAll('[data-question]')].find(item => item.dataset.question === selectedQuestion)?.focus({preventScroll: true}); window.scrollTo(0, y); }
  if (roleSelection) { const y = window.scrollY; selectedRole = roleSelection.dataset.selectRole; render(); [...document.querySelectorAll('[data-select-role]')].find(item => item.dataset.selectRole === selectedRole)?.focus({preventScroll: true}); window.scrollTo(0, y); }
  if (catalogSelection) { const y = window.scrollY; if (catalogSelection.dataset.catalogKind === 'library') selectedLibraryFile = catalogSelection.dataset.catalogSelect; else selectedArtifact = catalogSelection.dataset.catalogSelect; render(); [...document.querySelectorAll('[data-catalog-select]')].find(item => item.dataset.catalogSelect === catalogSelection.dataset.catalogSelect)?.focus({preventScroll: true}); window.scrollTo(0, y); }
  if (directorySelection) { libraryDirectory = directorySelection.dataset.libraryDirectory; catalogQuery = ''; selectedLibraryFile = null; render(); }
  if (skillSelection) { const y = window.scrollY; selectedSkill = skillSelection.dataset.selectSkill; render(); [...document.querySelectorAll('[data-select-skill]')].find(item => item.dataset.selectSkill === selectedSkill)?.focus({preventScroll: true}); window.scrollTo(0, y); }
  if (deliverySelection) { const y = window.scrollY; selectedDeliveryFile = deliverySelection.dataset.deliveryFile; render(); [...document.querySelectorAll('[data-delivery-file]')].find(item => item.dataset.deliveryFile === selectedDeliveryFile)?.focus({preventScroll: true}); window.scrollTo(0, y); }
  if (resultTabButton) { resultTab = resultTabButton.dataset.resultTab; resultExpanded = false; render(); document.querySelector(`[data-result-tab="${resultTab}"]`)?.focus(); }
  if (pin) { const prefs = resultPreferences(); const path = pin.dataset.resultPin; prefs.pins = prefs.pins.includes(path) ? prefs.pins.filter(item => item !== path) : [...prefs.pins, path]; if (saveResultPreferences(prefs)) { render(); [...document.querySelectorAll('[data-result-pin]')].find(item => item.dataset.resultPin === path)?.focus(); } }
  if (event.target.closest('[data-result-expand]')) { resultExpanded = true; render(); }
  if (event.target.closest('[data-result-collapse]')) { resultExpanded = false; render(); }
  if (event.target.closest('[data-result-clear-views]')) { const prefs = resultPreferences(); prefs.views = {}; if (saveResultPreferences(prefs)) render(); }
  if (event.target.closest('[data-result-clear-pins]')) { const prefs = resultPreferences(); prefs.pins = []; if (saveResultPreferences(prefs)) render(); }
  if (role || event.target.closest('#add-role')) { $('#role-name').value = role?.dataset.role || ''; $('#thread-id').value = ''; $('#role-dialog').showModal(); }
  if (file) openFile(file.dataset.file).catch((error) => alert(error.message));
  if (close) {
    const dialog = document.getElementById(close.dataset.close);
    if (dialog.id === 'node-dialog') closeNodeDrawer();
    else dialog.close();
  }
  if (project) switchProject(project.dataset.projectPath, false);
  if (copyPath) {
    const separator = state.project.includes('\\') ? '\\' : '/';
    const fullPath = state.project.replace(/[\\/]+$/, '') + separator + copyPath.dataset.copyPath.replace(/[\\/]/g, separator);
    if (!navigator.clipboard) alert(`请手动使用此路径：\n${fullPath}`);
    else navigator.clipboard.writeText(fullPath).then(() => { copyPath.textContent = '已复制'; }).catch(() => alert(`无法复制，请手动使用此路径：\n${fullPath}`));
  }
  if (copyFile) {
    if (!navigator.clipboard) { alert('当前浏览器无法复制，请打开提示词后手动复制。'); return; }
    fetch(fileUrl(copyFile.dataset.copyFile)).then(async response => { if (!response.ok) throw new Error('文件不可读取'); return response.text(); }).then(text => navigator.clipboard.writeText(text)).then(() => { copyFile.textContent = '已复制，请手动转交'; }).catch(error => alert(`复制失败：${error.message}`));
  }
});
document.addEventListener('change', event => { if (event.target.id === 'result-category') { resultCategory = event.target.value; resultExpanded = false; render(); } else if (event.target.id === 'artifact-stage') { artifactStage = event.target.value; render(); } });
function closeNodeDrawer() {
  const dialog = $('#node-dialog');
  if (!dialog.open || dialog.classList.contains('is-closing')) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { dialog.close(); return; }
  dialog.classList.add('is-closing');
  let timer;
  const finish = () => { clearTimeout(timer); dialog.removeEventListener('animationend', onEnd); dialog.classList.remove('is-closing'); if (dialog.open) dialog.close(); };
  const onEnd = event => { if (event.target === dialog && event.animationName === 'drawer-out') finish(); };
  dialog.addEventListener('animationend', onEnd);
  timer = setTimeout(finish, 350);
}
$('#node-dialog').addEventListener('cancel', event => { event.preventDefault(); closeNodeDrawer(); });
$('#node-dialog').addEventListener('click', event => {
  if (event.target !== event.currentTarget) return;
  const bounds = event.currentTarget.getBoundingClientRect();
  if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) closeNodeDrawer();
});
$('#node-dialog').addEventListener('close', () => { if (current === 'overview') { render(); [...document.querySelectorAll('[data-node]')].find(item => item.dataset.node === contextNode)?.focus(); } });
$('#file-dialog').addEventListener('close', () => { if (current === 'overview' && !$('#node-dialog').open) render(); });
document.addEventListener('input', (event) => {
  if (event.target.matches('[data-catalog-search]')) {
    catalogQuery = event.target.value.toLowerCase().trim();
    const rows = [...document.querySelectorAll('[data-catalog-row]')];
    rows.forEach(row => { row.hidden = !row.dataset.catalogText.includes(catalogQuery); });
    const message = document.querySelector('.catalog-no-match');
    if (message) message.hidden = rows.some(row => !row.hidden) || !rows.length;
    return;
  }
  if (event.target.matches('[data-question-search]')) {
    questionQuery = event.target.value.toLowerCase().trim();
    const options = [...document.querySelectorAll('[data-question-search-text]')];
    options.forEach(item => { item.hidden = !item.dataset.questionSearchText.includes(questionQuery); });
    $('.question-no-match').hidden = options.some(item => !item.hidden);
    return;
  }
  if (!event.target.matches('[data-file-search]')) return;
  const query = event.target.value.toLowerCase().trim();
  const card = event.target.closest('.card');
  const items = [...card.querySelectorAll('[data-search-text]')];
  items.forEach(item => { item.hidden = !item.dataset.searchText.includes(query); });
  card.querySelector('.file-no-match').hidden = items.some(item => !item.hidden);
});
const projectStorageKey = 'harness-workbench-saved-projects';
function savedProjects() {
  try {
    const saved = JSON.parse(localStorage.getItem(projectStorageKey) || '[]');
    return Array.isArray(saved) ? saved.filter(p => p && typeof p.path === 'string' && typeof p.name === 'string') : [];
  } catch { return []; }
}
function showProjects() {
  const query = $('#project-search').value.trim().toLowerCase();
  const unique = new Map();
  for (const project of [...(state?.available_projects || []), ...savedProjects()]) {
    if (typeof project.path === 'string' && typeof project.name === 'string') unique.set(project.path.toLowerCase().replace(/[\\/]+$/, ''), project);
  }
  const matches = [...unique.values()].filter(p => `${p.name} ${p.path}`.toLowerCase().includes(query));
  $('#project-candidates').innerHTML = matches.length ? matches.map(p => `<button type="button" class="project-candidate" data-project-path="${esc(p.path)}"><b>${esc(p.name)}</b>${p.path === state?.project ? '<span>当前项目</span>' : '<span>打开 ›</span>'}<small>${esc(p.path)}</small></button>`).join('') : '<div class="empty">没有匹配的项目，可在下方添加已有项目目录。</div>';
}
async function switchProject(path, remember) {
  const generation = ++switchGeneration;
  const error = $(remember ? '#project-error' : '#project-search-error');
  error.hidden = true;
  let saveFailed = false;
  let sessionSaveFailed = false;
  try {
    if (!path.trim()) throw new Error('请填写已有项目目录');
    await post('/api/project', { path: path.trim() });
    if (generation !== switchGeneration) return;
    if (remember) {
      const saved = savedProjects().filter(p => p.path.toLowerCase().replace(/[\\/]+$/, '') !== path.trim().toLowerCase().replace(/[\\/]+$/, ''));
      saved.push({ name: path.trim().replace(/[\\/]+$/, '').split(/[\\/]/).pop(), path: path.trim() });
      try { localStorage.setItem(projectStorageKey, JSON.stringify(saved)); }
      catch { saveFailed = true; }
    }
    selectedProjectInMemory = path.trim();
    try { sessionStorage.setItem('harness-workbench-project', selectedProjectInMemory); }
    catch { sessionSaveFailed = true; }
    if ($('#project-dialog').open) $('#project-dialog').close();
    closeProjectSearch();
    $('#project-search').value = '';
    await refresh();
    if (generation === switchGeneration && (saveFailed || sessionSaveFailed)) alert('浏览器无法保存项目选择；刷新页面后可能需要重新选择或添加。');
  } catch (err) { if (generation === switchGeneration) { error.textContent = err.message; error.hidden = false; } }
}
function closeProjectSearch() { $('#project-search-panel').hidden = true; $('#project-search').setAttribute('aria-expanded', 'false'); }
$('#project-search').addEventListener('focus', () => {
  $('#project-search-error').hidden = true; showProjects();
  $('#project-search-panel').hidden = false; $('#project-search').setAttribute('aria-expanded', 'true');
});
$('#add-project').addEventListener('click', () => { closeProjectSearch(); $('#project-path').value = ''; $('#project-error').hidden = true; $('#project-dialog').showModal(); });
document.addEventListener('click', event => { if (!event.target.closest('.project-search-wrap')) closeProjectSearch(); });
document.addEventListener('keydown', event => { if (event.key === 'Escape' && !$('#project-search-panel').hidden) { closeProjectSearch(); $('#project-search').blur(); } });
document.addEventListener('keydown', event => { if (event.key === 'Escape' && $('.sidebar').classList.contains('mobile-open')) { closeMobileNav(); $('#nav-toggle').focus(); } });
$('#project-search').addEventListener('input', showProjects);
$('#project-search').addEventListener('keydown', event => { if (event.key === 'Enter') event.preventDefault(); });
$('#refresh').addEventListener('click', refresh);
$('#project-form').addEventListener('submit', (event) => { event.preventDefault(); switchProject($('#project-path').value, true); });
$('#role-form').addEventListener('submit', async (event) => { event.preventDefault(); try { await post('/api/role-link', { project: state.project, role: $('#role-name').value, thread_id: $('#thread-id').value }); $('#role-dialog').close(); await refresh(); } catch (error) { alert(error.message); } });
setInterval(checkSync, 10000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) checkSync(); });
refresh();
