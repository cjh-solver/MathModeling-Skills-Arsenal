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
