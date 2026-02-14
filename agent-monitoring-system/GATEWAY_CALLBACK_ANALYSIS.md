# OpenClaw Gateway — callback_query Handling Deep Analysis

**Source file**: `/usr/lib/node_modules/openclaw/dist/reply-DptDUVRg.js` (65,170 lines)  
**Framework**: grammY (Telegram bot framework for Node.js)

---

## 1. callback_query Handler (Line 35863)

The **single** callback_query handler is registered at **line 35863**:

```js
// Line 35863-36094
bot.on("callback_query", async (ctx) => {
    const callback = ctx.callbackQuery;
    if (!callback) return;
    if (shouldSkipUpdate(ctx)) return;

    // IMMEDIATELY answers the callback (ACK to Telegram) — no filtering
    await withTelegramApiErrorLogging({
        operation: "answerCallbackQuery",
        runtime,
        fn: () => bot.api.answerCallbackQuery(callback.id)
    }).catch(() => {});

    try {
        const data = (callback.data ?? "").trim();
        const callbackMessage = callback.message;
        if (!data || !callbackMessage) return;

        // Check inlineButtons scope
        const inlineButtonsScope = resolveTelegramInlineButtonsScope({ cfg, accountId });
        if (inlineButtonsScope === "off") return;

        // Chat type filtering
        const chatId = callbackMessage.chat.id;
        const isGroup = callbackMessage.chat.type === "group" || callbackMessage.chat.type === "supergroup";
        if (inlineButtonsScope === "dm" && isGroup) return;
        if (inlineButtonsScope === "group" && !isGroup) return;

        // ... allowFrom / groupPolicy checks (lines 35886-35957) ...

        // --- SPECIAL CASE 1: Commands pagination (line 35972) ---
        const paginationMatch = data.match(/^commands_page_(\d+|noop)(?::(.+))?$/);
        if (paginationMatch) {
            // Handles pagination — edits the message with new page, returns early
            return;
        }

        // --- SPECIAL CASE 2: Model selection (line 35996) ---
        const modelCallback = parseModelCallbackData(data);
        if (modelCallback) {
            // Handles mdl_prov, mdl_back, mdl_list_*, mdl_sel_* — returns early
            return;
        }

        // --- FALLTHROUGH: ALL other callback_data → synthetic message to AI ---
        const syntheticMessage = {
            ...callbackMessage,
            from: callback.from,
            text: data,          // callback_data becomes the message text!
            caption: void 0,
            caption_entities: void 0,
            entities: void 0
        };
        const getFile = typeof ctx.getFile === "function" ? ctx.getFile.bind(ctx) : async () => ({});
        await processMessage({
            message: syntheticMessage,
            me: ctx.me,
            getFile
        }, [], storeAllowFrom, {
            forceWasMentioned: true,
            messageIdOverride: callback.id
        });
    } catch (err) {
        runtime.error?.(danger(`callback handler failed: ${String(err)}`));
    }
});
```

### Key finding: **NO callback_data prefix filtering exists**

The flow is:
1. Dedupe check (`shouldSkipUpdate`) — only skips duplicate update IDs
2. **`answerCallbackQuery` is called IMMEDIATELY** for ALL callbacks — before any data inspection
3. Empty data or missing message → return
4. `inlineButtonsScope` check (off/dm/group/allowlist)
5. allowFrom / groupPolicy access control
6. Check for `commands_page_*` prefix → handle pagination
7. Check for `mdl_*` prefix → handle model selection
8. **Everything else** → create synthetic message with `text: data` and send to AI

**Any callback_data starting with "m:" will fall through to step 8 and be sent to the AI as a synthetic message.**

---

## 2. inlineButtons / inlineButtonsScope Configuration (Lines 5516-5548)

