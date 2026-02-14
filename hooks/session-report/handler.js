import { execFile } from "node:child_process";

const SCRIPT = "/root/.openclaw/workspace/agent-monitoring-system/send_session_report.py";

const sendSessionReport = async (event) => {
    // /new → action="new", /reset → action="reset"
    if (event.type !== "command" || !["new", "reset"].includes(event.action)) return;

    console.log(`[session-report] hook triggered (action=${event.action}), running send_session_report.py …`);

    try {
        await new Promise((resolve, reject) => {
            execFile("python3", [SCRIPT], { timeout: 30_000 }, (err, stdout, stderr) => {
                if (stdout) console.log("[session-report]", stdout.trim());
                if (stderr) console.error("[session-report]", stderr.trim());
                if (err) reject(err); else resolve();
            });
        });
        console.log("[session-report] done");
    } catch (err) {
        console.error("[session-report] hook failed:", err.message || err);
    }
};

export default sendSessionReport;
