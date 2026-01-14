TASK: Stabilize the complete system (sauber_main) with evidence.

Ground Truth:
- Start script: START_COMPLETE_SYSTEM.bat
- Core port: 8001
- Health endpoint: GET /api/system/health
- E2E job: POST /api/jobs (via chain specs)

## Completed ✅

### Gate 1: Boot & Health
- [x] System boots successfully
- [x] Health endpoint returns 200 OK
- [x] All services active (Core, WebRelay, Broker, Hosts, Dashboard)

### Gate 2: Dispatcher Active
- [x] Dispatcher thread launches
- [x] Dispatcher loop runs (`is_running=True`)
- [x] Jobs move from pending → working
- [x] Error logging implemented

### Fixes Applied
- [x] Added dispatcher error logging (start, loop, crash detection)
- [x] Fixed orphaned jobs (cleared invalid `depends_on: ['parent']`)
- [x] Created diagnostic scripts (check_dispatcher, check_dependencies, fix_orphaned_jobs)

## Remaining Issues ⚠️

### Orphaned Jobs
- **Problem:** Chain specs create jobs with `depends_on: ['parent']` but parent doesn't exist
- **Workaround:** Run `fix_orphaned_jobs.py` to clear invalid dependencies
- **Long-term:** Fix chain spec creation logic

### Job Completion
- **Status:** Jobs dispatch to workers but completion not fully verified
- **Next:** Monitor worker logs for job results

## Next Steps

1. [ ] Fix chain spec logic (prevent orphaned jobs)
2. [ ] Verify full E2E job completion (worker → result)
3. [ ] Gate 3: Failure/Recovery testing
4. [ ] Add dispatcher health to `/api/system/health`
5. [ ] Implement automatic orphaned job cleanup
.
