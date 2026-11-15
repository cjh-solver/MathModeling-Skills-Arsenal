import tempfile
import json
import hashlib
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
import zipfile
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

    def test_invalid_role_link_root_never_overwrites_existing_records(self):
        self.links.parent.mkdir()
        self.write_control('active_mode: full-contest-harness\nnodes: {}\n')
        for content in ('[]', 'null', '"unexpected"', '42', '{invalid'):
            with self.subTest(content=content):
                self.links.write_text(content, encoding='utf-8')
                before = self.links.read_bytes()
                with self.assertRaisesRegex(ValueError, '角色登记文件'):
                    app.save_link(self.project, '解题', '01a18b46-b9e2-7e40-a766-3cb725796ebc', self.links)
                self.assertEqual(self.links.read_bytes(), before)
                state = app.build_state(self.project, self.links)
                self.assertIn('角色登记文件', state['role_links_error'])
                self.assertTrue(state['roles'])
                self.assertEqual(self.links.read_bytes(), before)

    def test_bad_role_history_does_not_hide_project_or_replace_registry_link(self):
        self.write_control('active_mode: full-contest-harness\nagent_instances: {H5: {agent_instance_id: solver}}\nnodes: {H5: {status: draft}}\n')
        registry = self.project / '.contest' / 'agent_registry.yaml'
        registry.write_text('instances:\n  - {agent_instance_id: solver, thread_id: 01a18b46-b9e2-7e40-a766-3cb725796ebc}\n', encoding='utf-8')
        self.links.parent.mkdir()
        self.links.write_text(json.dumps({str(self.project): {'解题': [None]}}), encoding='utf-8')
        before = self.links.read_bytes()
        state = app.build_state(self.project, self.links)
        self.assertTrue(state['role_links_error'])
        self.assertEqual(state['nodes'][0]['id'], 'H5')
        role = next(role for role in state['roles'] if role['name'] == '解题')
        self.assertIsNone(role['thread_id'])
        self.assertIsNotNone(role['registry_thread_id'])
        with self.assertRaises(ValueError):
            app.save_link(self.project, '主控', '01a18b46-b9e2-7e40-a766-3cb725796ebc', self.links)
        self.assertEqual(self.links.read_bytes(), before)

    def test_duplicate_link_fields_are_reported_without_overwriting_history(self):
        self.links.parent.mkdir()
        self.write_control('active_mode: full-contest-harness\nnodes: {}\n')
        project = json.dumps(str(self.project), ensure_ascii=False)
        thread = '01a18b46-b9e2-7e40-a766-3cb725796ebc'
        cases = [
            f'{{{project}: {{}}, {project}: {{}}}}',
            f'{{{project}: {{"解题": "{thread}", "解题": "{thread}"}}}}',
            f'{{{project}: {{"解题": [{{"thread_id": "{thread}", "thread_id": "{thread}"}}]}}}}',
        ]
        for content in cases:
            with self.subTest(content=content):
                self.links.write_text(content, encoding='utf-8')
                before = self.links.read_bytes()
                with self.assertRaisesRegex(ValueError, '重复字段'):
                    app.save_link(self.project, '主控', thread, self.links)
                state = app.build_state(self.project, self.links)
                self.assertIn('重复字段', state['role_links_error'])
                self.assertEqual(self.links.read_bytes(), before)
        self.links.write_text(json.dumps({str(self.project): {'解题': thread}}), encoding='utf-8')
        app.save_link(self.project, '主控', thread, self.links)
        state = app.build_state(self.project, self.links)
        self.assertIsNone(state['role_links_error'])
        self.assertEqual(next(role for role in state['roles'] if role['name'] == '解题')['thread_id'], thread)

    def test_malformed_project_registry_is_reported_and_valid_entries_remain(self):
        self.write_control('active_mode: full-contest-harness\nnodes: {}\n')
        registry = self.project / '.contest' / 'agent_registry.yaml'
        for content in ('instances: invalid\n', 'other: value\n'):
            registry.write_text(content, encoding='utf-8')
            state = app.build_state(self.project, self.links)
            self.assertIn('格式错误', state['registry_error'])
        registry.write_text('instances:\n  - {role: 已登记角色}\n  - invalid\n', encoding='utf-8')
        state = app.build_state(self.project, self.links)
        self.assertIn('格式错误', state['registry_error'])
        self.assertIn('已登记角色', [role['name'] for role in state['roles']])
        registry.write_text('instances: []\n', encoding='utf-8')
        self.assertIsNone(app.build_state(self.project, self.links)['registry_error'])

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

    def test_control_and_record_symlinks_respect_project_boundary(self):
        outside = self.base / 'outside.yaml'
        outside.write_text(
            'active_mode: full-contest-harness\nnodes: {}\n'
            'instances: [{role: 外部角色}]\napprovals: [{gate: H8, decision: approved}]\n',
            encoding='utf-8',
        )
        try:
            self.control.symlink_to(outside)
        except OSError as error:
            self.skipTest(f'symbolic links unavailable: {error}')
        with self.assertRaises(ValueError):
            app.project_path(str(self.project))
        with self.assertRaises(ValueError):
            app.build_state(self.project, self.links)

        self.control.unlink()
        self.write_control('active_mode: full-contest-harness\nnodes: {}\n')
        (self.project / '.contest' / 'approval_log.yaml').symlink_to(outside)
        (self.project / '.contest' / 'agent_registry.yaml').symlink_to(outside)
        state = app.build_state(self.project, self.links)
        self.assertEqual(state['approvals'], [])
        self.assertIn('不在当前项目', state['approval_error'])
        self.assertIn('不在当前项目', state['registry_error'])
        self.assertNotIn('外部角色', [role['name'] for role in state['roles']])

        internal = self.project / '.contest' / 'local_approvals.yaml'
        internal.write_text('approvals: [{gate: H8, decision: approved}]\n', encoding='utf-8')
        approval = self.project / '.contest' / 'approval_log.yaml'
        approval.unlink()
        approval.symlink_to(internal)
        state = app.build_state(self.project, self.links)
        self.assertIsNone(state['approval_error'])
        self.assertEqual(state['approvals'][0]['gate'], 'H8')

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
        paper = self.project / 'paper'
        paper.mkdir()
        (paper / 'main.pdf').write_bytes(b'pdf')
        (paper / 'compile_report.json').write_text('{"passed": false}', encoding='utf-8')
        self.write_control('active_mode: full-contest-harness\nnodes: {H8: {paper_source: paper/main.tex}}\n')
        state = app.build_state(self.project, self.links)
        self.assertTrue(state['files_truncated'])
        self.assertNotIn('paper/main.pdf', [item['path'] for item in state['files']])
        self.assertEqual(state['paper_pdf'], 'paper/main.pdf')
        self.assertFalse(state['reports'][0]['passed'])

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
        (self.base / 'outside.pdf').write_bytes(b'pdf')
        self.write_control('active_mode: full-contest-harness\nnodes: {H8: {paper_source: ../outside.tex}}\n')
        self.assertIsNone(app.build_state(self.project, self.links)['paper_pdf'])

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

    def test_recorded_timestamp_requires_valid_timezone(self):
        self.assertEqual(app.recorded_timestamp('2026-11-14T13:00:00Z'), '2026-11-14T13:00:00+00:00')
        self.assertIsNone(app.recorded_timestamp('2026-11-14T13:00:00'))
        self.assertIsNone(app.recorded_timestamp('2026-02-30T13:00:00Z'))
        self.assertIsNone(app.recorded_timestamp(None))

    def test_json_safe_preserves_shared_values_and_rejects_cycles(self):
        shared = [float('nan'), 2.5]
        self.assertEqual(app.json_safe({'first': shared, 'second': shared}),
                         {'first': ['NaN', 2.5], 'second': ['NaN', 2.5]})
        cycle = []
        cycle.append(cycle)
        with self.assertRaisesRegex(ValueError, '循环引用'):
            app.json_safe(cycle)
        with self.assertRaisesRegex(ValueError, '无法区分的键'):
            app.json_safe({app.date(2026, 11, 15): 1, '2026-11-15': 2})
        self.assertEqual(app.json_safe({1: 'number', False: 'boolean', None: 'empty', 2.5: 'decimal'}),
                         {'1': 'number', 'false': 'boolean', 'null': 'empty', '2.5': 'decimal'})
        for data in ({1: 'number', '1': 'text'}, {None: 1, 'null': 2}, {False: 1, 'false': 2}):
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, '无法区分的键'):
                app.json_safe({'nested': data})

    def test_visual_slots_follow_harness_representation_rules(self):
        valid = [
            {'slot_id': 'a', 'representation': 'text'},
            {'slot_id': 'b', 'representation': {'mode': 'table'}},
            {'slot_id': 'c', 'representation': 'figure', 'generation_route': 'modelviz'},
            {'slot_id': 'd', 'representation': {'mode': 'figure'}, 'figure_intent': {'generation_route': 'tikz-scientific-figures'}},
        ]
        invalid = [None, {}, {'slot_id': 'a'}, {'slot_id': '', 'representation': 'text'},
                   {'slot_id': 'a', 'representation': 'figure'},
                   {'slot_id': 'a', 'representation': 'figure', 'generation_route': 'unknown'},
                   {'slot_id': 'a', 'representation': 'image'}]
        for slot in valid:
            with self.subTest(slot=slot):
                self.assertTrue(app.valid_visual_slot(slot))
        for slot in invalid:
            with self.subTest(slot=slot):
                self.assertFalse(app.valid_visual_slot(slot))

    def test_chapter_parallel_plan_and_prompt_follow_documented_schema(self):
        plan = self.project / 'plan.yaml'
        draft = self.project / 'q1.tex'
        prompt = self.project / 'prompt.md'
        visual_plan = self.project / 'visual.yaml'
        quality = self.project / 'quality.yaml'
        packet = self.project / 'review.yaml'
        plan.write_text('writing_order: [Q1, abstract]\nchapter_order: [abstract, Q1]\ncentral_thesis: Example\nchapters: [{chapter_id: Q1, kind: modeling}]', encoding='utf-8')
        draft.write_text('Example chapter', encoding='utf-8')
        prompt.write_text('Example figure prompt', encoding='utf-8')
        packet.write_text('node_id: H7_CHAPTER:Q1', encoding='utf-8')
        plan_hash = hashlib.sha256(plan.read_bytes()).hexdigest()
        draft_hash = hashlib.sha256(draft.read_bytes()).hexdigest()
        quality_data = {'status': 'ready', 'draft_sha256': draft_hash, 'checks': {key: 'PASS' for key in app.CHAPTER_QUALITY_CHECKS}}
        quality.write_text(app.yaml.safe_dump(quality_data), encoding='utf-8')
        visual_plan.write_text(f'chapter_id: Q1\nrevision_id: r1\ndraft: {{path: q1.tex, sha256: {draft_hash}}}\nslots: [{{slot_id: figure1, representation: figure, generation_route: modelviz}}]\n', encoding='utf-8')
        prompt_hash = hashlib.sha256(prompt.read_bytes()).hexdigest()
        visual_hash = hashlib.sha256(visual_plan.read_bytes()).hexdigest()
        quality_hash = hashlib.sha256(quality.read_bytes()).hexdigest()
        packet_hash = hashlib.sha256(packet.read_bytes()).hexdigest()
        self.write_control(f'''active_mode: full-contest-harness
visual_workflow: chapter_parallel
nodes:
  H7:
    writer_preparation:
      writing_plan: {{path: plan.yaml, sha256: {plan_hash}}}
      plan_review_packet: plan-review.yaml
      chapters:
        - chapter_id: Q1
          draft: {{path: q1.tex, sha256: {draft_hash}}}
          draft_completed_at: "2026-11-14T11:00:00+08:00"
          quality_review: {{path: quality.yaml, sha256: {quality_hash}}}
          review_packet: review.yaml
          visual_prompts:
            - {{revision_id: r1, prompt: {{path: prompt.md, sha256: {prompt_hash}}}, visual_plan: {{path: visual.yaml, sha256: {visual_hash}}}, prepared_at: "2026-11-14T13:00:00+08:00", supersedes: null}}
''')
        (self.project / '.contest' / 'approval_log.yaml').write_text(f'''approvals:
  - gate: H7_CHAPTER:Q1
    decision: approved
    timestamp: "2026-11-14T12:00:00+08:00"
    artifact_digests: {{q1.tex: {draft_hash}, quality.yaml: {quality_hash}, review.yaml: {packet_hash}}}
''', encoding='utf-8')
        result = app.build_state(self.project, self.links)
        self.assertEqual(result['writing_plan']['hash'], 'matches')
        self.assertEqual(result['writing_plan']['review_packet'], 'plan-review.yaml')
        self.assertEqual(result['writing_plan']['writing_order'], ['Q1', 'abstract'])
        self.assertEqual(result['chapters'][0]['prompts'][0]['revision'], 'r1')
        self.assertEqual(result['chapters'][0]['prompts'][0]['hash'], 'matches')
        self.assertEqual(result['chapters'][0]['prompts'][0]['sha256'], prompt_hash)
        self.assertEqual(result['chapters'][0]['prompts'][0]['visual_plan_hash'], 'matches')
        self.assertTrue(result['chapters'][0]['prompts'][0]['plan_binding'])
        self.assertEqual(result['chapters'][0]['prompts'][0]['prepared_at'], '2026-11-14T13:00:00+08:00')
        self.assertEqual(result['chapters'][0]['draft_hash'], 'matches')
        self.assertEqual(result['chapters'][0]['draft_completed_at'], '2026-11-14T11:00:00+08:00')
        self.assertEqual(result['chapters'][0]['quality_review'], 'quality.yaml')
        self.assertEqual(result['chapters'][0]['quality_hash'], 'matches')
        self.assertTrue(result['chapters'][0]['quality_ready'])
        self.assertEqual(result['chapters'][0]['review_packet'], 'review.yaml')
        self.assertEqual(result['approvals'][0]['timestamp'], '2026-11-14T12:00:00+08:00')
        self.assertEqual(result['approvals'][0]['digests']['status'], 'matches')
        invalid_visual = visual_plan.read_text(encoding='utf-8').replace('generation_route: modelviz', 'generation_route: unknown')
        visual_plan.write_text(invalid_visual, encoding='utf-8')
        invalid_hash = hashlib.sha256(visual_plan.read_bytes()).hexdigest()
        self.control.write_text(self.control.read_text(encoding='utf-8').replace(visual_hash, invalid_hash), encoding='utf-8')
        invalid = app.build_state(self.project, self.links)['chapters'][0]['prompts'][0]
        self.assertEqual(invalid['visual_plan_hash'], 'matches')
        self.assertFalse(invalid['plan_binding'])
        self.control.write_text(self.control.read_text(encoding='utf-8').replace(invalid_hash, visual_hash), encoding='utf-8')
        visual_plan.write_text(f'chapter_id: WRONG\nrevision_id: r1\ndraft: {{path: q1.tex, sha256: {draft_hash}}}\nslots: [{{slot_id: figure1}}]\n', encoding='utf-8')
        updated_visual_hash = hashlib.sha256(visual_plan.read_bytes()).hexdigest()
        self.control.write_text(self.control.read_text(encoding='utf-8').replace(visual_hash, updated_visual_hash), encoding='utf-8')
        mismatched = app.build_state(self.project, self.links)
        self.assertEqual(mismatched['chapters'][0]['prompts'][0]['visual_plan_hash'], 'matches')
        self.assertFalse(mismatched['chapters'][0]['prompts'][0]['plan_binding'])
        quality_data['checks']['model_and_derivation'] = {'status': 'not_applicable', 'reason': 'example'}
        quality.write_text(app.yaml.safe_dump(quality_data), encoding='utf-8')
        updated_quality_hash = hashlib.sha256(quality.read_bytes()).hexdigest()
        self.control.write_text(self.control.read_text(encoding='utf-8').replace(quality_hash, updated_quality_hash), encoding='utf-8')
        unready = app.build_state(self.project, self.links)
        self.assertEqual(unready['chapters'][0]['quality_hash'], 'matches')
        self.assertFalse(unready['chapters'][0]['quality_ready'])
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
        self.write_control('active_mode: full-contest-harness\nproblem_scope: {subproblems: [Q1]}\nnodes:\n  H5: {model_summary_cards: models.yaml}\n')
        model_file = self.project / 'models.yaml'
        model_file.write_text('cards:\n  - subproblem_id: Q1\n    result: {values: [.nan, .inf, -.inf, 1.25], daily: {2026-11-15: 4.2}}\n', encoding='utf-8')
        original = model_file.read_bytes()
        def reject_nonstandard_constant(value):
            raise AssertionError(f'Nonstandard JSON constant: {value}')
        with urllib.request.urlopen(base + '/api/state') as response:
            state = json.load(response, parse_constant=reject_nonstandard_constant)
        self.assertEqual(state['question_views'][0]['models'][0]['result']['values'], ['NaN', 'Infinity', '-Infinity', 1.25])
        self.assertEqual(state['question_views'][0]['models'][0]['result']['daily'], {'2026-11-15': 4.2})
        self.assertEqual(model_file.read_bytes(), original)
        model_file.write_text('cards:\n  - subproblem_id: Q1\n    result: {1: numeric, "1": text}\n', encoding='utf-8')
        original = model_file.read_bytes()
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(base + '/api/state')
        self.assertEqual(error.exception.code, 400)
        self.assertIn('无法区分的键', json.load(error.exception)['error'])
        self.assertEqual(model_file.read_bytes(), original)
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
            with zipfile.ZipFile(self.project / 'broken.xlsx', 'w') as archive:
                archive.writestr('[Content_Types].xml', '<broken')
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(base + '/api/document?path=broken.xlsx')
            self.assertEqual(error.exception.code, 400)
            workbook = app.openpyxl.Workbook()
            workbook.active['A1'] = '=1+1'
            workbook.create_chartsheet('Chart').add_chart(app.openpyxl.chart.BarChart())
            workbook.save(self.project / 'sample.xlsx')
            workbook.close()
            with zipfile.ZipFile(self.project / 'sample.xlsx') as source, zipfile.ZipFile(self.project / 'broken-sheet.xlsx', 'w') as target:
                for entry in source.infolist():
                    content = source.read(entry.filename)
                    if entry.filename == 'xl/worksheets/sheet1.xml':
                        content = b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:A1"/><sheetData><row><broken'
                    target.writestr(entry, content)
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(base + '/api/document?path=broken-sheet.xlsx')
            self.assertEqual(error.exception.code, 400)
            with urllib.request.urlopen(base + '/api/document?path=sample.xlsx') as response:
                preview = json.load(response)
                self.assertEqual(preview['rows'][0][0], '=1+1')
                self.assertEqual(preview['sheets'], ['Sheet'])
                self.assertIn('图表工作表', preview['note'])
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(base + '/api/document?path=sample.xlsx&sheet=Chart')
            self.assertEqual(error.exception.code, 400)
            workbook = app.openpyxl.Workbook()
            workbook.remove(workbook.active)
            workbook.create_chartsheet('Chart').add_chart(app.openpyxl.chart.BarChart())
            workbook.save(self.project / 'charts-only.xlsx')
            workbook.close()
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(base + '/api/document?path=charts-only.xlsx')
            self.assertEqual(error.exception.code, 400)
        if app.docx is not None:
            document = app.docx.Document()
            document.add_paragraph('sample paragraph')
            document.add_table(rows=1, cols=1).cell(0, 0).text = 'table value'
            document.add_paragraph('after table')
            document.save(self.project / 'sample.docx')
            with urllib.request.urlopen(base + '/api/document?path=sample.docx') as response:
                preview = json.load(response)
                self.assertEqual(preview['paragraphs'][0], 'sample paragraph')
                self.assertEqual([block['type'] for block in preview['blocks']], ['paragraph', 'table', 'paragraph'])
                self.assertEqual(preview['blocks'][1]['rows'], [['table value']])
                self.assertEqual(preview['blocks'][2]['text'], 'after table')
        (self.project / 'sample.csv').write_text('name,value\n"a,b",3\n', encoding='utf-8')
        with urllib.request.urlopen(base + '/api/document?path=sample.csv') as response:
            self.assertEqual(json.load(response)['rows'][1], ['a,b', '3'])
        (self.project / 'long.csv').write_text('x' * 150000, encoding='utf-8')
        with urllib.request.urlopen(base + '/api/document?path=long.csv') as response:
            preview = json.load(response)
            self.assertEqual(len(preview['rows'][0][0]), 5000)
            self.assertIn('5000', preview['note'])

    def test_approval_hash_checks_do_not_escape_project_or_hide_changes(self):
        (self.project / 'result.txt').write_text('actual', encoding='utf-8')
        expected = hashlib.sha256(b'actual').hexdigest()
        outside = self.base / 'outside.txt'
        outside.write_text('actual', encoding='utf-8')
        result = app.digest_status(self.project, {'result.txt': expected, 'missing.txt': expected, '../outside.txt': expected})
        self.assertEqual([item['status'] for item in result['files']], ['matches', 'missing', 'unverified'])
        absolute = app.digest_status(self.project, {str(self.project / 'result.txt'): expected})
        self.assertEqual(absolute['status'], 'issues')
        self.assertEqual(absolute['files'][0]['status'], 'unverified')
        (self.project / 'result.txt').write_text('changed', encoding='utf-8')
        self.assertEqual(app.digest_status(self.project, {'result.txt': expected})['files'][0]['status'], 'changed')

    def test_absolute_approval_reference_remains_visible_but_unverified(self):
        self.write_control('active_mode: full-contest-harness\nnodes: {H6: {status: approved}}\n')
        artifact = self.project / 'result.txt'
        artifact.write_text('evidence', encoding='utf-8')
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        log = self.project / '.contest' / 'approval_log.yaml'
        log.write_text(app.yaml.safe_dump({'approvals': [{
            'gate': 'H6', 'decision': 'approved',
            'artifact_digests': {str(artifact): digest},
        }]}), encoding='utf-8')
        approval = app.build_state(self.project, self.links)['approvals'][0]
        self.assertEqual(approval['decision'], 'approved')
        self.assertEqual(approval['digests']['status'], 'issues')
        self.assertEqual(approval['digests']['files'][0]['status'], 'unverified')

    def test_invalid_approval_entries_are_reported_without_discarding_valid_ones(self):
        self.write_control('active_mode: full-contest-harness\nnodes: {}\n')
        log = self.project / '.contest' / 'approval_log.yaml'
        log.write_text('approvals: invalid\n', encoding='utf-8')
        result = app.build_state(self.project, self.links)
        self.assertEqual(result['approval_error'], '批准记录列表格式错误')
        self.assertEqual(result['approvals'], [])
        log.write_text('authorization_mode: manual\n', encoding='utf-8')
        result = app.build_state(self.project, self.links)
        self.assertEqual(result['approval_error'], '批准记录列表未登记')
        log.write_text('approvals: []\n', encoding='utf-8')
        self.assertIsNone(app.build_state(self.project, self.links)['approval_error'])
        log.write_text('approvals:\n  - gate: H6\n    decision: approved\n  - invalid\n', encoding='utf-8')
        result = app.build_state(self.project, self.links)
        self.assertEqual(result['approval_error'], '批准记录包含格式错误的条目')
        self.assertEqual(result['approvals'][0]['gate'], 'H6')
        for entry in ['{gate: H7}', '{decision: approved}', '{gate: H7, decision: ""}']:
            log.write_text(f'approvals:\n  - gate: H6\n    decision: approved\n  - {entry}\n', encoding='utf-8')
            result = app.build_state(self.project, self.links)
            self.assertEqual(result['approval_error'], '批准记录包含格式错误的条目')

    def test_duplicate_yaml_fields_never_silently_override_records(self):
        self.write_control('active_mode: full-contest-harness\nactive_mode: another-mode\nnodes: {}\n')
        with self.assertRaisesRegex(ValueError, '重复字段'):
            app.build_state(self.project, self.links)

        self.write_control('active_mode: full-contest-harness\nnodes: {}\n')
        log = self.project / '.contest' / 'approval_log.yaml'
        log.write_text('approvals:\n  - gate: H6\n    decision: rejected\n    decision: approved\n', encoding='utf-8')
        before = log.read_bytes()
        state = app.build_state(self.project, self.links)
        self.assertIn('重复字段', state['approval_error'])
        self.assertEqual(state['approvals'], [])
        self.assertEqual(log.read_bytes(), before)

        log.write_text('defaults: &defaults {gate: H6, decision: rejected}\n'
                       'approvals:\n  - <<: *defaults\n    decision: approved\n', encoding='utf-8')
        state = app.build_state(self.project, self.links)
        self.assertIsNone(state['approval_error'])
        self.assertEqual(state['approvals'][0]['decision'], 'approved')

    def test_existing_report_is_displayed_as_recorded_not_recomputed(self):
        report = self.project / 'report.json'
        report.write_text(json.dumps({'passed': False, 'issues': ['build failed']}), encoding='utf-8')
        result = app.read_report(self.project, 'report.json', 'Compile')
        self.assertFalse(result['passed'])
        self.assertEqual(result['issues'], ['build failed'])
        self.assertIsNotNone(result['modified'])
        for content in ('{"passed": false, "passed": true}', '{"passed": true, "details": {"status": "failed", "status": "passed"}}'):
            report.write_text(content, encoding='utf-8')
            before = report.read_bytes()
            result = app.read_report(self.project, 'report.json', 'Compile')
            self.assertIsNone(result['passed'])
            self.assertIn('重复字段', result['error'])
            self.assertEqual(report.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