```js
// Line 5516
const DEFAULT_INLINE_BUTTONS_SCOPE = "allowlist";

// Line 5517-5521
function normalizeInlineButtonsScope(value) {
    if (typeof value !== "string") return;
    const trimmed = value.trim().toLowerCase();
    if (trimmed === "off" || trimmed === "dm" || trimmed === "group" ||
        trimmed === "all" || trimmed === "allowlist") return trimmed;
    // Returns undefined for any unrecognized value!
}

// Line 5522-5529
function resolveInlineButtonsScopeFromCapabilities(capabilities) {
    if (!capabilities) return DEFAULT_INLINE_BUTTONS_SCOPE;
    if (Array.isArray(capabilities))
        return capabilities.some(entry => String(entry).trim().toLowerCase() === "inlinebuttons") ? "all" : "off";
    if (typeof capabilities === "object") {
        const inlineButtons = capabilities.inlineButtons;
        return normalizeInlineButtonsScope(inlineButtons) ?? DEFAULT_INLINE_BUTTONS_SCOPE;
    }
    return DEFAULT_INLINE_BUTTONS_SCOPE;
}

// Line 5531-5534
function resolveTelegramInlineButtonsScope(params) {
    return resolveInlineButtonsScopeFromCapabilities(
        resolveTelegramAccount({ cfg: params.cfg, accountId: params.accountId }).config.capabilities
    );
}
```

### Supported values for `capabilities.inlineButtons`:

| Value | Meaning |
|-------|---------|
| `"off"` | Inline buttons completely disabled — callback_query handler returns immediately |
| `"dm"` | Only process callbacks in DMs (private chats) |
| `"group"` | Only process callbacks in groups/supergroups |
| `"all"` | Process callbacks everywhere ← **your current config** |
| `"allowlist"` | Only process callbacks for users in the allowlist (default) |

**There is NO pattern-based filter option.** No "ignore prefix" feature exists. The value `"all"` means every callback_data is processed.

---

## 3. Synthetic Message Creation (Lines 36070-36090)

```js
// Line 36070-36090 — the fallthrough after commands_page_ and mdl_ checks
const syntheticMessage = {
    ...callbackMessage,
    from: callback.from,
    text: data,                    // callback_data becomes message text
    caption: void 0,
    caption_entities: void 0,
    entities: void 0
};
const getFile = typeof ctx.getFile === "function" ? ctx.getFile.bind(ctx) : async () => ({});
await processMessage({
    message: syntheticMessage,
    me: ctx.me,
    getFile
}, [], storeAllowFrom, {
    forceWasMentioned: true,       // Forces processing as if bot was @mentioned
    messageIdOverride: callback.id
});
```

**There is ZERO filtering/skipping logic between the `mdl_*` check and the synthetic message creation.** Any callback_data that doesn't match `commands_page_*` or `mdl_*` is unconditionally forwarded to the AI.

---

## 4. answerCallbackQuery (Line 35868)

```js
// Line 35866-35871
await withTelegramApiErrorLogging({
    operation: "answerCallbackQuery",
    runtime,
    fn: () => bot.api.answerCallbackQuery(callback.id)
}).catch(() => {});
```

**Always called, for ALL callbacks, BEFORE any data inspection.** This means:
- Telegram gets an ACK for every button click
- The loading spinner on the button always resolves
- Even if the handler later returns early (empty data, scope check), the callback is already answered

---

## 5. Prefix-Based Filtering — NONE EXISTS

The only prefix-based routing in the callback handler:

| Prefix | Check | Line |
|--------|-------|------|
| `commands_page_*` | `data.match(/^commands_page_(\d+\|noop)(?::(.+))?$/)` | 35972 |
| `mdl_*` | `parseModelCallbackData(data)` — checks for `mdl_prov`, `mdl_back`, `mdl_list_*`, `mdl_sel_*` | 35996 |

**No check exists for "m:" prefix or any other custom pattern.** All other data falls through to `processMessage()`.

---

## 6. getUpdates Processing (Lines 38233, 38259)

