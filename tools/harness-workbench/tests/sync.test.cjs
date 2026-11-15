const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

test('a delayed bootstrap cannot replace a project loaded by a newer refresh', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const start = source.indexOf('async function refresh()');
  const end = source.indexOf('\nfunction syncStatus(', start);
  assert.ok(start >= 0 && end > start);

  let resolveBootstrap;
  let bootstrapStarted;
  const started = new Promise(resolve => { bootstrapStarted = resolve; });
  const bootstrap = new Promise(resolve => { resolveBootstrap = resolve; });
  let stateRequests = 0;
  const elements = {
    '#error': { hidden: true, textContent: '' },
    '#content': { innerHTML: '' },
    '#project-search-panel': { hidden: true },
  };
  const context = {
    syncGeneration: 0, syncSnapshot: '', syncCandidate: '', state: null,
    selectedProjectPath: () => '',
    $: selector => elements[selector],
    syncStatus() {}, render() {}, showProjects() {},
    fetch: async url => {
      if (url === '/api/bootstrap') { bootstrapStarted(); return bootstrap; }
      stateRequests += 1;
      if (stateRequests === 1) return { ok: false, json: async () => ({ error: '暂时无法读取' }) };
      return { ok: true, json: async () => ({ project: 'project-b', available_projects: [] }) };
    },
  };
  vm.runInNewContext(source.slice(start, end), context);
  const first = context.refresh();
  await started;
  await context.refresh();
  assert.equal(context.state.project, 'project-b');
  resolveBootstrap({ ok: true, json: async () => ({ available_projects: [] }) });
  await first;
  assert.equal(context.state.project, 'project-b');
  assert.equal(elements['#error'].hidden, true);
});

test('bootstrap still supplies project choices when the initial refresh fails', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const start = source.indexOf('async function refresh()');
  const end = source.indexOf('\nfunction syncStatus(', start);
  assert.ok(start >= 0 && end > start);
  const elements = {
    '#error': { hidden: true, textContent: '' },
    '#content': { innerHTML: '' },
    '#project-search-panel': { hidden: true },
  };
  const context = {
    syncGeneration: 0, state: null, selectedProjectPath: () => '',
    $: selector => elements[selector], syncStatus() {}, showProjects() {},
    fetch: async url => url === '/api/bootstrap'
      ? { ok: true, json: async () => ({ available_projects: [{ name: '示例', path: 'example' }] }) }
      : { ok: false, json: async () => ({ error: '暂时无法读取' }) },
  };
  vm.runInNewContext(source.slice(start, end), context);
  await context.refresh();
  assert.equal(context.state.project, '');
  assert.equal(context.state.available_projects[0].name, '示例');
  assert.equal(elements['#error'].hidden, false);
});

test('automatic sync recovers a failed refresh without hiding a different project failure', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const refreshStart = source.indexOf('async function refresh()');
  const refreshEnd = source.indexOf('\nfunction syncStatus(', refreshStart);
  const syncStart = source.indexOf('async function checkSync()');
  const syncEnd = source.indexOf('\nasync function post(', syncStart);
  assert.ok(refreshStart >= 0 && refreshEnd > refreshStart && syncStart >= 0 && syncEnd > syncStart);

  for (const selection of ['project-a', 'project-b']) {
    const state = { project: 'project-a', available_projects: [] };
    const elements = {
      '#error': { hidden: true, textContent: '' },
      '#content': { innerHTML: '' },
      '#project-search-panel': { hidden: true },
    };
    let requests = 0;
    const context = {
      syncGeneration: 0, syncSnapshot: JSON.stringify(state), syncCandidate: '',
      syncBusy: false, loadedSelection: 'project-a', refreshFailed: false, state,
      selectedProjectPath: () => selection, document: { hidden: false },
      $: selector => elements[selector], syncStatus() {}, render() {},
      fetch: async () => {
        requests += 1;
        return requests === 1
          ? { ok: false, json: async () => ({ error: '暂时无法读取' }) }
          : { ok: true, json: async () => state };
      },
    };
    vm.runInNewContext(source.slice(refreshStart, refreshEnd) + source.slice(syncStart, syncEnd), context);
    await context.refresh();
    assert.equal(elements['#error'].hidden, false);
    await context.checkSync();
    assert.equal(elements['#error'].hidden, selection === 'project-a');
    assert.equal(requests, selection === 'project-a' ? 2 : 1);
    assert.equal(context.state.project, 'project-a');
  }
});
