const test = require('node:test');
const assert = require('node:assert/strict');
const ranking = require('../static/ranking.js');

const state = {
  files: [
    { path: 'paper.pdf', modified: 1 },
    { path: 'review.yaml', modified: 2 },
    { path: 'verify.csv', modified: 3 },
    { path: 'other.json', modified: 4 },
    { path: 'figure.png', modified: 5 },
  ],
  paper_pdf: 'paper.pdf',
  figures: [{ png: 'figure.png' }],
  nodes: [
    { id: 'H9', status: 'review_pending', review: 'review.yaml' },
    { id: 'H6', status: 'approved', evidence: { artifacts: [{ path: 'verify.csv' }] } },
  ],
  approvals: [], reports: [],
};

test('pins and recorded pending take precedence over context and recency', () => {
  const items = ranking.build(state, { pins: ['paper.pdf'], views: { 'other.json': 100 } }, 'H6');
  assert.deepEqual(items.slice(0, 3).map(item => item.path), ['paper.pdf', 'review.yaml', 'verify.csv']);
  assert.match(items[1].reasons[0], /待处理/);
  assert.match(items[2].reasons[0], /H6/);
});

test('changed approval evidence is prioritized without inferring approval', () => {
  const modified = { ...state, nodes: [{ id: 'H7', status: 'approved', review: 'review.yaml' }], approvals: [{ gate: 'H7', digests: { status: 'issues', files: [{ path: 'figure.png', status: 'changed' }] } }] };
  const items = ranking.build(modified);
  assert.equal(items.find(item => item.path === 'figure.png').tier, 4);
  assert.match(items.find(item => item.path === 'figure.png').reasons[0], /待核/);
});

test('recorded review artifacts of a pending node are prioritized when the review file is not listed', () => {
  const data = {
    files: [{ path: 'evidence.pdf', modified: 1 }, { path: 'unrelated.txt', modified: 100 }],
    nodes: [{ id: 'H6', status: 'review_pending', review: 'review.yaml', evidence: { artifacts: [{ path: 'evidence.pdf' }] } }],
  };
  const items = ranking.build(data);
  assert.equal(items[0].path, 'evidence.pdf');
  assert.equal(items[0].tier, 4);
  assert.match(items[0].reasons[0], /H6 节点记录待处理/);
  data.nodes[0].status = 'approved';
  assert.equal(ranking.build(data).find(item => item.path === 'evidence.pdf').tier, 0);
});

test('evidence gaps and stale records receive attention without treating frozen records as pending', () => {
  const modified = {
    files: [{ path: 'gap.yaml' }, { path: 'stale.yaml' }, { path: 'frozen.yaml' }],
    nodes: [
      { id: 'H5', status: 'evidence_gap', review: 'gap.yaml' },
      { id: 'H6', status: 'stale', review: 'stale.yaml' },
      { id: 'H7', status: 'frozen', review: 'frozen.yaml' },
    ],
  };
  const items = ranking.build(modified);
  assert.equal(items.find(item => item.path === 'gap.yaml').tier, 4);
  assert.equal(items.find(item => item.path === 'stale.yaml').tier, 4);
  assert.notEqual(items.find(item => item.path === 'frozen.yaml').tier, 4);
  assert.equal(ranking.needsAttention('evidence_gap'), true);
  assert.equal(ranking.needsAttention('stale'), true);
  assert.equal(ranking.needsAttention('frozen'), false);
});

test('categories distinguish recorded associations from file type inference', () => {
  const items = ranking.build(state);
  assert.equal(items.find(item => item.path === 'paper.pdf').categorySource, '项目登记');
  assert.equal(items.find(item => item.path === 'verify.csv').categorySource, '按文件类型');
  assert.deepEqual(items.find(item => item.path === 'other.json').categories, ['其他']);
  assert.equal(ranking.build({ files: [] }).length, 0);
});

test('stage filters use recorded file references only', () => {
  const items = ranking.build(state);
  assert.deepEqual(items.find(item => item.path === 'review.yaml').nodes, ['H9']);
  assert.deepEqual(items.find(item => item.path === 'verify.csv').nodes, ['H6']);
  assert.deepEqual(items.find(item => item.path === 'figure.png').nodes, []);
});

test('diversification never moves lower priority above pinned or urgent files', () => {
  const items = ranking.diverse(ranking.build(state, { pins: ['paper.pdf'] }, 'H6'));
  assert.deepEqual(items.slice(0, 3).map(item => item.tier), [5, 4, 3]);
});

test('TSV tables are categorized as data files', () => {
  const items = ranking.build({ files: [{ path: 'results.TSV', modified: 1 }] });
  assert.deepEqual(items[0].categories, ['数据与代码']);
});
