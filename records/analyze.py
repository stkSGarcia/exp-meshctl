#!/usr/bin/env python3
"""
Analyze Claude Code session recordings.
Produces per-query statistics sorted by checkpoint order.
"""

import json
import re
import os
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent


# ── helpers ──────────────────────────────────────────────────────────────────

def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def parse_ts(ts):
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def fmt_duration(seconds):
    if seconds is None:
        return "N/A"
    m, s = divmod(int(seconds), 60)
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def fmt_latency(ms):
    if ms is None:
        return "N/A"
    if ms >= 1000:
        return f"{ms/1000:.1f}s"
    return f"{ms:.0f}ms"


# ── core parsing ─────────────────────────────────────────────────────────────

def get_unique_llm_calls(records):
    """
    Return deduplicated LLM calls. Each real API call produces a chain of
    assistant records (streaming artifacts); keep only the first in each chain
    (the one whose parent is NOT another assistant record).
    """
    by_uuid = {r["uuid"]: r for r in records if r.get("uuid")}
    calls = []
    for r in records:
        if r.get("type") != "assistant":
            continue
        parent = by_uuid.get(r.get("parentUuid"))
        if parent and parent.get("type") == "assistant":
            continue  # streaming duplicate
        calls.append(r)
    return calls


def collect_tool_names(records):
    """Count tool_use names from assistant content."""
    counts = defaultdict(int)
    for r in records:
        if r.get("type") != "assistant":
            continue
        for item in r.get("message", {}).get("content", []):
            if isinstance(item, dict) and item.get("type") == "tool_use":
                counts[item.get("name", "unknown")] += 1
    return counts


def count_tool_results(records):
    """Count tool_result items inside user messages."""
    total = 0
    for r in records:
        if r.get("type") != "user":
            continue
        content = r.get("message", {}).get("content", "")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    total += 1
    return total


def build_read_params_map(records):
    """Map tool_use_id → (offset, limit) for partial Read calls only."""
    params = {}
    for r in records:
        if r.get("type") != "assistant":
            continue
        for block in r.get("message", {}).get("content", []):
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") != "Read":
                continue
            inp = block.get("input", {})
            offset = inp.get("offset")
            limit = inp.get("limit")
            if offset is not None or limit is not None:
                params[block["id"]] = (offset, limit)
    return params


def extract_tool_result_fields(r):
    """Return (text, file_path, tool_use_id) from a user record with tool_result."""
    content = r.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return "", None, None
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        inner = block.get("content", "")
        text = inner if isinstance(inner, str) else json.dumps(inner)
        tool_use_id = block.get("tool_use_id")
        tool_result = r.get("toolUseResult", {})
        file_path = None
        if isinstance(tool_result, dict) and tool_result.get("file"):
            file_path = tool_result["file"].get("filePath", "")
        return text, file_path, tool_use_id
    return "", None, None


PROJECT_ROOTS = [
    "/home/stk/projects/exp-meshctl/",
    "/Users/samuel/Projects/exp-meshctl/",
]

def shorten_path(path):
    for root in PROJECT_ROOTS:
        if path.startswith(root):
            return path[len(root):]
    return path


def compute_text_content(window_records, read_params):
    """
    Compute actively-loaded external text content for user records in a time window.
    Returns dict with char counts and file list.
    """
    skill_instruction = 0
    file_read = 0
    bash_output = 0
    other_tool_result = 0
    files = []  # (short_path, chars, offset, limit)

    for r in window_records:
        if r.get("type") != "user":
            continue

        is_meta = r.get("isMeta", False)
        tool_result = r.get("toolUseResult", {})
        content = r.get("message", {}).get("content", "")

        if is_meta:
            text = " ".join(c.get("text", "") for c in content if isinstance(c, dict)) \
                if isinstance(content, list) else (content or "")
            skill_instruction += len(text)

        elif isinstance(tool_result, dict) and tool_result.get("file"):
            text, file_path, tool_use_id = extract_tool_result_fields(r)
            file_read += len(text)
            if file_path:
                offset, limit = read_params.get(tool_use_id, (None, None))
                files.append((shorten_path(file_path), len(text), offset, limit))

        elif isinstance(tool_result, dict) and "stdout" in tool_result:
            stdout = tool_result.get("stdout", "") or ""
            stderr = tool_result.get("stderr", "") or ""
            bash_output += len(stdout) + len(stderr)

        else:
            if isinstance(tool_result, str):
                other_tool_result += len(tool_result)
            else:
                text, _, _ = extract_tool_result_fields(r)
                if text:
                    other_tool_result += len(text)

    total = skill_instruction + file_read + bash_output + other_tool_result
    return {
        "text_skill_instr": skill_instruction,
        "text_file_read": file_read,
        "text_bash": bash_output,
        "text_other": other_tool_result,
        "text_total": total,
        "text_files": files,
    }


