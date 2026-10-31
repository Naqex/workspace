# External integrations

These directories are independent upstream repositories or Naqex forks, linked
as submodules. Keep upstream layout, licenses and attribution. Products developed
here remain under `projects/` alongside this integration group.

For adoption, fork, relocation or upgrade, use the workspace skill
`upstream-integrations` and read `../../tooling/integrations/README.md`.
The catalog routes to source owners; workspace gitlinks pin source versions.
Read each repository's own AGENTS/rules before changing or running it.

Source adoption, dependencies, embedded UI and actual engine jobs are separate
acceptance states. A chosen engine has no implicit right to dispatch model or
broker work. Runtime data/secrets belong in their configured local instance,
not in a source checkout; new services use the existing local-services contract.

If a nested upstream instruction assumes that this agent runs inside a Paperclip
task, apply its issue/artifact API workflow only to that real task. A Codex source
integration task does not create a Paperclip job merely to report its own work.
