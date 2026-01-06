---
active: true
iteration: 2
max_iterations: 100
completion_promise: "CLOUDSHIFT_COMPLETE"
started_at: "2026-01-06T14:55:30Z"
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
