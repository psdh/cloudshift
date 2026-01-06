---
active: true
iteration: 8
max_iterations: 100
completion_promise: "CLOUDSHIFT_COMPLETE"
started_at: "2026-01-06T13:41:26Z"
---

# CloudShift Implementation - Ralph Loop Prompt

## Context
You are implementing CloudShift, a cloud file migration webapp (OneDrive → Google Drive).

**Reference Documents:**
- `PRD.md` - Full product requirements
- `TECHNICAL_PLAN.md` - 70 tasks across 14 epics with acceptance criteria

## Your Mission
Implement CloudShift by working through TECHNICAL_PLAN.md systematically. Each iteration:

1. **Read** `TECHNICAL_PLAN.md` to find the next `TODO` task
2. **Implement** that task fully, meeting ALL acceptance criteria
3. **Test** your implementation (run tests, verify it works)
4. **Update** `TECHNICAL_PLAN.md` - mark task as `DONE` and check off completed criteria
5. **Commit** your changes with a descriptive message
6. **Continue** to the next task

## Rules

### Task Order
- You decide which task to work on next
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
- One commit per completed task
- Commit message format: `feat(epic-N): Task X.Y - <task name>`
- Example: `feat(epic-1): Task 1.1 - Initialize Python backend project`

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
Next Task: [Task X.Y - Name]
Rationale: [Why this task next]
===============================
```

## Start Now

1. Read TECHNICAL_PLAN.md to understand the full scope
2. Assess what's already done (check for existing code/files)
3. Pick the most logical next task to work on
4. Begin implementation
