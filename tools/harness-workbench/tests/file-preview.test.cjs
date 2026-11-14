const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function createPreview(fetch) {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const start = source.indexOf('async function openFile(path)');
  const end = source.indexOf("\ndocument.addEventListener('click'", start);
  assert.ok(start >= 0 && end > start);
  const body = { children: [], replaceChildren() { this.children = []; }, append(item) { this.children.push(item); } };
  const dialog = { open: false, showModal() { this.open = true; } };
  const title = {};
  const context = {
    $: selector => ({ '#file-dialog': dialog, '#file-title': title, '#file-body': body })[selector],
    document: { createElement: () => ({ textContent: '' }) },
    fileUrl: value => value,
    fetch,
    resultPreferences: () => ({ views: {} }),
    preferenceKey: () => 'preferences',
    localStorage: { setItem() {} },
  };
  vm.runInNewContext(source.slice(start, end), context);
  return { context, body, dialog };
}

test('text preview reports missing files and network errors', async () => {
  for (const fetch of [async () => ({ ok: false }), async () => { throw new Error('离线'); }]) {
    const { context, body, dialog } = createPreview(fetch);
    await context.openFile('missing.md');
    assert.equal(dialog.open, true);
    assert.match(body.children[0].textContent, /文件预览不可用/);
  }
});

test('text preview shows successfully loaded content', async () => {
  const { context, body } = createPreview(async () => ({ ok: true, text: async () => '已有内容' }));
  await context.openFile('paper.md');
  assert.equal(body.children[0].textContent, '已有内容');
});

test('view history stays with the original project while a file is loading', async () => {
  let finish;
  const pending = new Promise(resolve => { finish = resolve; });
  const { context } = createPreview(() => pending);
  let project = 'project-a';
  const saved = {};
  context.preferenceKey = () => project;
  context.localStorage = { setItem(key, value) { saved[key] = JSON.parse(value); } };
  const preview = context.openFile('paper.md');
  project = 'project-b';
  finish({ ok: true, text: async () => 'content' });
  await preview;
  assert.ok(saved['project-a'].views['paper.md']);
  assert.equal(saved['project-b'], undefined);
});