```js
// Line 32537-32541
function resolveTelegramAllowedUpdates() {
    const updates = [...API_CONSTANTS.DEFAULT_UPDATE_TYPES];
    if (!updates.includes("message_reaction")) updates.push("message_reaction");
    return updates;
}
```

grammY's `API_CONSTANTS.DEFAULT_UPDATE_TYPES` includes `"callback_query"`. There is **no way** to exclude callback_query from the update types via configuration — it's hardcoded.

The `allowed_updates` parameter is passed to Telegram's getUpdates at lines 38233 and 38259:
```js
allowed_updates: resolveTelegramAllowedUpdates()
```

---

## 7. Configuration Schema — No Undocumented Options

From the prompt template at line 33216:
```js
params.inlineButtonsEnabled
    ? "- Inline buttons supported. Use `action=send` with `buttons=[[{text,callback_data}]]` (callback_data routes back as a user message)."
    : params.runtimeChannel
        ? `- Inline buttons not enabled for ${params.runtimeChannel}. If you need them, ask to set ${params.runtimeChannel}.capabilities.inlineButtons ("dm"|"group"|"all"|"allowlist").`
        : ""
```

The documentation explicitly lists only: `"dm"`, `"group"`, `"all"`, `"allowlist"`. Combined with `"off"` from the normalizer — that's the complete set. **No undocumented options exist.**

---

## 8. CONCLUSION: Can Gateway Be Configured to Ignore "m:" Callbacks?

### Answer: **NO — not through configuration.**

The Gateway has no mechanism to:
- Filter callback_data by prefix/pattern
- Ignore specific callback_data values
- Configure a skip list or ignore list for callbacks
- Exclude certain callback patterns from processing

The only options are:
1. **`"off"`** — disables ALL inline button callback processing (you lose ALL button functionality)
2. **`"dm"` / `"group"` / `"allowlist"`** — scope by chat type or user, not by data content

### Minimal Code Change to Enable "m:" Filtering

Add **2 lines** to the callback_query handler at line 35972 (just before the `commands_page_` check):

```js
// Add after line 35884 ("if (inlineButtonsScope === "group" && !isGroup) return;")
// or more precisely, just before line 35972 (the paginationMatch):

if (data.startsWith("m:")) return;  // Skip menu navigation callbacks
```

**Exact insertion point** — between lines 35971 and 35972:

```diff
                        }
+                       if (data.startsWith("m:")) return;
                        const paginationMatch = data.match(/^commands_page_(\d+|noop)(?::(.+))?$/);
```

This would:
- Skip "m:*" callbacks before they create a synthetic message
- Still allow `answerCallbackQuery` to fire (button won't show loading forever)
- Not affect `commands_page_*` or `mdl_*` handling
- Be the least invasive change possible

### Alternative: Configurable prefix ignore list

For a more robust solution, add a config option like:
```json
{
  "channels": {
    "telegram": {
      "capabilities": {
        "inlineButtons": "all",
        "inlineButtonsIgnorePrefixes": ["m:"]
      }
    }
  }
}
```

Then in the handler:
```js
const ignorePrefixes = telegramCfg.capabilities?.inlineButtonsIgnorePrefixes ?? [];
if (ignorePrefixes.length > 0 && ignorePrefixes.some(p => data.startsWith(p))) return;
```

---

## Summary Table

| Question | Answer |
|----------|--------|
| Can Gateway ignore "m:" callbacks via config? | **No** |
| What does `inlineButtons: "all"` do? | Processes ALL callback_data in all chat types |
| Is there prefix-based filtering? | Only for `commands_page_*` and `mdl_*` (Gateway's own buttons) |
| Does `answerCallbackQuery` always fire? | **Yes**, before any data inspection |
| Where is synthetic message created? | Lines 36070-36090 — `text: data` |
| Minimal fix location? | Line 35971 — add `if (data.startsWith("m:")) return;` |
