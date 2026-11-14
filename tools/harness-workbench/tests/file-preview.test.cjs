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

test('failed image preview shows a readable error', () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const start = source.indexOf('function previewImage(path, alt)');
  const end = source.indexOf('\nasync function renderCatalogPreview', start);
  assert.ok(start >= 0 && end > start);
  let replacement;
  const context = {
    document: { createElement: () => ({ addEventListener(_event, callback) { this.fail = callback; }, replaceWith(element) { replacement = element; } }) },
    fileUrl: value => value,
  };
  vm.runInNewContext(source.slice(start, end), context);
  const image = context.previewImage('figure.png', '图表');
  image.fail();
  assert.match(replacement.textContent, /图片无法读取/);
});

test('PDF page errors are visible and another page can be tried', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const start = source.indexOf('async function renderPdf(');
  const end = source.indexOf('\nasync function renderDocument(', start);
  assert.ok(start >= 0 && end > start);
  const element = () => ({ addEventListener(type, callback) { this[type] = callback; } });
  const image = element(), label = {}, previous = element(), next = element(), error = { hidden: true };
  const elements = { img: image, '.pdf-toolbar span': label, '.pdf-previous': previous, '.pdf-next': next, '.pdf-page-error': error };
  const container = { querySelector: selector => elements[selector] };
  const context = { state: { project: 'project' }, fetch: async () => ({ ok: true, json: async () => ({ pages: 2 }) }) };
  vm.runInNewContext(source.slice(start, end), context);
  await context.renderPdf(container, 'paper.pdf');
  image.error();
  assert.equal(image.hidden, true);
  assert.equal(error.hidden, false);
  next.click();
  assert.equal(error.hidden, true);
  assert.equal(image.hidden, false);
  assert.match(image.src, /page=2$/);
});

test('Word preview preserves the order of paragraphs and tables', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const start = source.indexOf('async function renderDocument(');
  const end = source.indexOf('\nfunction previewImage(', start);
  assert.ok(start >= 0 && end > start);
  const context = {
    state: { project: 'project' },
    esc: text => String(text),
    fetch: async () => ({ ok: true, json: async () => ({
      type: 'docx', note: 'preview',
      blocks: [
        { type: 'paragraph', text: 'first paragraph' },
        { type: 'table', rows: [['table value']] },
        { type: 'paragraph', text: 'last paragraph' },
      ],
    }) }),
  };
  vm.runInNewContext(source.slice(start, end), context);
  const container = {};
  await context.renderDocument(container, 'sample.docx');
  assert.ok(container.innerHTML.indexOf('first paragraph') < container.innerHTML.indexOf('table value'));
  assert.ok(container.innerHTML.indexOf('table value') < container.innerHTML.indexOf('last paragraph'));
});

test('file search explains when there are no matches and clears the message', () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  assert.match(source, /class="file-no-match" hidden/);
  const start = source.indexOf("document.addEventListener('input',");
  const end = source.indexOf("\nconst projectStorageKey", start);
  assert.ok(start >= 0 && end > start);
  let handler;
  const items = [{ dataset: { searchText: 'paper.tex 论文' }, hidden: false }];
  const message = { hidden: true };
  const card = { querySelectorAll: () => items, querySelector: () => message };
  const context = { document: { addEventListener(_type, callback) { handler = callback; } } };
  vm.runInNewContext(source.slice(start, end), context);
  const input = { value: 'missing', matches: selector => selector === '[data-file-search]', closest: () => card };
  handler({ target: input });
  assert.equal(items[0].hidden, true);
  assert.equal(message.hidden, false);
  input.value = '';
  handler({ target: input });
  assert.equal(items[0].hidden, false);
  assert.equal(message.hidden, true);
});

test('a project can be opened when persistent browser storage is unavailable', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const start = source.indexOf('async function switchProject(');
  const end = source.indexOf('\nfunction closeProjectSearch(', start);
  assert.ok(start >= 0 && end > start);
  const errors = { '#project-error': {}, '#project-search-error': {} };
  const dialog = { open: false };
  const search = { value: 'query' };
  let selected, refreshed = false, warning = '';
  const context = {
    $: selector => ({ ...errors, '#project-dialog': dialog, '#project-search': search })[selector],
    post: async () => {}, savedProjects: () => [], projectStorageKey: 'projects',
    selectedProjectInMemory: null,
    localStorage: { setItem() { throw new Error('storage unavailable'); } },
    sessionStorage: { setItem(_key, value) { selected = value; } },
    closeProjectSearch() {}, refresh: async () => { refreshed = true; },
    alert: message => { warning = message; },
  };
  vm.runInNewContext(source.slice(start, end), context);
  await context.switchProject('C:\\Contest', true);
  assert.equal(selected, 'C:\\Contest');
  assert.equal(refreshed, true);
  assert.match(warning, /无法保存项目选择/);
  assert.equal(errors['#project-error'].hidden, true);
});

test('blocked session storage keeps the current project in memory', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const helperStart = source.indexOf('function selectedProjectPath()');
  const helperEnd = source.indexOf('\nconst $ =', helperStart);
  const switchStart = source.indexOf('async function switchProject(');
  const switchEnd = source.indexOf('\nfunction closeProjectSearch(', switchStart);
  assert.ok(helperStart >= 0 && helperEnd > helperStart && switchStart >= 0 && switchEnd > switchStart);
  const error = {}, dialog = { open: false }, search = {};
  let loadedProject, warning = '';
  const context = {
    selectedProjectInMemory: null,
    $: selector => ({ '#project-error': error, '#project-dialog': dialog, '#project-search': search })[selector],
    post: async () => {}, savedProjects: () => [], projectStorageKey: 'projects',
    localStorage: { setItem() {} },
    sessionStorage: { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); } },
    closeProjectSearch() {}, refresh: async () => { loadedProject = context.selectedProjectPath(); },
    alert: message => { warning = message; },
  };
  vm.runInNewContext(source.slice(helperStart, helperEnd) + source.slice(switchStart, switchEnd), context);
  assert.equal(context.selectedProjectPath(), null);
  await context.switchProject('C:\\Contest', true);
  assert.equal(loadedProject, 'C:\\Contest');
  assert.match(warning, /刷新页面后可能需要重新选择/);
  assert.equal(error.hidden, true);
});
