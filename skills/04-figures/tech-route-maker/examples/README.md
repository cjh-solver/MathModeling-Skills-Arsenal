# Examples And Gallery

This gallery shows the core research and engineering scenarios supported by `tech-route-maker`. The public copy includes the scenario briefs and one [editable academic example](out/). Other generated demo outputs are not included.

The optional `assets/github-visual-preview.png` image on the repository homepage is a generated visual preview only. It is not used as the editable diagram source.

| Demo | Audience | Layout | Style | Preview |
|---|---|---|---|---|
| [Academic paper method route](academic-paper-demo/) | Chinese paper or defense | Chinese research method matrix | Blue-green proposal | [SVG](out/tech-route.svg) |
| [Thesis proposal technical route](thesis-proposal-demo/) | Chinese thesis, opening report, research plan | Chinese proposal poster route | Polished pastel academic | Brief only |
| [Chinese grant application route](chinese-grant-application-demo/) | Grant, project application, reviewer-facing route | Chinese grant application route | Soft grant report | Brief only |
| [Engineering energy system route](engineering-energy-system-demo/) | Engineering report or course design | Chinese wide project map | Blue-green proposal | Brief only |
| [Biomedical mechanism route](biomedical-mechanism-demo/) | Biomedical proposal or paper | Chinese proposal poster route | Polished pastel academic | Brief only |
| [Draw.io copy-code HGDY route](drawio-copy-code-demo/) | Project application / Draw.io handoff | Chinese grant application route | Soft grant report | Brief only |
| [Agent workflow route](agent-workflow-demo/) | Skill/tool documentation | Horizontal stages | Minimal gray | Brief only |

## Legacy / Experimental

`legacy-campaign-route-demo/` is retained for users who explicitly need campaign or advertising route diagrams. It is not part of the default gallery.

## Render the Included Example

From the skill directory:

```bash
python scripts/render_all.py examples/out/tech-route.json work/example-output --formats svg,drawio-code,json
```

The output is illustrative and still requires factual and visual review before formal use.

## What To Compare

- PPTX: editable slide shapes.
- SVG: vector preview and design-tool editing.
- Draw.io: long-term technical maintenance.
- Draw.io code: copy `tech-route.drawio-code.xml` into [diagrams.net / draw.io](https://app.diagrams.net/) through **Extras > Edit Diagram**.
- HTML: interactive reading and evidence inspection.
- JSON: source of truth for rerendering.
- `QUALITY_REPORT.md`: warnings and manual review checklist.
