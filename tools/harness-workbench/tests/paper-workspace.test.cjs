const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
const start = source.indexOf('function paperOutline(');
const end = source.indexOf('\nfunction literaturePage(', start);
assert.ok(start >= 0 && end > start);
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

function snapshot(overrides = {}) {
  return {
    project: 'project-a', visual_workflow: 'chapter_parallel',
    writing_plan: {path:'plan.yaml',hash:'matches',chapter_order:['abstract','analysis','Q1'],
      chapters:[{id:'analysis',title:'问题分析'},{id:'Q1',title:'配置模型'}]},
    chapters:[{id:'Q1',draft:'paper/Q1.tex',draft_available:true,draft_hash:'matches'},
      {id:'analysis',draft:'paper/分析.tex',draft_available:true,draft_hash:'matches'}],
    files:[{path:'paper/Q1.tex'},{path:'paper/分析.tex'}],
    figures:[],reports:[],literature:[],paper_source:null,paper_pdf:null,...overrides,
  };
}

function context(state = snapshot()) {
  const c = {state,selectedPaperItem:null,icon:()=>'',esc:escapeHtml,
    fileIcon:p=>'<i>'+escapeHtml(p)+'</i>',fileDisplayName:p=>p.split('/').pop(),
    fileLink:(p,label='查看')=>'<button data-file="'+escapeHtml(p)+'">'+label+'</button>',
    fileUrl:p=>p,empty:t=>'<p>'+escapeHtml(t)+'</p>',filePage:()=>'',writingPlan:()=>'',chapterRows:()=>''};
  vm.createContext(c);
  vm.runInContext(source.slice(start,end),c);
  return c;
}

test('paper outline follows reader order, retains empty chapters and appends extra records', () => {
  const state=snapshot();
  state.chapters.push({id:'extra',draft:'paper/extra.tex',draft_available:true});
  const before=JSON.stringify(state);
  const c=context(state), outline=c.paperOutline(state);
  assert.deepEqual(Array.from(outline.items,item=>item.id),['abstract','analysis','Q1','extra']);
  assert.equal(outline.items[2].title,'配置模型');
  assert.equal(outline.items[0].label,'未登记');
  assert.equal(outline.items[3].inPlan,false);
  assert.equal(JSON.stringify(state),before);
  assert.doesNotMatch(c.paperPage(),/已批准|已核验/);
});

test('stale or malformed plans fall back to recorded order without trusting changed titles', () => {
  for (const change of [{hash:'issues'},{error:'unreadable'},{chapter_order:['Q1','Q1']},{chapter_order:[{}]}]) {
    const state=snapshot();
    Object.assign(state.writing_plan,change);
    const c=context(state), outline=c.paperOutline(state);
    assert.deepEqual(Array.from(outline.items,item=>item.id),['Q1','analysis']);
    assert.ok(outline.warning);
    assert.equal(outline.items[0].title,'Q1');
  }
});

test('native chapter aliases stay readable while unknown IDs retain their exact names', () => {
  const state=snapshot({chapters:[],writing_plan:{hash:'matches',chapter_order:['modeling_q2','custom_method']}});
  const items=context(state).paperOutline(state).items;
  assert.equal(items[0].id,'modeling_q2');
  assert.equal(items[0].title,'问题 2 · 建模与求解');
  assert.equal(items[1].title,'custom_method');
});

test('registered chapter sources are previewed inline before a full PDF exists', () => {
  const c=context(snapshot({files:[],files_truncated:true}));
  const html=c.paperPage();
  assert.equal(c.selectedPaperItem,'chapter:analysis');
  assert.match(html,/data-preview-path="paper\/分析.tex"/);
  assert.doesNotMatch(html,/未找到已登记论文源文件的同名 PDF/);
  c.state=snapshot({chapters:[],paper_source:'paper/总稿.tex',paper_source_available:true,files:[]});
  c.selectedPaperItem=null;
  assert.match(c.paperPage(),/data-preview-path="paper\/总稿.tex"/);
});

test('PDF is the initial default while explicit chapter reading survives refreshed data', () => {
  const state=snapshot({paper_pdf:'paper/paper.pdf'});
  state.files.push({path:'paper/paper.pdf'});
  const c=context(state);
  assert.match(c.paperPage(),/id="paper-pdf"/);
  c.selectedPaperItem='chapter:Q1';
  assert.match(c.paperPage(),/data-preview-path="paper\/Q1.tex"/);
  c.state=JSON.parse(JSON.stringify(state));
  assert.match(c.paperPage(),/data-preview-path="paper\/Q1.tex"/);
  assert.equal(c.selectedPaperItem,'chapter:Q1');
});

test('duplicate chapter registration remains a visible conflict without choosing a draft', () => {
  const state=snapshot();
  state.chapters.push({...state.chapters[0],draft:'paper/other.tex'});
  const c=context(state), item=c.paperOutline(state).items.find(row=>row.id==='Q1');
  assert.equal(item.ambiguous,true);
  assert.equal(item.path,null);
  c.selectedPaperItem='chapter:Q1';
  const html=c.paperPage();
  assert.match(html,/登记冲突/);
  assert.match(html,/同一章节存在多份登记/);
  assert.doesNotMatch(html,/data-preview-path=/);
});

