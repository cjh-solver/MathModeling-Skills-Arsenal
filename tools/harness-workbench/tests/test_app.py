import tempfile
import json
import hashlib
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import app


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.project = self.base / "contest"
        (self.project / ".contest").mkdir(parents=True)
        self.links = self.base / "app-data" / "links.json"
        self.control = self.project / ".contest" / "harness_control.yaml"

    def tearDown(self):
        self.temp.cleanup()

    def write_control(self, text):
        self.control.write_text(text, encoding="utf-8")

    def test_node_evidence_distinguishes_inputs_requested_outputs_and_review_artifacts(self):
        self.write_control('active_mode: full-contest-harness\nnodes:\n  H6: {status: review_pending, task_card: task.yaml, review_packet: review.yaml}\n')
        (self.project / 'task.yaml').write_text('node_id: H6\ninputs: [{path: input.txt}]\nrequired_outputs: [missing.txt, result.txt]\n', encoding='utf-8')
        (self.project / 'review.yaml').write_text('node_id: H6\nimportant_artifacts: [{path: result.txt}]\nsummary: recorded\n', encoding='utf-8')
        (self.project / 'input.txt').write_text('input', encoding='utf-8')
        (self.project / 'result.txt').write_text('result', encoding='utf-8')
        evidence = app.build_state(self.project, self.links)['nodes'][0]['evidence']
        self.assertEqual(evidence['inputs'][0]['path'], 'input.txt')
        self.assertFalse(evidence['required_outputs'][0]['present'])
        self.assertEqual(evidence['artifacts'][0]['path'], 'result.txt')
        self.assertEqual(evidence['review_summary'], 'recorded')
        (self.project / 'review.yaml').write_text('node_id: H5\nimportant_artifacts: [result.txt]\n', encoding='utf-8')
        evidence = app.build_state(self.project, self.links)['nodes'][0]['evidence']
        self.assertEqual(evidence['artifacts'], [])
        self.assertEqual(evidence['review_error'], '审查包节点不匹配')

    def test_historical_h4_and_pending_h9_are_preserved(self):
        self.write_control("""active_mode: full-contest-harness
problem_scope: {subproblems: [Q1]}
nodes:
  H4: {status: approved}
  H9: {status: review_pending}
agent_instances:
  H5: {agent_instance_id: instance-not-a-thread}
""")
        result = app.build_state(self.project, self.links)
        self.assertEqual([(n['id'], n['status']) for n in result['nodes']], [('H4', 'approved'), ('H9', 'review_pending')])
        self.assertEqual(result['visual_workflow'], '未记录（历史流程）')
        solver = next(role for role in result['roles'] if role['name'] == '解题')
        self.assertEqual(solver['instance_id'], 'instance-not-a-thread')
        self.assertIsNone(solver['thread_id'])

    def test_merged_h4_is_hidden_and_support_instances_are_distinct(self):
        self.write_control("""active_mode: full-contest-harness
visual_workflow: chapter_parallel
nodes:
  H4: {status: merged}
  H5: {status: not_started}
  H7: {writer_preparation: {writing_plan: {path: plan.yaml, sha256: bad}, chapters: [{chapter_id: q1, draft: {path: paper/q1.tex}, visuals_required: false, visual_prompts: [{revision_id: r1, prompt: {path: prompt.md}}]}]}}
dispatch_records:
  - {owner_role: 辅助角色, agent_instance_id: support-1, node_id: H5}
  - {owner_role: 辅助角色, agent_instance_id: support-1, node_id: H5}
""")
        (self.project / 'plan.yaml').write_text('writing_order: [q1, abstract]\nchapter_order: [abstract, q1]', encoding='utf-8')
        result = app.build_state(self.project, self.links)
        self.assertEqual([n['id'] for n in result['nodes']], ['H5', 'H7'])
        self.assertEqual(result['visual_workflow'], 'chapter_parallel')
        self.assertEqual(result['chapters'][0]['draft'], 'paper/q1.tex')
        self.assertEqual(result['chapters'][0]['prompts'][0]['path'], 'prompt.md')
        self.assertEqual(result['writing_plan']['writing_order'], ['q1', 'abstract'])
        self.assertEqual(result['writing_plan']['hash'], 'issues')
        self.assertEqual(sum(r['instance_id'] == 'support-1' for r in result['roles']), 1)

    def test_role_registration_is_separate_from_project_and_validated(self):
        self.write_control('active_mode: full-contest-harness\nnodes: {}\n')
        original = self.control.read_bytes()
        with self.assertRaises(ValueError):
            app.save_link(self.project, '解题', 'not-a-uuid', self.links)
        thread_id = '01a18b46-b9e2-7e40-a766-3cb725796ebc'
        app.save_link(self.project, '解题', thread_id, self.links)
        result = app.build_state(self.project, self.links)
        self.assertEqual(next(r for r in result['roles'] if r['name'] == '解题')['thread_id'], thread_id)
        second = '01a1c61b-1718-75e3-8979-051bcc08bfec'
        app.save_link(self.project, '解题', second, self.links)
        updated = next(r for r in app.build_state(self.project, self.links)['roles'] if r['name'] == '解题')
        self.assertEqual(updated['thread_id'], second)
        self.assertEqual([entry['thread_id'] for entry in updated['history']], [thread_id, second])
        self.assertEqual(self.control.read_bytes(), original)

    def test_legacy_link_is_preserved_when_updating(self):
        first = '01a18b46-b9e2-7e40-a766-3cb725796ebc'
        second = '01a1c61b-1718-75e3-8979-051bcc08bfec'
        self.links.parent.mkdir()
        self.links.write_text(json.dumps({str(self.project): {'解题': first}}), encoding='utf-8')
        app.save_link(self.project, '解题', second, self.links)
        current, histories = app.current_links(app.load_links(self.links)[str(self.project)])
        self.assertEqual(current['解题'], second)
        self.assertEqual([item['thread_id'] for item in histories['解题']], [first, second])

    def test_verified_lookup_provenance_is_retained(self):
        self.write_control('active_mode: full-contest-harness\nnodes: {}\n')
        thread_id = '01a18b46-b9e2-7e40-a766-3cb725796ebc'
        app.save_link(self.project, '解题', thread_id, self.links, source='verified_codex_thread_lookup', title='实际会话')
        role = next(r for r in app.build_state(self.project, self.links)['roles'] if r['name'] == '解题')
        self.assertEqual(role['link_source'], 'verified_codex_thread_lookup')
        self.assertEqual(role['history'][0]['title'], '实际会话')

    def test_project_and_preview_boundaries(self):
        self.write_control('active_mode: full-contest-harness\nnodes: {}\n')
        (self.project / 'paper.md').write_text('paper', encoding='utf-8')
        (self.base / 'outside.md').write_text('outside', encoding='utf-8')
        self.assertEqual(app.project_path(str(self.project)), self.project)
        self.assertEqual(app.safe_file(self.project, 'paper.md').name, 'paper.md')
        with self.assertRaises(ValueError):
            app.safe_file(self.project, '../outside.md')
        with self.assertRaises(ValueError):
            app.project_path(str(self.base))

    def test_file_listing_discloses_depth_limit_and_large_preview(self):
        deep = self.project / 'one' / 'two' / 'three' / 'four' / 'five'
        deep.mkdir(parents=True)
        (deep / 'hidden.md').write_text('deep', encoding='utf-8')
        with (self.project / 'large.txt').open('wb') as file:
            file.truncate(20 * 1024 * 1024 + 1)
        files, incomplete = app.list_files(self.project)
        self.assertTrue(incomplete)
        self.assertFalse(next(file for file in files if file['path'] == 'large.txt')['previewable'])
        self.assertNotIn('one/two/three/four/five/hidden.md', [file['path'] for file in files])

    def test_file_listing_limit_is_only_incomplete_when_exceeded(self):
        for index in range(1500):
            (self.project / f'{index:04}.txt').touch()
        files, incomplete = app.list_files(self.project)
        self.assertEqual(len(files), 1500)
        self.assertFalse(incomplete)
        (self.project / 'extra.txt').touch()
        files, incomplete = app.list_files(self.project)
        self.assertEqual(len(files), 1500)
        self.assertTrue(incomplete)

    def test_project_discovery_finds_candidates_without_scanning_hidden_trees(self):
        self.write_control('active_mode: full-contest-harness\nnodes: {}\n')
        hidden = self.base / '.hidden' / '.contest'
        hidden.mkdir(parents=True)
        (hidden / 'harness_control.yaml').write_text('active_mode: full-contest-harness', encoding='utf-8')
        self.assertEqual([item['name'] for item in app.discover_projects(self.base)], ['contest'])

    def test_paper_preview_is_matched_only_to_recorded_source(self):
        self.write_control('active_mode: full-contest-harness\nnodes: {H8: {paper_source: draft/main.tex}}\n')
        (self.project / 'draft').mkdir()
        (self.project / 'draft' / 'main.tex').write_text('test', encoding='utf-8')
        (self.project / 'draft' / 'main.pdf').write_bytes(b'not a valid pdf')
        result = app.build_state(self.project, self.links)
        self.assertEqual(result['paper_source'], 'draft/main.tex')
        self.assertEqual(result['paper_pdf'], 'draft/main.pdf')

    def test_project_role_registry_uses_only_explicit_valid_thread_ids(self):
        self.write_control("""active_mode: full-contest-harness
agent_instances: {H5: {agent_instance_id: solver-1}}
nodes: {H5: {status: approved}}
dispatch_records: [{node_id: H5, agent_instance_id: solver-1, task_id: task1, model: model1}]
""")
        (self.project / '.contest' / 'agent_registry.yaml').write_text("""instances:
  - {role: 解题, agent_instance_id: solver-1, thread_id: 01a18b46-b9e2-7e40-a766-3cb725796ebc, user_accessible: true, status: active}
  - {role: 辅助, agent_instance_id: helper-1, thread_id: pending-not-an-id, status: pending}
""", encoding='utf-8')
        result = app.build_state(self.project, self.links)
        solver = next(role for role in result['roles'] if role['name'] == '解题')
        self.assertEqual(solver['thread_id'], '01a18b46-b9e2-7e40-a766-3cb725796ebc')
        self.assertEqual(solver['link_source'], 'project_registry')
        self.assertEqual(solver['dispatches'][0]['task_id'], 'task1')
        helper = next(role for role in result['roles'] if role['instance_id'] == 'helper-1')
        self.assertIsNone(helper['thread_id'])

    def test_unsupported_mode_is_not_misrepresented(self):
        self.write_control('active_mode: mathorcup\nnodes: {}\n')
        with self.assertRaisesRegex(ValueError, 'full-contest-harness'):
            app.build_state(self.project, self.links)

    def test_explicit_question_and_figure_associations_are_loaded(self):
        self.write_control("""active_mode: full-contest-harness
problem_scope: {subproblems: [Q1, Q2]}
nodes:
  H1: {unified_problem_package: {path: problem.yaml}}
  H5: {model_summary_cards: models.yaml, result_interpretation_cards: interpretations.yaml}
  H7: {figure_registry: figures.yaml}
""")
        (self.project / 'problem.yaml').write_text('objectives: {Q1: estimate}\nquestions: {Q1: {inputs: [data], outputs: [result]}}', encoding='utf-8')
        (self.project / 'models.yaml').write_text('cards: [{card_id: model1, subproblem_id: Q1, result: 42}]', encoding='utf-8')
        (self.project / 'interpretations.yaml').write_text('cards: [{id: result1, subproblem_id: Q1, fact: 42, evidence: result.csv}]', encoding='utf-8')
        (self.project / 'figures.yaml').write_text('figures: [{figure_id: chart1, png: {path: chart.png}, source_files: [{path: plot.py}, 7], caption_claim: Example}]', encoding='utf-8')
        result = app.build_state(self.project, self.links)
        self.assertEqual(result['question_views'][0]['objective'], 'estimate')
        self.assertEqual(result['question_views'][0]['models'][0]['result'], 42)
        self.assertEqual(result['question_views'][0]['interpretations'][0]['evidence'], 'result.csv')
        self.assertEqual(result['question_views'][1]['models'], [])
        self.assertEqual(result['figures'][0]['png'], 'chart.png')
        self.assertEqual(result['figures'][0]['source_files'], ['plot.py'])

    def test_question_associations_require_recorded_coverage_and_matching_dispatch(self):
        self.write_control("""active_mode: full-contest-harness
problem_scope: {subproblems: [Q1, Q2]}
nodes:
  H5: {task_card: .contest/H5.yaml, model_summary_cards: models.yaml}
  H7: {figure_registry: figures.yaml}
dispatch_records:
  - {node_id: H5, task_id: task-1, task_card_path: .contest/H5.yaml, owner_role: 解题 agent}
  - {node_id: H5, task_id: wrong, task_card_path: .contest/H5.yaml, owner_role: 不应显示}
  - {node_id: H5, task_id: task-1, task_card_path: .contest/H5.yaml, owner_role: 错误负责人}
""")
        (self.project / '.contest' / 'H5.yaml').write_text('node_id: H5\ntask_id: task-1\nowner_role: 解题 agent\ncovered_subproblems: [Q1]\n', encoding='utf-8')
        (self.project / 'models.yaml').write_text('cards: [{card_id: m1, subproblem_id: Q1}]', encoding='utf-8')
        (self.project / 'figures.yaml').write_text('figures: [{figure_id: H7-Q1, png: chart.png}, {figure_id: unrelated, subproblem_id: Q1, svg: chart.svg}, {figure_id: H7-Q10, png: other.png}]', encoding='utf-8')
        for name in ('chart.png', 'chart.svg', 'other.png'):
            (self.project / name).write_bytes(b'test')
        result = app.build_state(self.project, self.links)
        q1, q2 = result['question_views']
        association = q1['associations']
        self.assertEqual([stage['id'] for stage in association['stages']], ['H5'])
        self.assertEqual([role['name'] for role in association['roles']], ['解题 agent'])
        self.assertTrue(any(item['path'] == 'models.yaml' and '明确' in item['relation'] for item in association['materials']))
        self.assertTrue(any(item['path'] == 'chart.png' and '可能相关' in item['relation'] for item in association['materials']))
        self.assertTrue(any(item['path'] == 'chart.svg' and '明确' in item['relation'] for item in association['materials']))
        self.assertNotIn('other.png', [item['path'] for item in association['materials']])
        self.assertEqual(q2['associations'], {'materials': [], 'stages': [], 'roles': []})

    def test_question_association_rejects_missing_and_external_files(self):
        outside = self.base / 'outside.png'
        outside.write_bytes(b'private')
        result = app.question_associations(self.project, 'Q1', {}, [], [
            {'subproblem_id': 'Q1', 'png': '../outside.png', 'svg': 'missing.svg'}
        ], [], [], None, 'figures.yaml')
        self.assertEqual(result['materials'], [])

    def test_chapter_parallel_plan_and_prompt_follow_documented_schema(self):
        plan = self.project / 'plan.yaml'
        draft = self.project / 'q1.tex'
        prompt = self.project / 'prompt.md'
        visual_plan = self.project / 'visual.yaml'
        plan.write_text('writing_order: [Q1, abstract]\nchapter_order: [abstract, Q1]\ncentral_thesis: Example', encoding='utf-8')
        draft.write_text('Example chapter', encoding='utf-8')
        prompt.write_text('Example figure prompt', encoding='utf-8')
        visual_plan.write_text('slots: []', encoding='utf-8')
        plan_hash = hashlib.sha256(plan.read_bytes()).hexdigest()
        draft_hash = hashlib.sha256(draft.read_bytes()).hexdigest()
        prompt_hash = hashlib.sha256(prompt.read_bytes()).hexdigest()
        visual_hash = hashlib.sha256(visual_plan.read_bytes()).hexdigest()
        self.write_control(f'''active_mode: full-contest-harness
visual_workflow: chapter_parallel
nodes:
  H7:
    writer_preparation:
      writing_plan: {{path: plan.yaml, sha256: {plan_hash}}}
      chapters:
        - chapter_id: Q1
          draft: {{path: q1.tex, sha256: {draft_hash}}}
          visual_prompts:
            - {{revision_id: r1, prompt: {{path: prompt.md, sha256: {prompt_hash}}}, visual_plan: {{path: visual.yaml, sha256: {visual_hash}}}, supersedes: null}}
''')
        (self.project / '.contest' / 'approval_log.yaml').write_text(f'''approvals:
  - gate: H7_CHAPTER:Q1
    decision: approved
    artifact_digests: {{q1.tex: {draft_hash}}}
''', encoding='utf-8')
        result = app.build_state(self.project, self.links)
        self.assertEqual(result['writing_plan']['hash'], 'matches')
        self.assertEqual(result['writing_plan']['writing_order'], ['Q1', 'abstract'])
        self.assertEqual(result['chapters'][0]['prompts'][0]['revision'], 'r1')
        self.assertEqual(result['chapters'][0]['prompts'][0]['hash'], 'matches')
        self.assertEqual(result['chapters'][0]['prompts'][0]['visual_plan_hash'], 'matches')
        self.assertEqual(result['chapters'][0]['draft_hash'], 'matches')
        self.assertEqual(result['approvals'][0]['digests']['status'], 'matches')
        draft.write_text('Changed chapter', encoding='utf-8')
        changed = app.build_state(self.project, self.links)
        self.assertEqual(changed['approvals'][0]['digests']['status'], 'issues')
        self.assertEqual(changed['chapters'][0]['draft_hash'], 'issues')

    def test_missing_and_outside_association_files_are_not_read(self):
        self.write_control("""active_mode: full-contest-harness
problem_scope: {subproblems: [Q1]}
nodes:
  H1: {unified_problem_package: ../secret.yaml}
  H5: {model_summary_cards: missing.yaml}
""")
        (self.base / 'secret.yaml').write_text('objectives: {Q1: private}', encoding='utf-8')
        result = app.build_state(self.project, self.links)
        self.assertIsNone(result['question_views'][0]['objective'])
        self.assertTrue(result['question_sources']['profile_error'])
        self.assertTrue(result['question_sources']['models_error'])

    def test_http_keeps_project_selection_per_request_and_rejects_cross_origin_writes(self):
        self.write_control('active_mode: full-contest-harness\nnodes: {}\n')
        other = self.base / 'other'
        (other / '.contest').mkdir(parents=True)
        (other / '.contest' / 'harness_control.yaml').write_text('active_mode: full-contest-harness\nnodes: {}\n', encoding='utf-8')
        class TestHandler(app.Handler):
            project = self.project
            links_path = self.links
            token = 'test-token'
            def log_message(self, *_args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), TestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f'http://127.0.0.1:{server.server_port}'
        with urllib.request.urlopen(base + '/api/state?project=' + urllib.parse.quote(str(other))) as response:
            self.assertEqual(json.load(response)['project'], str(other))
        with urllib.request.urlopen(base + '/api/state') as response:
            self.assertEqual(json.load(response)['project'], str(self.project))
        self.write_control('invalid: [')
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(base + '/api/state')
        with urllib.request.urlopen(base + '/api/bootstrap') as response:
            self.assertEqual(json.load(response)['token'], 'test-token')
        TestHandler.project = None
        with urllib.request.urlopen(base + '/') as response:
            self.assertEqual(response.status, 200)
        with urllib.request.urlopen(base + '/api/bootstrap') as response:
            self.assertEqual(json.load(response)['token'], 'test-token')
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(base + '/api/state')
        self.assertEqual(error.exception.code, 400)
        with urllib.request.urlopen(base + '/api/state?project=' + urllib.parse.quote(str(other))) as response:
            self.assertEqual(json.load(response)['project'], str(other))
        TestHandler.project = self.project
        self.write_control('active_mode: full-contest-harness\nnodes: {}\n')
        body = json.dumps({'project': str(other), 'role': '解题', 'thread_id': '01a18b46-b9e2-7e40-a766-3cb725796ebc'}).encode()
        request = urllib.request.Request(base + '/api/role-link', data=body, headers={'Origin': 'https://example.com', 'X-Workbench-Token': 'test-token', 'Content-Type': 'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request)
        self.assertEqual(error.exception.code, 403)
        self.assertFalse(self.links.exists())
        request = urllib.request.Request(base + '/api/role-link', data=body, headers={'Origin': base, 'X-Workbench-Token': 'test-token', 'Content-Type': 'application/json'})
        with urllib.request.urlopen(request) as response:
            self.assertEqual(json.load(response), {'ok': True})
        saved = app.load_links(self.links)
        self.assertIn(str(other), saved)
        self.assertNotIn(str(self.project), saved)
        if app.fitz is not None:
            with app.fitz.open() as document:
                document.new_page()
                document.save(self.project / 'sample.pdf')
            with urllib.request.urlopen(base + '/api/pdf-info?path=sample.pdf') as response:
                self.assertEqual(json.load(response)['pages'], 1)
            with urllib.request.urlopen(base + '/api/pdf-page?path=sample.pdf&page=1') as response:
                self.assertEqual(response.headers.get_content_type(), 'image/png')
                self.assertEqual(response.read(8), b'\x89PNG\r\n\x1a\n')
        if app.openpyxl is not None:
            workbook = app.openpyxl.Workbook()
            workbook.active['A1'] = '=1+1'
            workbook.save(self.project / 'sample.xlsx')
            workbook.close()
            with urllib.request.urlopen(base + '/api/document?path=sample.xlsx') as response:
                self.assertEqual(json.load(response)['rows'][0][0], '=1+1')
        if app.docx is not None:
            document = app.docx.Document()
            document.add_paragraph('sample paragraph')
            document.save(self.project / 'sample.docx')
            with urllib.request.urlopen(base + '/api/document?path=sample.docx') as response:
                self.assertEqual(json.load(response)['paragraphs'][0], 'sample paragraph')
        (self.project / 'sample.csv').write_text('name,value\n"a,b",3\n', encoding='utf-8')
        with urllib.request.urlopen(base + '/api/document?path=sample.csv') as response:
            self.assertEqual(json.load(response)['rows'][1], ['a,b', '3'])

    def test_approval_hash_checks_do_not_escape_project_or_hide_changes(self):
        (self.project / 'result.txt').write_text('actual', encoding='utf-8')
        expected = hashlib.sha256(b'actual').hexdigest()
        outside = self.base / 'outside.txt'
        outside.write_text('actual', encoding='utf-8')
        result = app.digest_status(self.project, {'result.txt': expected, 'missing.txt': expected, '../outside.txt': expected})
        self.assertEqual([item['status'] for item in result['files']], ['matches', 'missing', 'unverified'])
        (self.project / 'result.txt').write_text('changed', encoding='utf-8')
        self.assertEqual(app.digest_status(self.project, {'result.txt': expected})['files'][0]['status'], 'changed')

    def test_existing_report_is_displayed_as_recorded_not_recomputed(self):
        report = self.project / 'report.json'
        report.write_text(json.dumps({'passed': False, 'issues': ['build failed']}), encoding='utf-8')
        result = app.read_report(self.project, 'report.json', 'Compile')
        self.assertFalse(result['passed'])
        self.assertEqual(result['issues'], ['build failed'])
        self.assertIsNotNone(result['modified'])


if __name__ == '__main__':
    unittest.main()
