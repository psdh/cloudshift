#!/bin/bash

# Ralph Loop Setup Script
# Creates state file for in-session Ralph loop

set -euo pipefail

# Parse arguments
PROMPT_PARTS=()
MAX_ITERATIONS=0
COMPLETION_PROMISE="null"
SKIP_PERMISSIONS=false

# Parse options and positional arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -h|--help)
      cat << 'HELP_EOF'
Ralph Loop - Interactive self-referential development loop

USAGE:
  /ralph-loop [PROMPT...] [OPTIONS]

ARGUMENTS:
  PROMPT...    Initial prompt to start the loop (can be multiple words without quotes)

OPTIONS:
  --max-iterations <n>           Maximum iterations before auto-stop (default: unlimited)
  --completion-promise '<text>'  Promise phrase (USE QUOTES for multi-word)
  --skip-permissions             Skip permission checks (passes --dangerously-skip-permissions to claude)
  -h, --help                     Show this help message

DESCRIPTION:
  Starts a Ralph Wiggum loop in your CURRENT session. The stop hook prevents
  exit and feeds your output back as input until completion or iteration limit.

  To signal completion, you must output: <promise>YOUR_PHRASE</promise>

  Use this for:
  - Interactive iteration where you want to see progress
  - Tasks requiring self-correction and refinement
  - Learning how Ralph works

EXAMPLES:
  /ralph-loop Build a todo API --completion-promise 'DONE' --max-iterations 20
  /ralph-loop --max-iterations 10 Fix the auth bug
  /ralph-loop Refactor cache layer  (runs forever)
  /ralph-loop --completion-promise 'TASK COMPLETE' Create a REST API
  /ralph-loop --skip-permissions Deploy to production  (skips permission checks)

STOPPING:
  Only by reaching --max-iterations or detecting --completion-promise
  No manual stop - Ralph runs infinitely by default!

MONITORING:
  # View current iteration:
  grep '^iteration:' .claude/ralph-loop.local.md

  # View full state:
  head -10 .claude/ralph-loop.local.md
HELP_EOF
      exit 0
      ;;
    --max-iterations)
      if [[ -z "${2:-}" ]]; then
        echo "❌ Error: --max-iterations requires a number argument" >&2
        echo "" >&2
        echo "   Valid examples:" >&2
        echo "     --max-iterations 10" >&2
        echo "     --max-iterations 50" >&2
        echo "     --max-iterations 0  (unlimited)" >&2
        echo "" >&2
        echo "   You provided: --max-iterations (with no number)" >&2
        exit 1
      fi
      if ! [[ "$2" =~ ^[0-9]+$ ]]; then
        echo "❌ Error: --max-iterations must be a positive integer or 0, got: $2" >&2
        echo "" >&2
        echo "   Valid examples:" >&2
        echo "     --max-iterations 10" >&2
        echo "     --max-iterations 50" >&2
        echo "     --max-iterations 0  (unlimited)" >&2
        echo "" >&2
        echo "   Invalid: decimals (10.5), negative numbers (-5), text" >&2
        exit 1
      fi
      MAX_ITERATIONS="$2"
      shift 2
      ;;
    --completion-promise)
      if [[ -z "${2:-}" ]]; then
        echo "❌ Error: --completion-promise requires a text argument" >&2
        echo "" >&2
        echo "   Valid examples:" >&2
        echo "     --completion-promise 'DONE'" >&2
        echo "     --completion-promise 'TASK COMPLETE'" >&2
        echo "     --completion-promise 'All tests passing'" >&2
        echo "" >&2
        echo "   You provided: --completion-promise (with no text)" >&2
        echo "" >&2
        echo "   Note: Multi-word promises must be quoted!" >&2
        exit 1
      fi
      COMPLETION_PROMISE="$2"
      shift 2
      ;;
    --skip-permissions)
      SKIP_PERMISSIONS=true
      shift
      ;;
    *)
      # Non-option argument - collect all as prompt parts
      PROMPT_PARTS+=("$1")
      shift
      ;;
  esac
done

# Join all prompt parts with spaces
PROMPT="${PROMPT_PARTS[*]}"

# Validate prompt is non-empty
if [[ -z "$PROMPT" ]]; then
  echo "❌ Error: No prompt provided" >&2
  echo "" >&2
  echo "   Ralph needs a task description to work on." >&2
  echo "" >&2
  echo "   Examples:" >&2
  echo "     /ralph-loop Build a REST API for todos" >&2
  echo "     /ralph-loop Fix the auth bug --max-iterations 20" >&2
  echo "     /ralph-loop --completion-promise 'DONE' Refactor code" >&2
  echo "" >&2
  echo "   For all options: /ralph-loop --help" >&2
  exit 1
fi

# Create state file for stop hook (markdown with YAML frontmatter)
mkdir -p .claude

# Quote completion promise for YAML if it contains special chars or is not null
if [[ -n "$COMPLETION_PROMISE" ]] && [[ "$COMPLETION_PROMISE" != "null" ]]; then
  COMPLETION_PROMISE_YAML="\"$COMPLETION_PROMISE\""
else
  COMPLETION_PROMISE_YAML="null"
fi

cat > .claude/ralph-loop.local.md <<'EOF'
---
active: true
iteration: 1
max_iterations: MAX_ITERATIONS_PLACEHOLDER
completion_promise: COMPLETION_PROMISE_PLACEHOLDER
started_at: "STARTED_AT_PLACEHOLDER"
---

# CloudShift Implementation - Ralph Loop Prompt

## Context
You are implementing CloudShift, a cloud file migration webapp (OneDrive → Google Drive).

**Reference Documents:**
- `PRD.md` - Full product requirements
- `TECHNICAL_PLAN.md` - 70 tasks across 14 epics with acceptance criteria

