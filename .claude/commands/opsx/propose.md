---
name: "OPSX: Propose"
description: Propose a new change - create it and generate all artifacts in one step
category: Workflow
tags: [workflow, artifacts, experimental]
---

Propose a new change - create the change and generate all artifacts in one step.

I'll create a change with artifacts:
- proposal.md (what & why)
- design.md (how)
- tasks.md (implementation steps)

When ready to implement, run /opsx:apply

---

**Input**: The argument after `/opsx:propose` is the change name (kebab-case), OR a description of what the user wants to build.

**Steps**

1. **If no input provided, ask what they want to build**

   Use the **AskUserQuestion tool** (open-ended, no preset options) to ask:
   > "What change do you want to work on? Describe what you want to build or fix."

   From their description, derive a kebab-case name (e.g., "add user authentication" → `add-user-auth`).

   **IMPORTANT**: Do NOT proceed without understanding what the user wants to build.

2. **Find similar existing specs and their requirements**

   a. **Extract exactly 4 descriptive tags from the user's description**

      From the description in step 1, derive exactly 4 short descriptive phrases (2–4 words each). Each tag should capture a distinct concept or aspect of the change — not single words.

   b. **Search 1 — find similar specs (no parent filter)**

      Join them with `|` as the separator:
      ```bash
      openspec kg search --text "<tag1>|<tag2>|<tag3>|<tag4>" --node-type spec --k 5 --json
      ```

      Save the returned `matches` as **spec matches**. Collect their `id` fields (e.g. `"spec:user-notifications"`).

   c. **Search 2 — find requirements that are children of those specs**

      If search 1 returned any matches, run a second search scoped to their children:
      ```bash
      openspec kg search --text "<tag1>|<tag2>|<tag3>|<tag4>" --node-type requirement --parent-ids "<id1>,<id2>,..." --k 10 --json
      ```
      where `--parent-ids` is the comma-separated list of spec IDs from search 1.

      Save the returned `matches` as **requirement matches**. Skip if search 1 returned 0 matches.

   d. **Use the combined context when drafting artifacts**

      From **spec matches**, extract and hold onto:
      - `id` — the spec's id (e.g. "spec:user-notifications")
      - `text` — the spec's summary (what it does)
      - `intent.text` — why the spec exists (from the proposal's Why section)
      - `matchedQueryTag` / `matchedNodeTag` — which query word matched which spec tag

      From **requirement matches**, extract and hold onto:
      - `id` — the requirement's id
      - `text` — what the requirement specifies
      - `matchedQueryTag` / `matchedNodeTag` — which concept matched

      Apply this context when drafting **proposal.md**, **spec**, and **design.md**:

      - In **proposal.md — Why section**:
        1. Open with a 1–2 sentence problem statement explaining why this change is needed.
        2. Add a "### Related Specs" subsection. For each related spec match write:
           > **`<id>`** — <text>. _Why it exists: <intent.text>._ This change [extends / builds on / complements] that spec by <specific relationship>.
        3. Close the Why section with a 1–2 sentence synthesis: how the related specs collectively motivate this change's scope and priority.
        4. If no related specs were found, write the Why section from first principles only.

      - In **spec** (requirements):
        - Where a new requirement reuses or adapts a pattern from a related requirement match, append a parenthetical reference: `(adapts <requirement-id>)`
        - Where new requirements build on an existing spec's behavior, open that requirements group with a blockquote: `> Extends: <spec-id>`
        - Draw on the related requirement `text` to stay consistent in language, scope, and acceptance criteria style.

      - In **design.md**:
        - Add a "## Related Work" section near the top. For each related spec write:
          > **`<id>`**: <text> — informs [specific design decision] because <intent.text>.
        - When a design decision was directly shaped by a related spec, add an inline citation in that section: _(see `<spec-id>`)_

   - If either search errors or returns 0 matches, continue silently without that context.

3. **Create the change directory**
   ```bash
   openspec new change "<name>"
   ```
   This creates a scaffolded change at `openspec/changes/<name>/` with `.openspec.yaml`.

   **If related specs were found in step 2**, write their IDs to a file so the archive step can create graph edges:
   - Collect the `id` field from each match (e.g. `"spec:user-notifications"`)
   - Write them as a JSON array to `openspec/changes/<name>/related-specs.json`

   Example:
   ```json
   ["spec:user-notifications", "spec:auth"]
   ```

4. **Get the artifact build order**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to get:
   - `applyRequires`: array of artifact IDs needed before implementation (e.g., `["tasks"]`)
   - `artifacts`: list of all artifacts with their status and dependencies

5. **Create artifacts in sequence until apply-ready**

   Use the **TodoWrite tool** to track progress through the artifacts.

   Loop through artifacts in dependency order (artifacts with no pending dependencies first):

   a. **For each artifact that is `ready` (dependencies satisfied)**:
      - Get instructions:
        ```bash
        openspec instructions <artifact-id> --change "<name>" --json
        ```
      - The instructions JSON includes:
        - `context`: Project background (constraints for you - do NOT include in output)
        - `rules`: Artifact-specific rules (constraints for you - do NOT include in output)
        - `template`: The structure to use for your output file
        - `instruction`: Schema-specific guidance for this artifact type
        - `outputPath`: Where to write the artifact
        - `dependencies`: Completed artifacts to read for context
      - Read any completed dependency files for context
      - Create the artifact file using `template` as the structure
      - Apply `context` and `rules` as constraints - but do NOT copy them into the file
      - If related specs/requirements were found in step 2, apply the structured format from step 2d: "### Related Specs" block in proposal.md Why section, `(adapts <id>)` / `> Extends: <id>` annotations in spec requirements, and "## Related Work" section in design.md
      - Show brief progress: "Created <artifact-id>"

   b. **Continue until all `applyRequires` artifacts are complete**
      - After creating each artifact, re-run `openspec status --change "<name>" --json`
      - Check if every artifact ID in `applyRequires` has `status: "done"` in the artifacts array
      - Stop when all `applyRequires` artifacts are done

   c. **If an artifact requires user input** (unclear context):
      - Use **AskUserQuestion tool** to clarify
      - Then continue with creation

6. **Show final status**
   ```bash
   openspec status --change "<name>"
   ```

**Output**

After completing all artifacts, summarize:
- Change name and location
- List of artifacts created with brief descriptions
- If similar specs were found, list them as "Related specs: [labels]"
- What's ready: "All artifacts created! Ready for implementation."
- Prompt: "Run `/opsx:apply` to start implementing."

**Artifact Creation Guidelines**

- Follow the `instruction` field from `openspec instructions` for each artifact type
- The schema defines what each artifact should contain - follow it
- Read dependency artifacts for context before creating new ones
- Use `template` as the structure for your output file - fill in its sections
- **IMPORTANT**: `context` and `rules` are constraints for YOU, not content for the file
  - Do NOT copy `<context>`, `<rules>`, `<project_context>` blocks into the artifact
  - These guide what you write, but should never appear in the output

**Guardrails**
- Create ALL artifacts needed for implementation (as defined by schema's `apply.requires`)
- Always read dependency artifacts before creating a new one
- If context is critically unclear, ask the user - but prefer making reasonable decisions to keep momentum
- If a change with that name already exists, ask if user wants to continue it or create a new one
- Verify each artifact file exists after writing before proceeding to next