def compute_metrics(calls, all_records, window_start, window_end):
    """
    Given a list of deduplicated LLM call records and all records in the window,
    compute aggregated statistics.
    """
    by_uuid = {r["uuid"]: r for r in all_records if r.get("uuid")}

    # filter calls to this window
    window_calls = []
    for c in calls:
        ts = parse_ts(c.get("timestamp"))
        if ts and window_start <= ts < window_end:
            window_calls.append(c)

    # filter all_records to window
    window_records = []
    for r in all_records:
        ts = parse_ts(r.get("timestamp"))
        if ts and window_start <= ts < window_end:
            window_records.append(r)

    # tokens
    input_tokens = 0
    cache_create_1h = 0
    cache_create_5m = 0
    cache_read = 0
    output_tokens = 0

    # call metadata
    stop_tool_use = 0
    stop_end_turn = 0
    thinking_calls = 0
    skill_calls = defaultdict(int)
    skill_output = defaultdict(int)

    # latency
    latencies_ms = []

    for c in window_calls:
        usage = c.get("message", {}).get("usage", {})
        input_tokens += usage.get("input_tokens", 0)
        cc = usage.get("cache_creation", {})
        cache_create_1h += cc.get("ephemeral_1h_input_tokens", 0)
        cache_create_5m += cc.get("ephemeral_5m_input_tokens", 0)
        cache_read += usage.get("cache_read_input_tokens", 0)
        out = usage.get("output_tokens", 0)
        output_tokens += out

        stop_reason = c.get("message", {}).get("stop_reason", "")
        if stop_reason == "tool_use":
            stop_tool_use += 1
        elif stop_reason == "end_turn":
            stop_end_turn += 1

        content = c.get("message", {}).get("content", [])
        if any(isinstance(x, dict) and x.get("type") == "thinking" for x in content):
            thinking_calls += 1

        skill = c.get("attributionSkill", "none")
        skill_calls[skill] += 1
        skill_output[skill] += out

        # latency: time from parent to this call
        parent = by_uuid.get(c.get("parentUuid"))
        if parent and parent.get("timestamp") and c.get("timestamp"):
            t_parent = parse_ts(parent.get("timestamp"))
            t_self = parse_ts(c.get("timestamp"))
            if t_parent and t_self:
                latencies_ms.append((t_self - t_parent).total_seconds() * 1000)

    total_tokens = input_tokens + cache_create_1h + cache_create_5m + cache_read + output_tokens
    avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else None

    # tool calls from all records in window
    tool_names = collect_tool_names(window_records)
    tool_results = count_tool_results(window_records)

    return {
        "llm_calls": len(window_calls),
        "input_tokens": input_tokens,
        "cache_create_1h": cache_create_1h,
        "cache_create_5m": cache_create_5m,
        "cache_read": cache_read,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "stop_tool_use": stop_tool_use,
        "stop_end_turn": stop_end_turn,
        "thinking_calls": thinking_calls,
        "skill_calls": dict(skill_calls),
        "skill_output": dict(skill_output),
        "avg_latency_ms": avg_latency,
        "tool_names": dict(tool_names),
        "tool_results": tool_results,
    }


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    # 1. load all session files
    session_files = sorted(BASE.glob("*.jsonl"))
    subagent_files = sorted(BASE.rglob("subagents/agent-*.jsonl"))

    # 2. load subagent records keyed by parent session id
    subagent_by_session = defaultdict(list)
    for sf in subagent_files:
        session_id = sf.parts[-3]  # grandparent dir = session id
        records = load_jsonl(sf)
        subagent_by_session[session_id].extend(records)

    rows = []

    for session_file in session_files:
        records = load_jsonl(session_file)
        session_id = session_file.stem

        # build uuid index
        by_uuid = {r["uuid"]: r for r in records if r.get("uuid")}

        # find queries
        queries = []
        for r in records:
            if r.get("type") != "user":
                continue
            content = r.get("message", {}).get("content", "")
            if not isinstance(content, str):
                continue
            if "<command-name>" not in content:
                continue
            cmd_m = re.search(r"<command-name>(.*?)</command-name>", content)
            args_m = re.search(r"<command-args>(.*?)</command-args>", content)
            queries.append({
                "uuid": r.get("uuid"),
                "timestamp": r.get("timestamp"),
                "command": cmd_m.group(1).strip() if cmd_m else "",
                "args": args_m.group(1).strip() if args_m else "",
            })

        if not queries:
            continue

        # determine checkpoint number from propose args
        checkpoint_num = None
        for q in queries:
            m = re.search(r"checkpoint_(\d+)", q["args"])
            if m:
                checkpoint_num = int(m.group(1))
                break
        if checkpoint_num is None:
            checkpoint_num = 99  # fallback

        # deduplicated calls for main session
        main_calls = get_unique_llm_calls(records)

        # deduplicated calls for subagents of this session
        sub_records = subagent_by_session.get(session_id, [])
        sub_calls = get_unique_llm_calls(sub_records) if sub_records else []

        # all records combined for tool counting
        all_records = records + sub_records
        all_calls = main_calls + sub_calls

        # read params map for partial-read annotation
        read_params = build_read_params_map(all_records)

        # timestamps for window bounds
        INF = datetime(9999, 1, 1, tzinfo=timezone.utc)

        for i, q in enumerate(queries):
            q_start = parse_ts(q["timestamp"])
            q_end = parse_ts(queries[i + 1]["timestamp"]) if i + 1 < len(queries) else INF

            metrics = compute_metrics(all_calls, all_records, q_start, q_end)

            # text content for this window
            window_records = [
                r for r in all_records
                if (ts := parse_ts(r.get("timestamp"))) and q_start <= ts < q_end
            ]
            text = compute_text_content(window_records, read_params)

            # wall-clock: last assistant record in window
            last_ts = None
            for r in all_records:
                if r.get("type") == "assistant":
                    ts = parse_ts(r.get("timestamp"))
                    if ts and q_start <= ts < q_end:
                        if last_ts is None or ts > last_ts:
                            last_ts = ts

            duration_s = (last_ts - q_start).total_seconds() if last_ts else None

            rows.append({
                "checkpoint": checkpoint_num,
                "order": i,
                "command": q["command"],
                "start": q["timestamp"],
                "duration_s": duration_s,
                **metrics,
                **text,
            })

    # sort by checkpoint then command order
    rows.sort(key=lambda r: (r["checkpoint"], r["order"]))

    # ── output ────────────────────────────────────────────────────────────────

    lines = []
    p = lines.append

    def md_row(*cells):
        return "| " + " | ".join(str(c) for c in cells) + " |"

    def md_sep(*alignments):
        # l=left, r=right, c=center
        parts = []
        for a in alignments:
            if a == "r":
                parts.append("---:")
            elif a == "c":
                parts.append(":---:")
            else:
                parts.append("---")
        return "| " + " | ".join(parts) + " |"

    # ── Table 1: tokens + timing + text content
    p("## Table 1: Tokens & Timing")
    p("")
    p("**Columns:** CP = checkpoint number · Duration = wall-clock time from command start to last assistant response · "
      "LLM Calls = deduplicated API calls (streaming chunks merged) · "
      "Input = fresh (non-cached) input tokens · CC-1h / CC-5m = tokens written to 1-hour / 5-minute cache · "
      "Cache Read = tokens served from cache · Output = generated tokens · Total = all of the above summed · "
      "Skill instr = chars of skill instruction text injected at invocation · "
      "File reads = chars of file content loaded via Read tool · "
      "Bash out = chars of bash stdout/stderr · "
      "Other = chars of other tool results (e.g. openspec CLI output) · "
      "Text total = sum of the four text columns (actively loaded external content only)")
    p("")
    p(md_row("CP", "Command", "Start (UTC)", "Duration", "LLM Calls",
             "Input", "CC-1h", "CC-5m", "Cache Read", "Output", "Total",
             "Skill instr", "File reads", "Bash out", "Other", "Text total"))
    p(md_sep("r", "l", "l", "r", "r", "r", "r", "r", "r", "r", "r",
             "r", "r", "r", "r", "r"))

    session_totals = defaultdict(lambda: defaultdict(int))
    for r in rows:
        cp = r["checkpoint"]
        p(md_row(
            cp, r["command"], r["start"][:19].replace("T", " "),
            fmt_duration(r["duration_s"]), r["llm_calls"],
            r["input_tokens"], r["cache_create_1h"], r["cache_create_5m"],
            r["cache_read"], r["output_tokens"], r["total_tokens"],
            r["text_skill_instr"], r["text_file_read"], r["text_bash"],
            r["text_other"], r["text_total"],
        ))
        for k in ("llm_calls", "input_tokens", "cache_create_1h", "cache_create_5m",
                  "cache_read", "output_tokens", "total_tokens",
                  "text_skill_instr", "text_file_read", "text_bash",
                  "text_other", "text_total"):
            session_totals[cp][k] += r[k]

    p("")
    p("**Per-checkpoint totals:**")
    p("")
    p(md_row("CP", "LLM Calls", "Input", "CC-1h", "CC-5m", "Cache Read", "Output", "Total",
             "Skill instr", "File reads", "Bash out", "Other", "Text total"))
    p(md_sep("r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r", "r"))
    for cp in sorted(session_totals.keys()):
        t = session_totals[cp]
        p(md_row(
            f"**{cp}**", t["llm_calls"], t["input_tokens"],
            t["cache_create_1h"], t["cache_create_5m"],
            t["cache_read"], t["output_tokens"], t["total_tokens"],
            t["text_skill_instr"], t["text_file_read"], t["text_bash"],
            t["text_other"], t["text_total"],
        ))

    # ── Table 2: LLM call breakdown + latency
    p("")
    p("## Table 2: LLM Call Breakdown & Latency")
    p("")
    p("**Columns:** Tool-use stops = calls that ended because the model invoked a tool · "
      "End-turn stops = calls that ended naturally (model finished responding) · "
      "Thinking calls = calls where extended thinking was active · "
      "Avg Latency = average time between a user turn and the next assistant response")
    p("")
    p(md_row("CP", "Command", "LLM Calls", "Tool-use stops", "End-turn stops", "Thinking calls", "Avg Latency"))
    p(md_sep("r", "l", "r", "r", "r", "r", "r"))
    for r in rows:
        p(md_row(
            r["checkpoint"], r["command"], r["llm_calls"],
            r["stop_tool_use"], r["stop_end_turn"],
            r["thinking_calls"], fmt_latency(r["avg_latency_ms"]),
        ))

    # ── Table 3: Skill attribution
    p("")
    p("## Table 3: Skill Attribution")
    p("")
    p("**Columns:** `<skill> calls` = number of LLM calls attributed to that skill within this command's time window · "
      "`<skill> output` = total output tokens produced by that skill · "
      "A command typically shows calls only for its own skill; non-zero values in other skills indicate subagent or overlap.")
    p("")
    all_skills = sorted({s for r in rows for s in r["skill_calls"].keys()})
    skill_hdrs = [f"{s} calls" for s in all_skills] + [f"{s} output" for s in all_skills]
    p(md_row("CP", "Command", *skill_hdrs))
    p(md_sep("r", "l", *["r"] * len(skill_hdrs)))
    for r in rows:
        skill_vals = [r["skill_calls"].get(s, 0) for s in all_skills]
        skill_outs = [r["skill_output"].get(s, 0) for s in all_skills]
        p(md_row(r["checkpoint"], r["command"], *skill_vals, *skill_outs))

    # ── Table 4: Tool execution breakdown
    p("")
    p("## Table 4: Tool Executions")
    p("")
    p("**Columns:** Tool Results = total number of tool result messages returned to the model · "
      "Bash / Edit / Write / Read / TodoWrite / Agent = number of times each tool was invoked · "
      "Other = invocations of any tool not in the fixed list above (e.g. AskUserQuestion, WebFetch)")
    p("")
    tool_order = ["Bash", "Edit", "Write", "Read", "TodoWrite", "Agent"]
    p(md_row("CP", "Command", "Tool Results", *tool_order, "Other"))
    p(md_sep("r", "l", *["r"] * (len(tool_order) + 2)))
    for r in rows:
        tn = r["tool_names"]
        other = sum(v for k, v in tn.items() if k not in tool_order)
        p(md_row(
            r["checkpoint"], r["command"], r["tool_results"],
            *[tn.get(t, 0) for t in tool_order],
            other,
        ))

    # ── Table 5: Files read per query
    p("")
    p("## Table 5: Files Read")
    p("")
    p("**Columns:** File = path relative to project root · "
      "Chars = total characters loaded from this file across all reads within the command · "
      "Notes = present only for partial reads, showing the offset and limit passed to the Read tool")
    p("")
    p(md_row("CP", "Command", "File", "Chars", "Notes"))
    p(md_sep("r", "l", "l", "r", "l"))
    for r in rows:
        files = r.get("text_files", [])
        # Aggregate by path within this row
        seen = {}
        for path, chars, offset, limit in files:
            if path not in seen:
                seen[path] = {"chars": 0, "reads": []}
            seen[path]["chars"] += chars
            if offset is not None or limit is not None:
                seen[path]["reads"].append((offset, limit))
        if not seen:
            p(md_row(r["checkpoint"], r["command"], "—", "", ""))
        else:
            for path, info in sorted(seen.items()):
                reads = info["reads"]
                note = ("partial: " + ", ".join(f"offset={o} limit={l}" for o, l in reads)) \
                    if reads else ""
                p(md_row(r["checkpoint"], r["command"], f"`{path}`", info["chars"], note))

    p("")
    p(f"*{len(rows)} queries across {len(session_totals)} checkpoints*")

    md = "\n".join(lines) + "\n"
    out_path = BASE / "results.md"
    with open(out_path, "w") as f:
        f.write(md)
    print(f"Written to {out_path} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
