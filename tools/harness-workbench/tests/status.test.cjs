const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { webcrypto, createHash } = require('node:crypto');
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
  const chapterStart = source.indexOf('function promptReady(');
  const chapterEnd = source.indexOf('\nfunction writingPlan(', chapterStart);
  assert.ok(gateStart >= 0 && gateEnd > gateStart && chapterStart >= 0 && chapterEnd > chapterStart);
  const state = { approvals: [], approval_error: null, chapters: [], visual_workflow: 'chapter_parallel' };
  const context = { state, fileIcon: () => '', fileLink: () => '', esc: String, empty: String };
  vm.runInNewContext(source.slice(gateStart, gateEnd) + source.slice(chapterStart, chapterEnd), context);
  const node = { id: 'H6', status: 'frozen' };
  assert.equal(context.gateNeedsReview(node), true);
  state.approvals = [{ gate: 'H6', decision: 'approved', digests: { status: 'matches' } }];
  assert.equal(context.gateNeedsReview(node), false);
  state.approval_error = '批准记录包含格式错误的条目';
  assert.equal(context.gateNeedsReview(node), true);
  state.chapters = [{ id: 'Q1', draft: 'q1.tex', draft_hash: 'matches', quality_review: 'quality.yaml', quality_hash: 'matches', review_packet: 'review.yaml', prompts: [{ path: 'prompt.md', sha256: 'a'.repeat(64), hash: 'matches', visual_plan_hash: 'matches' }] }];
  state.approvals.push({ gate: 'H7_CHAPTER:Q1', decision: 'approved', timestamp: '2026-11-14T12:00:00+08:00', digests: { status: 'matches', files: ['q1.tex', 'quality.yaml', 'review.yaml'].map(path => ({ path, status: 'matches' })) } });
  assert.doesNotMatch(context.chapterRows(), /data-copy-file/);
  assert.match(context.chapterRows(), /批准记录不完整，待核/);
  state.approval_error = null;
  assert.match(context.chapterRows(), /data-copy-file/);
  state.chapters[0].visuals_required = false;
  assert.doesNotMatch(context.chapterRows(), /data-copy-file/);
  assert.match(context.chapterRows(), /记录为无需图表，请核对提示词/);
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

test('copying a chapter prompt rechecks current approval and the exact bytes', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const readyStart = source.indexOf('function promptReady(');
  const readyEnd = source.indexOf('\nfunction chapterRows(', readyStart);
  const copyStart = source.indexOf('async function copyChapterPrompt(');
  const copyEnd = source.indexOf("\ndocument.addEventListener('click'", copyStart);
  assert.ok(readyStart >= 0 && readyEnd > readyStart && copyStart >= 0 && copyEnd > copyStart);
  const text = 'synthetic prompt';
  const hash = createHash('sha256').update(text).digest('hex');
  for (const scenario of ['valid', 'changed-file', 'revoked-before', 'revoked-after', 'project-changed', 'workflow-changed', 'wrong-project', 'visuals-cancelled', 'quality-changed', 'missing-review', 'invalid-timestamp']) {
    const prompt = { path: 'prompt.md', revision: 'r1', sha256: hash, hash: 'matches', visual_plan_hash: 'matches' };
    const chapter = { id: 'Q1', draft: 'q1.tex', draft_hash: 'matches', quality_review: 'quality.yaml', quality_hash: 'matches', review_packet: 'review.yaml', prompts: [prompt] };
    const approval = { gate: 'H7_CHAPTER:Q1', decision: 'approved', timestamp: '2026-11-14T12:00:00+08:00', digests: { status: 'matches', files: ['q1.tex', 'quality.yaml', 'review.yaml'].map(path => ({ path, status: 'matches' })) } };
    const snapshot = { project: 'project-a', visual_workflow: 'chapter_parallel', approval_error: null, approvals: [approval], chapters: [chapter] };
    const state = { project: 'project-a' };
    let snapshots = 0, copied = null;
    const context = {
      state, crypto: webcrypto, Uint8Array, TextDecoder,
      navigator: { clipboard: { writeText: async value => { copied = value; } } },
      fetch: async url => {
        if (url.startsWith('/api/state?')) {
          snapshots++;
          return { ok: true, json: async () => {
            if (scenario === 'revoked-before' || (scenario === 'revoked-after' && snapshots === 2)) return { ...snapshot, approval_error: '记录待核' };
            if (scenario === 'workflow-changed' && snapshots === 2) return { ...snapshot, visual_workflow: 'writer_first_draft' };
            if (scenario === 'wrong-project' && snapshots === 2) return { ...snapshot, project: 'project-b' };
            if (scenario === 'visuals-cancelled' && snapshots === 2) return { ...snapshot, chapters: [{ ...chapter, visuals_required: false }] };
            if (scenario === 'quality-changed' && snapshots === 2) return { ...snapshot, chapters: [{ ...chapter, quality_hash: 'issues' }] };
            if (scenario === 'missing-review' && snapshots === 2) return { ...snapshot, approvals: [{ ...approval, digests: { status: 'matches', files: approval.digests.files.slice(0, 2) } }] };
            if (scenario === 'invalid-timestamp' && snapshots === 2) return { ...snapshot, approvals: [{ ...approval, timestamp: '2026-11-14T12:00:00' }] };
            return snapshot;
          } };
        }
        if (scenario === 'project-changed') state.project = 'project-b';
        const bytes = new TextEncoder().encode(scenario === 'changed-file' ? 'changed prompt' : text);
        return { ok: true, arrayBuffer: async () => bytes.buffer };
      },
    };
    vm.runInNewContext(source.slice(readyStart, readyEnd) + source.slice(copyStart, copyEnd), context);
    const button = { dataset: { chapterId: 'Q1', copyFile: 'prompt.md' } };
    if (scenario === 'valid') {
      await context.copyChapterPrompt(button);
      assert.equal(copied, text);
      assert.equal(snapshots, 2);
    } else {
      await assert.rejects(context.copyChapterPrompt(button));
      assert.equal(copied, null, scenario);
    }
  }
});
