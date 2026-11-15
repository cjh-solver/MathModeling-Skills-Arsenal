const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const textResponse = text => ({ ok: true, arrayBuffer: async () => Buffer.from(text, 'utf8') });

function createPreview(fetch) {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const start = source.indexOf('async function openFile(path)');
  const end = source.indexOf("\ndocument.addEventListener('click'", start);
  const decoderStart = source.indexOf('async function decodeTextPreview(response)');
  const decoderEnd = source.indexOf('\nasync function renderCatalogPreview(', decoderStart);
  assert.ok(start >= 0 && end > start && decoderStart >= 0 && decoderEnd > decoderStart);
  const body = { children: [], replaceChildren() { this.children = []; }, append(item) { this.children.push(item); } };
  const dialog = { open: false, showModal() { this.open = true; } };
  const title = {};
  const context = {
    $: selector => ({ '#file-dialog': dialog, '#file-title': title, '#file-body': body })[selector],
    document: { createElement: () => ({ textContent: '', addEventListener(type, callback) { this[type] = callback; }, remove() { this.removed = true; }, before(item) { const index = body.children.indexOf(this); if (index >= 0) body.children.splice(index, 0, item); }, after(item) { const index = body.children.indexOf(this); if (index >= 0) body.children.splice(index + 1, 0, item); } }) },
    fileUrl: value => value,
    fetch, TextDecoder,
    resultPreferences: () => ({ views: {} }),
    preferenceKey: () => 'preferences',
    localStorage: { setItem() {} },
  };
  vm.runInNewContext(source.slice(decoderStart, decoderEnd) + source.slice(start, end), context);
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
  const { context, body } = createPreview(async () => textResponse('已有内容'));
  await context.openFile('paper.md');
  assert.equal(body.children[0].textContent, '已有内容');
});

test('GB18030 text previews show the decoded text and an encoding notice', async () => {
  const bytes = Uint8Array.from([0xd6, 0xd0, 0xce, 0xc4]);
  const { context, body } = createPreview(async () => ({ ok: true, arrayBuffer: async () => bytes }));
  await context.openFile('notes.txt');
  assert.match(body.children[0].textContent, /GB18030.*核对/);
  assert.equal(body.children[1].textContent, '中文');
});

test('undecodable text reports an error instead of displaying replacement characters', async () => {
  const { context, body } = createPreview(async () => ({ ok: true, arrayBuffer: async () => Uint8Array.from([0xff]) }));
  await context.openFile('notes.txt');
  assert.match(body.children[0].textContent, /无法识别文本编码/);
});

test('catalog preview uses the same GB18030 fallback', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const start = source.indexOf('async function decodeTextPreview(response)');
  const end = source.indexOf('\nasync function openFile(', start);
  assert.ok(start >= 0 && end > start);
  const container = { children: [], replaceChildren(...items) { this.children = items; } };
  const context = {
    TextDecoder, document: { createElement: () => ({ textContent: '' }) },
    fileUrl: value => value, fetch: async () => ({ ok: true, arrayBuffer: async () => Uint8Array.from([0xd6, 0xd0, 0xce, 0xc4]) }),
  };
  vm.runInNewContext(source.slice(start, end), context);
  await context.renderCatalogPreview(container, 'notes.txt');
  assert.match(container.children[0].textContent, /GB18030/);
  assert.equal(container.children[1].textContent, '中文');
});

test('long text preview starts bounded and can be expanded', async () => {
  const text = 'x'.repeat(40001);
  const { context, body } = createPreview(async () => textResponse(text));
  await context.openFile('long.md');
  assert.match(body.children[0].textContent, /预览已截断/);
  assert.equal(body.children[1].textContent, '展开完整内容');
  body.children[1].click();
  assert.equal(body.children[0].textContent, text);
  assert.equal(body.children[1].removed, true);
});

test('a delayed long text preview does not change a newer preview', async () => {
  let finish;
  const pending = new Promise(resolve => { finish = resolve; });
  const { context, body } = createPreview(() => pending);
  const older = context.openFile('old.md');
  context.fetch = async () => textResponse('new content');
  await context.openFile('new.md');
  finish(textResponse('x'.repeat(40001)));
  await older;
  assert.equal(body.children.length, 1);
  assert.equal(body.children[0].textContent, 'new content');
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
  finish(textResponse('content'));
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
    selectedProjectInMemory: null, switchGeneration: 0,
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
    selectedProjectInMemory: null, switchGeneration: 0,
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

test('only the latest project choice applies when validation returns out of order', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  const start = source.indexOf('async function switchProject(');
  const end = source.indexOf('\nfunction closeProjectSearch(', start);
  assert.ok(start >= 0 && end > start);
  for (const failFirst of [false, true]) {
    const error = {}, dialog = { open: false }, search = {};
    let finishFirst, failFirstRequest, finishSecond, selected;
    const first = new Promise((resolve, reject) => { finishFirst = resolve; failFirstRequest = reject; });
    const second = new Promise(resolve => { finishSecond = resolve; });
    const context = {
      selectedProjectInMemory: null, switchGeneration: 0,
      $: selector => ({ '#project-search-error': error, '#project-dialog': dialog, '#project-search': search })[selector],
      post: (_url, body) => body.path === 'first' ? first : second,
      sessionStorage: { setItem(_key, value) { selected = value; } },
      closeProjectSearch() {}, refresh: async () => {}, alert() {},
    };
    vm.runInNewContext(source.slice(start, end), context);
    const older = context.switchProject('first', false);
    const newer = context.switchProject('second', false);
    finishSecond();
    await newer;
    if (failFirst) failFirstRequest(new Error('stale error')); else finishFirst();
    await older;
    assert.equal(selected, 'second');
    assert.equal(context.selectedProjectInMemory, 'second');
    assert.equal(error.hidden, true);
  }
});

test('selecting a question or role preserves the reading position', () => {
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  for (const [name, key] of [['question', 'question'], ['roleSelection', 'selectRole']]) {
    const line = source.split('\n').find(value => value.trimStart().startsWith(`if (${name}) {`));
    assert.ok(line);
    let focusOptions;
    const item = { dataset: { [key]: 'choice' }, focus(options) { focusOptions = options; } };
    const window = { scrollY: 350, scrollTo(_x, y) { this.scrollY = y; } };
    const context = {
      [name]: item, window, document: { querySelectorAll: () => [item] },
      selectedQuestion: null, selectedRole: null,
      render() { window.scrollY = 0; },
    };
    vm.runInNewContext(line, context);
    assert.equal(window.scrollY, 350);
    assert.equal(focusOptions.preventScroll, true);
    assert.equal(context[name === 'question' ? 'selectedQuestion' : 'selectedRole'], 'choice');
  }
});
