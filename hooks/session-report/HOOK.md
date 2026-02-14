---
name: session-report
description: "Send dev daily report and monitoring dashboard on session reset"
metadata:
  {
    "openclaw":
      {
        "emoji": "📊",
        "events": ["command:new", "command:reset"],
        "requires": { "config": ["workspace.dir"] },
      },
  }
---

# Session Report Hook

Automatically sends the dev daily report and monitoring dashboard when a new session starts (via `/reset` or `/new`).
