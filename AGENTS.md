# AGENTS.md

AI Jargon Atlas is a pipeline that produces short bilingual (EN + KR) educational
videos explaining AI jargon, each starring a pixel-art mascot named Atlas. Episodes
are defined by a small YAML in `episodes_yaml/` and built in three stages via the
`atlas` CLI: **stage 1** generates a bilingual `script.json`, **stage 2** generates
pixel-art images, **stage 3** generates voiceover and assembles the video. Source
lives in `src/atlas_pipeline/`; see `README.md` for the full workflow.

## Writing or editing an episode script

`script.json` drives everything downstream, so it's worth refining carefully before
running stages 2–3. To generate or edit an episode's script by chatting, follow the
procedure in **`.claude/skills/episode-script/SKILL.md`** — it documents the schema,
the editorial rules (beats, pacing, bilingual voice, Atlas poses), the file
conventions, and how to validate. In Claude Code this is also available as the
`/episode-script` skill.