test('planned or missing chapters explain the empty reader without inventing content', () => {
  const c=context();
  c.selectedPaperItem='chapter:abstract';
  assert.match(c.paperPage(),/尚未登记本章正文/);
  c.state.chapters[0].draft_available=false;
  c.selectedPaperItem='chapter:Q1';
  const html=c.paperPage();
  assert.match(html,/已登记的正文文件缺失/);
  assert.doesNotMatch(html,/data-preview-path=/);
});

test('chapter titles, identifiers and paths are escaped', () => {
  const id='<script>Q1</script>', draft='paper/x" onclick="bad.tex';
  const state=snapshot({chapters:[{id,draft,draft_available:true}],
    writing_plan:{hash:'matches',chapter_order:[id],chapters:[{id,title:'<img src=x onerror=bad>'}]}});
  const html=context(state).paperPage();
  assert.match(html,/&lt;img/);
  assert.match(html,/&quot; onclick=&quot;/);
  assert.doesNotMatch(html,/<script>|<img src=x/);
});

test('paper selection uses the real click handler and preserves focus and scroll', () => {
  const c=context();
  let clickHandler, focused, scroll;
  const button={dataset:{paperSelect:'chapter:Q1'},focus:options=>{focused=options.preventScroll;}};
  c.document={addEventListener:(name,fn)=>{if(name==='click')clickHandler=fn;},querySelectorAll:()=>[button]};
  c.window={scrollY:145,scrollTo:(x,y)=>{scroll=[x,y];}};
  c.render=()=>{};
  c.$=()=>({hidden:true});
  const eventStart=source.indexOf("document.addEventListener('click',");
  const eventEnd=source.indexOf('\n});',eventStart)+4;
  vm.runInContext(source.slice(eventStart,eventEnd),c);
  clickHandler({target:{closest:selector=>selector==='[data-paper-select]'?button:null}});
  assert.equal(c.selectedPaperItem,'chapter:Q1');
  assert.equal(focused,true);
  assert.deepEqual(scroll,[0,145]);
});

test('a real project refresh resets the previous project chapter selection', async () => {
  const c=context();
  c.selectedPaperItem='chapter:Q1';
  c.syncGeneration=0;
  c.selectedProjectPath=()=> 'project-b';
  c.fetch=async()=>({ok:true,json:async()=>snapshot({project:'project-b'})});
  c.$=()=>({hidden:true});
  c.syncStatus=()=>{};
  c.render=()=>{};
  const refreshStart=source.indexOf('async function refresh()');
  const refreshEnd=source.indexOf('\nfunction syncStatus(',refreshStart);
  vm.runInContext(source.slice(refreshStart,refreshEnd),c);
  await c.refresh();
  assert.equal(c.state.project,'project-b');
  assert.equal(c.selectedPaperItem,null);
});

test('unsupported registered files offer their path instead of starting a preview', () => {
  const state=snapshot();
  state.files=[];
  state.chapters[0].draft_previewable=false;
  const c=context(state);
  c.selectedPaperItem='chapter:Q1';
  const html=c.paperPage();
  assert.match(html,/不支持预览/);
  assert.match(html,/data-copy-path="paper\/Q1.tex"/);
  assert.doesNotMatch(html,/data-preview-path=/);
});

test('render preserves directory scrolling only inside the same project', () => {
  for (const project of ['project-a','project-b']) {
    const c=context(snapshot({project}));
    c.selectedPaperItem='chapter:Q1';
    c.current='paper';
    c.pages=[['paper','file','论文工作区','已有章节']];
    c.nav=()=>{};
    for(const name of ['overview','flow','rolePage','questionPage','literaturePage','artifactPage','skillsPage','deliveryPage']) c[name]=()=> '';
    c.document={body:{dataset:{}}};
    let replaced=false, preview;
    const previous={dataset:{project:'project-a'},scrollTop:120};
    const next={dataset:{project},scrollTop:0,clientHeight:230,querySelector:()=>({offsetTop:0,offsetHeight:50})};
    const content={set innerHTML(value){replaced=true;}};
    const elements={'#page-title':{},'#page-subtitle':{},'#project-search':{},'#content':content,
      '#paper-chapter-preview':{dataset:{previewPath:'paper/Q1.tex'}}};
    c.$=selector=>selector==='.paper-chapter-list'?(replaced?next:previous):elements[selector]||null;
    c.renderCatalogPreview=(container,file)=>{preview=file;};
    const renderStart=source.indexOf('function render()');
    const renderEnd=source.indexOf('\nasync function refresh()',renderStart);
    vm.runInContext(source.slice(renderStart,renderEnd),c);
    c.render();
    assert.equal(next.scrollTop,project==='project-a'?120:0);
    assert.equal(preview,'paper/Q1.tex');
  }
});
