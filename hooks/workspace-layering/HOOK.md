---
name: workspace-layering
description: "Enforce core workspace files as immutable base layer for multi-tenant isolation"
metadata:
  {
    "openclaw":
      {
        "emoji": "🔒",
        "events": ["agent:bootstrap"],
        "requires": { "config": ["workspace.dir"] },
      },
  }
---

# Workspace Layering Hook

Implements a two-layer workspace architecture:

1. **Core layer** (shared workspace) — immutable principles that cannot be overridden by tenants
2. **Tenant layer** (agent workspace) — per-tenant customization that supplements (but never replaces) core content

## Security Design

| File | Policy | Reason |
|------|--------|--------|
| SOUL.md | core-only | Persona + safety boundaries |
| TOOLS.md | core-only | Tool usage rules |
| HEARTBEAT.md | core-only | Monitoring behavior |
| IDENTITY.md | core + tenant | Base identity + tenant additions |
| AGENTS.md | core + tenant | Base agent config + tenant extensions |
| BOOTSTRAP.md | core + tenant | Base bootstrap + tenant steps |
| USER.md | tenant-only | Personal data (sharing = data leak) |
| MEMORY.md | tenant-only | Conversation memory (sharing = data leak) |
