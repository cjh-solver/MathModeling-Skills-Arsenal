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
