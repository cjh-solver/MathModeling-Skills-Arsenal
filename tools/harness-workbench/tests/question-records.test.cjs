const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { QuestionLabels } = require('../static/ranking.js');

function renderQuestion(question, questionSources = {}) {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const start = source.indexOf('function questionPage()');
  const end = source.indexOf('\nfunction ', start + 20);
  assert.ok(start >= 0 && end > start);
  const statusNames = source.split('\n').find(line => line.startsWith('const statusNames ='));
  const context = {
    state: { question_views: [{ id: 'Q1', ...question }], question_sources: questionSources }, selectedQuestion: null, questionQuery: '',
    QuestionLabels, icon: () => '', empty: value => value, fileIcon: () => '', fileDisplayName: value => value,
    fileLink: value => value, display: value => value == null ? '未登记' : typeof value === 'string' ? value : JSON.stringify(value),
    esc: value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;'),
  };
  vm.runInNewContext(`${statusNames}\n${source.slice(start, end)}`, context);
  return context.questionPage();
}

test('current model cards expose model details without manufacturing a numeric result', () => {
  const html = renderQuestion({
    objective: '降低成本',
    models: [{ id: 'Q1-final-model', purpose: '满足需求', result: null, formulation: { expression: 'min c*x' }, solver_interface: { method: 'LP' } }],
    interpretations: [{ fact: '成本为 42 元', meaning: '满足需求', boundary: '测试范围', verification: 'draft' }],
  });
  assert.match(html, /模型与求解接口/);
  assert.match(html, /min c\*x/);
  assert.match(html, /求解方法：LP/);
  assert.match(html, /成本为 42 元/);
  assert.match(html, /状态：草稿/);
  assert.doesNotMatch(html, /结果：未登记/);
  assert.doesNotMatch(html, /记录为已核验/);
});

test('question records escape file content and retain a real zero result', () => {
  const html = renderQuestion({
    models: [{ id: 'legacy', result: 0 }, { id: 'current', purpose: '<script>bad()</script>', formulation: { expression: '<img src=x onerror=bad()>' } }],
    interpretations: [{ fact: '<b>42</b>', verification: 'verified' }],
  });
  assert.match(html, /结果：0/);
  assert.match(html, /&lt;script&gt;bad\(\)&lt;\/script&gt;/);
  assert.match(html, /&lt;img src=x onerror=bad\(\)&gt;/);
  assert.match(html, /&lt;b&gt;42&lt;\/b&gt;/);
  assert.match(html, /记录为已核验/);
  assert.doesNotMatch(html, /<script>|<img src=x|<b>42<\/b>/);
});

test('detached verification remains a source record without promoting a draft', () => {
  const html = renderQuestion({ interpretations: [{ fact: '合成结果', verification: 'draft' }] },
    { verification: '核验/H6.yaml' });
  assert.match(html, /H6 核验记录：核验\/H6.yaml/);
  assert.match(html, /状态：草稿/);
  assert.doesNotMatch(html, /记录为已核验/);
});

test('verification source errors are escaped and absent records add no empty row', () => {
  assert.doesNotMatch(renderQuestion({}), /H6 核验记录：/);
  const html = renderQuestion({}, { verification: 'H6.yaml', verification_error: '<unreadable>' });
  assert.match(html, /&lt;unreadable&gt;/);
  assert.doesNotMatch(html, /<unreadable>/);
});
