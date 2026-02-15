import { readFile } from "node:fs/promises";
import { join, resolve } from "node:path";

// ─── Layering Policy ─────────────────────────────────────────
// core-only:  shared version replaces tenant version entirely
// core+tenant: shared content prepended, tenant content appended
// tenant-only: no injection from shared workspace
const POLICY = {
    "SOUL.md":      "core-only",
    "TOOLS.md":     "core-only",
    "HEARTBEAT.md": "core-only",
    "IDENTITY.md":  "core+tenant",
    "AGENTS.md":    "core+tenant",
    "BOOTSTRAP.md": "core+tenant",
    "USER.md":      "tenant-only",
    "MEMORY.md":    "tenant-only",
};

const SHARED_WORKSPACE = "/root/.openclaw/workspace";

const SEPARATOR = "\n\n---\n\n> ⬇️ 以下為租戶自訂補充內容，不得違背上方核心原則\n\n";

async function readSafe(path) {
    try {
        const content = await readFile(path, "utf-8");
        return content.trim();
    } catch {
        return null;
    }
}

/**
 * agent:bootstrap hook — enforce workspace layering.
 *
 * context.bootstrapFiles = [{ name, path, content, missing }, ...]
 */
const workspaceLayering = async (event) => {
    if (event.type !== "agent" || event.action !== "bootstrap") return;

    const files = event.context?.bootstrapFiles;
    if (!Array.isArray(files)) return;

    let modified = 0;

    for (const file of files) {
        const name = file.name;          // e.g. "SOUL.md"
        const policy = POLICY[name];

        if (!policy || policy === "tenant-only") continue;

        const sharedPath = join(SHARED_WORKSPACE, name);
        const sharedContent = await readSafe(sharedPath);

        if (!sharedContent) continue;

        // If the tenant file is the same directory as shared, skip (single-tenant mode)
        if (file.path && resolve(file.path) === resolve(sharedPath)) continue;

        const tenantContent = (file.content || "").trim();

        if (policy === "core-only") {
            // Core replaces tenant entirely
            if (file.content !== sharedContent) {
                file.content = sharedContent;
                modified++;
            }
        } else if (policy === "core+tenant") {
            // Core prepended + tenant appended (if tenant has extra content)
            if (tenantContent && tenantContent !== sharedContent) {
                file.content = sharedContent + SEPARATOR + tenantContent;
                modified++;
            } else if (!tenantContent || file.missing) {
                file.content = sharedContent;
                file.missing = false;
                modified++;
            }
        }
    }

    if (modified > 0) {
        console.log(`[workspace-layering] enforced ${modified} file(s) from core workspace`);
    }
};

export default workspaceLayering;