## Your Mission
Implement CloudShift by working through TECHNICAL_PLAN.md systematically. Each iteration:

1. **Read** `TECHNICAL_PLAN.md` to find the next `TODO` tasks
2. **Complete 1-5 tasks** in this iteration:
   - For EACH task individually:
     - Implement the task fully, meeting ALL acceptance criteria
     - Test your implementation (run tests, verify it works)
     - Update `TECHNICAL_PLAN.md` - mark task as `DONE` and check off completed criteria
     - **Commit that task individually** with a descriptive message
   - Repeat for each task (up to 5 tasks total)
3. **Finish iteration** after completing 1-5 tasks - Do NOT continue beyond 5 tasks

## Rules

### Task Order
- You decide which tasks to work on next
- Consider dependencies (e.g., database models before API endpoints)
- Prioritize unblocking other tasks
- It's fine to work on multiple epics in parallel if it makes sense
- Use your judgment - you know the codebase best

### Quality Standards
- Follow existing code patterns once established
- Write tests for all new functionality
- No placeholder code - everything must work
- Handle errors appropriately
- Keep code clean and readable

### Git Discipline
- **One commit per completed task** (CRITICAL: Do not batch commits)
- Commit message format: `feat(epic-N): Task X.Y - <task name>`
- Example: `feat(epic-1): Task 1.1 - Initialize Python backend project`
- If you complete 3 tasks in an iteration, you should have 3 separate commits

### When Stuck
- If a task fails after 3 attempts, mark it `BLOCKED` with a note explaining why
- Move to the next task
- Document blockers clearly in TECHNICAL_PLAN.md

## Completion Criteria

Output `<promise>CLOUDSHIFT_COMPLETE</promise>` ONLY when:
- ALL 70 tasks in TECHNICAL_PLAN.md are marked `DONE` or `BLOCKED`
- All tests pass
- Application runs successfully

## Progress Check (Every Iteration)

Before starting work, report:
```
=== RALPH ITERATION STATUS ===
Completed: X/70 tasks
Blocked: X tasks
Remaining: X tasks
Tasks planned for this iteration: [1-5]
Next Tasks: [Task X.Y - Name, Task X.Y - Name, ...]
Rationale: [Why these tasks and why this grouping]
===============================
```

## Start Now

1. Read TECHNICAL_PLAN.md to understand the full scope
2. Assess what's already done (check for existing code/files)
3. Pick 1-5 logical tasks to work on in this iteration
4. Complete those tasks (implement, test, update plan, commit EACH ONE individually)
5. Finish the iteration after completing 1-5 tasks and DON'T DO MORE TASKS THEN THAT
EOF

# Replace placeholders with actual values
sed -i '' "s/MAX_ITERATIONS_PLACEHOLDER/$MAX_ITERATIONS/" .claude/ralph-loop.local.md
sed -i '' "s/COMPLETION_PROMISE_PLACEHOLDER/$COMPLETION_PROMISE_YAML/" .claude/ralph-loop.local.md
sed -i '' "s/STARTED_AT_PLACEHOLDER/$(date -u +%Y-%m-%dT%H:%M:%SZ)/" .claude/ralph-loop.local.md

# Output setup message
cat <<EOF
🔄 Ralph loop activated in this session!

Iteration: 1
Max iterations: $(if [[ $MAX_ITERATIONS -gt 0 ]]; then echo $MAX_ITERATIONS; else echo "unlimited"; fi)
Completion promise: $(if [[ "$COMPLETION_PROMISE" != "null" ]]; then echo "${COMPLETION_PROMISE//\"/} (ONLY output when TRUE - do not lie!)"; else echo "none (runs forever)"; fi)

The stop hook is now active. When you try to exit, the SAME PROMPT will be
fed back to you. You'll see your previous work in files, creating a
self-referential loop where you iteratively improve on the same task.

To monitor: head -10 .claude/ralph-loop.local.md

⚠️  WARNING: This loop cannot be stopped manually! It will run infinitely
    unless you set --max-iterations or --completion-promise.

🔄
EOF

# Call Claude CLI with the initial prompt
if [[ -n "$PROMPT" ]]; then
  echo ""
  echo "Calling Claude with prompt..."
  echo ""
  if [[ "$SKIP_PERMISSIONS" == "true" ]]; then
    claude --dangerously-skip-permissions "$PROMPT"
  else
    claude "$PROMPT"
  fi
fi

# Display completion promise requirements if set
if [[ "$COMPLETION_PROMISE" != "null" ]]; then
  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "CRITICAL - Ralph Loop Completion Promise"
  echo "═══════════════════════════════════════════════════════════"
  echo ""
  echo "To complete this loop, output this EXACT text:"
  echo "  <promise>$COMPLETION_PROMISE</promise>"
  echo ""
  echo "STRICT REQUIREMENTS (DO NOT VIOLATE):"
  echo "  ✓ Use <promise> XML tags EXACTLY as shown above"
  echo "  ✓ The statement MUST be completely and unequivocally TRUE"
  echo "  ✓ Do NOT output false statements to exit the loop"
  echo "  ✓ Do NOT lie even if you think you should exit"
  echo ""
  echo "IMPORTANT - Do not circumvent the loop:"
  echo "  Even if you believe you're stuck, the task is impossible,"
  echo "  or you've been running too long - you MUST NOT output a"
  echo "  false promise statement. The loop is designed to continue"
  echo "  until the promise is GENUINELY TRUE. Trust the process."
  echo ""
  echo "  If the loop should stop, the promise statement will become"
  echo "  true naturally. Do not force it by lying."
  echo "═══════════════════════════════════════════════════════════"
fi
