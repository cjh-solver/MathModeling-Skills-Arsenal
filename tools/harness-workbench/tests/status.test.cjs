const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ranking = require('../static/ranking.js');

test('overview and workflow surface stale and evidence-gap nodes', () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const lines = source.split('\n');
  const names = lines.find(line => line.startsWith('const statusNames ='));
  const status = lines.find(line => line.startsWith('const status ='));
  const trackerStart = source.indexOf('function tracker()');
  const trackerEnd = source.indexOf('\nfunction evidenceRows(', trackerStart);
  const overviewStart = source.indexOf('function overview()');
  const overviewEnd = source.indexOf('\nfunction approvalRow(', overviewStart);
  assert.ok(names && status && trackerStart >= 0 && trackerEnd > trackerStart && overviewStart >= 0 && overviewEnd > overviewStart);
  const context = {
    WorkbenchRanking: ranking, current: 'overview', contextNode: null,
    state: { nodes: [
      { id: 'H5', name: '建模', status: 'approved' },
      { id: 'H6', name: '验证', status: 'evidence_gap' },
      { id: 'H7', name: '图表', status: 'stale' },
    ], roles: [], reports: [] },
    esc: value => String(value), icon: () => '', head: () => '',
    gateNeedsReview: () => false, projectCard: () => '', resultPanel: () => '',
    roles: () => '', paperFigureSummary: () => '', empty: text => text,
  };
  vm.runInNewContext([names, status, source.slice(trackerStart, trackerEnd), source.slice(overviewStart, overviewEnd)].join('\n'), context);
  const overview = context.overview();
  assert.match(overview, /H6 · 验证/);
  assert.match(overview, /证据缺口/);
  assert.match(overview, /H7 · 图表/);
  assert.match(overview, /记录已过期/);
  assert.match(context.tracker(), /track-attention/);
  context.current = 'flow';
  assert.match(context.tracker(), /data-node="H6" aria-pressed="true"/);
});

test('frozen gates and chapter transfers remain conservative when approval records are invalid', () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const gateStart = source.indexOf('function gateNeedsReview(');
  const gateEnd = source.indexOf('\nfunction projectCard(', gateStart);
  const chapterStart = source.indexOf('function chapterRows(');
  const chapterEnd = source.indexOf('\nfunction writingPlan(', chapterStart);
  assert.ok(gateStart >= 0 && gateEnd > gateStart && chapterStart >= 0 && chapterEnd > chapterStart);
  const state = { approvals: [], approval_error: null, chapters: [] };
  const context = { state, fileIcon: () => '', fileLink: () => '', esc: String, empty: String };
  vm.runInNewContext(source.slice(gateStart, gateEnd) + source.slice(chapterStart, chapterEnd), context);
  const node = { id: 'H6', status: 'frozen' };
  assert.equal(context.gateNeedsReview(node), true);
  state.approvals = [{ gate: 'H6', decision: 'approved', digests: { status: 'matches' } }];
  assert.equal(context.gateNeedsReview(node), false);
  state.approval_error = '批准记录包含格式错误的条目';
  assert.equal(context.gateNeedsReview(node), true);
  state.chapters = [{ id: 'Q1', draft: 'q1.tex', draft_hash: 'matches', prompts: [{ path: 'prompt.md', hash: 'matches', visual_plan_hash: 'matches' }] }];
  state.approvals.push({ gate: 'H7_CHAPTER:Q1', decision: 'approved', digests: { status: 'matches', files: [{ path: 'q1.tex', status: 'matches' }] } });
  assert.doesNotMatch(context.chapterRows(), /data-copy-file/);
  assert.match(context.chapterRows(), /批准记录不完整，待核/);
  state.approval_error = null;
  assert.match(context.chapterRows(), /data-copy-file/);
});

test('readable approval entries remain visible alongside an incomplete-record warning', () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const start = source.indexOf('function approvalRecords(');
  const end = source.indexOf('\nfunction nodeContent(', start);
  assert.ok(start >= 0 && end > start);
  const context = {
    state: { approval_error: '批准记录包含格式错误的条目' },
    empty: String,
    approvalRow: item => `记录：${item.gate}`,
  };
  vm.runInNewContext(source.slice(start, end), context);
  const result = context.approvalRecords([{ gate: 'H6' }]);
  assert.match(result, /批准记录不完整或不可读取/);
  assert.match(result, /记录：H6/);
  assert.doesNotMatch(context.approvalRecords([]), /未找到批准记录/);
});
