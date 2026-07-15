# Daily-Use Flow Diagrams

Mirrors `tools/build-release/INSTALL.md`'s "Daily use" step lists exactly. If those
steps change, update this file too.

## Docs-only flow (`source_of_truth: docs-only`, or absent)

```mermaid
flowchart
    A["git checkout -b story/&lt;name&gt;"] --> B{"openspec SDD?"}
    B -- yes --> C["/opsx:propose &lt;change&gt;<br/>(before kickoff, for a real<br/>Phase-1 point estimate)"]
    B -- no --> D
    C --> D["'kick off this story'<br/>(chat) → writes .story.yaml"]
    D --> E{"openspec SDD?"}
    E -- yes --> F["/opsx:apply"]
    E -- no --> G
    F --> G["Work normally —<br/>commits/checkouts/AI sessions<br/>captured silently"]
    G --> H["Commit + push"]
    H --> I{"openspec SDD?"}
    I -- yes --> J["opsx-wrapper archive &lt;change&gt;<br/>(archives + snapshots in one)"]
    I -- no --> K["snapshot-assembler"]
    J --> L["snapshots/&lt;story-id&gt;.json"]
    K --> L
    L --> M["(optional) metrics-report"]
    L --> N["(optional) dashboard"]
```

## JIRA flow (`source_of_truth: jira`)

```mermaid
flowchart
    A["git checkout -b story/&lt;name&gt;"] --> B["'kick off this story &lt;ISSUE-KEY&gt;'<br/>→ Atlassian MCP fetches points/goal/sprint<br/>→ writes .story.yaml"]
    B --> C{"openspec SDD?"}
    C -- yes --> D["/opsx:propose &lt;change&gt;<br/>(AFTER kickoff — no JIRA-fetch<br/>capability of its own)"]
    C -- no --> E
    D --> E{"openspec SDD?"}
    E -- yes --> F["/opsx:apply"]
    E -- no --> G
    F --> G["Work normally —<br/>same silent capture"]
    G --> H["Commit + push"]
    H --> I{"openspec SDD?"}
    I -- yes --> J["opsx-wrapper archive &lt;change&gt;"]
    I -- no --> K["snapshot-assembler"]
    J --> L["snapshots/&lt;story-id&gt;.json"]
    K --> L
    L --> M["(optional) metrics-report"]
    L --> N["(optional) dashboard"]
```

**The one real structural difference:** JIRA's kickoff must run **before**
`/opsx:propose` (no JIRA-fetch capability of its own — it would otherwise fall
back to unauthenticated `WebFetch`, which can't reach an authenticated Atlassian
page). Docs-only runs `/opsx:propose` **before** kickoff instead, so the Phase-1
estimator has a real `tasks.md` to read.

## Release testing checklist (JIRA, fresh-install round)

This is the pilot-testing procedure used to verify a fresh release end-to-end
(re-installing from scratch, not the normal per-story flow a developer follows —
a real developer installs once and skips straight to "Daily use" above for every
subsequent story).

```mermaid
flowchart
    A["Uninstall (uninstall.ps1/.sh)"] --> B["Confirm .claude/settings.json<br/>and .story-config.yaml removed"]
    B --> C["Re-install fresh<br/>(install.ps1/.sh, latest release)"]
    C --> D["uv run tools/setup-hooks.py --repo-root ."]
    D --> E["Confirm hooks wired into<br/>.claude/settings.json"]
    E --> F["Confirm/set .story-config.yaml:<br/>source_of_truth: jira"]
    F --> G["Confirm .story.yaml absent<br/>(no story left open)"]
    G --> H["claude mcp add --transport http atlassian ..."]
    H --> I["git checkout -b story/&lt;name&gt;"]
    I --> J["Invoke story-kickoff,<br/>give it a JIRA issue key"]
    J --> K["Confirm points/goal/sprint"]
    K --> L["Confirm .story.yaml written<br/>(source_of_truth: jira + issue key)"]
    L --> M["Do real work —<br/>commits, normal coding session"]
    M --> N["(optional) trigger a real<br/>test/build failure"]
    N --> O["(optional) log-defect →<br/>real JIRA subtask"]
    O --> P["End session<br/>(close chat window)"]
    P --> Q["Close the story —<br/>snapshot-assembler"]
    Q --> R["metrics-report"]
    R --> S["dashboard"]
    S --> T["Paste back snapshot/report/dashboard<br/>for verification"]
```
