# Slice 034 P2 — code review r1

Range: JenkinsPipelineUtils `d9ff168..197b9a3` (branch `phase/034-P2`). Gate: green on `197b9a3`
(`gate_r1.log`: root Maven suite, `docs` strict build, `check_site.py`).

**Ready to merge; nothing to fix.** Each of P2's outcomes is in the diff:

- **Strict build from a locked toolchain.** `docs/pyproject.toml` with `uv.lock`, run with
  `uv run --locked`.
- **The address.** `site_url: https://pipelines.home/docs/` (`docs/mkdocs.yml:20`).
- **The pages.** A docs home (`docs/pages/index.md`), the landing page source with relative
  `docs/` and `docs/llms.txt` links (`docs/landing/index.html:36-40`), and no guide page (nav is
  `Home` alone, `docs/mkdocs.yml:70-71`).
- **The LLM support.** The manual's llmstxt block, with its single `"*.md"` pattern and
  `llms-full.txt`, and its four validation promotions come over as they are
  (`docs/mkdocs.yml:36-66` against KubeCoder `manual/mkdocs.yml:43-72`).
- **Left out, as the plan says.** The start-time `site_url` rewrite, the CLI reference and the
  VSIX.
- **In the gate.** The `docs` component's default working directory is `docs/`, so
  `kc project test` runs the build (`.kubecoder/project.yaml:19-29`).
- **The manifest.** Its header comment is still true.

**Probes (none needed a finding):**

- **A realistic second page.** I copied the tree to scratch and added a nested
  `guide/stages.md`: a cross-page `#anchor` link, a table and a ```` ```groovy ```` block. The
  strict build and `check_site.py` both passed, and the Markdown copy landed at
  `guide/stages/index.md`, which is the URL llms.txt lists.
- **Does `check_site.py` really check llms.txt and llms-full.txt?** The executor's red run never
  reached these two checks, because it stopped at the missing copy first. I removed the page's
  entry from the built `llms.txt` and its text from `llms-full.txt`: each check failed on its
  own, exit 1.
- **The docs-home check.** I changed the landing link to `href="docs"`. The check failed, exit 1.
- **Is the lock safe from MkDocs 2.0?** The build prints Material's MkDocs 2.0 warning, but
  mkdocs-material 9.7.7 requires `mkdocs<2,>=1.6`, so re-locking cannot pull MkDocs 2.0 in.

## Findings

None.
