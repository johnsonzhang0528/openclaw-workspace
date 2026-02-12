#!/usr/bin/env python3
"""
Patch OpenClaw to enable enforceFinalTag for DeepSeek provider.

When enforceFinalTag is enabled:
- System automatically injects <think>/<final> tag instructions into system prompt
- ONLY text inside <final> tags is shown to the user
- All intermediate text (reasoning, narration) is silently discarded

This eliminates the "message spam" issue on Telegram where every
intermediate text segment before a tool call becomes a separate message.

Usage:
    python3 patch_enforceFinalTag.py          # Apply patch
    python3 patch_enforceFinalTag.py --check  # Check if patch is needed
    python3 patch_enforceFinalTag.py --revert # Revert patch

Note: Re-run this script after every OpenClaw update (npm update -g openclaw)
"""

import glob
import sys
import os

OPENCLAW_DIST = "/usr/lib/node_modules/openclaw/dist/"

# The original pattern (before patch)
ORIGINAL = 'if (normalized.includes("minimax")) return true;\n\treturn false;\n}'

# The patched version (with deepseek added)
PATCHED = 'if (normalized.includes("minimax")) return true;\n\tif (normalized === "deepseek") return true;\n\treturn false;\n}'


def find_js_files():
    """Find all JS files that contain isReasoningTagProvider."""
    files = []
    for f in glob.glob(os.path.join(OPENCLAW_DIST, "**/*.js"), recursive=True):
        with open(f, "r") as fh:
            content = fh.read()
        if "isReasoningTagProvider" in content:
            files.append(f)
    return files


def check_status():
    """Check if patch is applied, needed, or has conflicts."""
    files = find_js_files()
    if not files:
        print("ERROR: No OpenClaw JS files found with isReasoningTagProvider")
        return 2

    for f in files:
        with open(f, "r") as fh:
            content = fh.read()
        basename = os.path.basename(f)
        if PATCHED in content:
            print(f"  ✅ {basename}: already patched")
        elif ORIGINAL in content:
            print(f"  ⚠️  {basename}: needs patching")
        else:
            print(f"  ❌ {basename}: unexpected content (manual check needed)")
    return 0


def apply_patch():
    """Apply the patch to all relevant files."""
    files = find_js_files()
    if not files:
        print("ERROR: No OpenClaw JS files found")
        return 1

    patched_count = 0
    for f in files:
        with open(f, "r") as fh:
            content = fh.read()
        basename = os.path.basename(f)
        if PATCHED in content:
            print(f"  ⏭️  {basename}: already patched, skipping")
            continue
        if ORIGINAL not in content:
            print(f"  ❌ {basename}: pattern not found, skipping")
            continue
        content = content.replace(ORIGINAL, PATCHED)
        with open(f, "w") as fh:
            fh.write(content)
        patched_count += 1
        print(f"  ✅ {basename}: patched successfully")

    print(f"\nPatched {patched_count} file(s)")
    if patched_count > 0:
        print("⚠️  Remember to restart the Gateway: systemctl --user restart openclaw-gateway")
    return 0


def revert_patch():
    """Revert the patch from all relevant files."""
    files = find_js_files()
    reverted = 0
    for f in files:
        with open(f, "r") as fh:
            content = fh.read()
        basename = os.path.basename(f)
        if ORIGINAL in content:
            print(f"  ⏭️  {basename}: not patched, skipping")
            continue
        if PATCHED not in content:
            print(f"  ❌ {basename}: unexpected content, skipping")
            continue
        content = content.replace(PATCHED, ORIGINAL)
        with open(f, "w") as fh:
            fh.write(content)
        reverted += 1
        print(f"  ↩️  {basename}: reverted successfully")

    print(f"\nReverted {reverted} file(s)")
    if reverted > 0:
        print("⚠️  Remember to restart the Gateway: systemctl --user restart openclaw-gateway")
    return 0


if __name__ == "__main__":
    print("OpenClaw enforceFinalTag Patch for DeepSeek")
    print("=" * 50)

    if "--check" in sys.argv:
        sys.exit(check_status())
    elif "--revert" in sys.argv:
        sys.exit(revert_patch())
    else:
        sys.exit(apply_patch())
