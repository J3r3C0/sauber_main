# Sheratan Core - End-to-End Test Script

## 🎯 Test Goal

Test the complete Self-Loop system flow:
1. Start Sheratan Core v2
2. Create a Self-Loop mission via API
3. Verify job creation and dispatch
4. Check loop state and iteration tracking

---

## 🚀 Prerequisites

```bash
cd c:\Projects\2_sheratan_core\core\sheratan_core_v2
.\venv\Scripts\Activate.ps1
python -m sheratan_core_v2.main
```

Server should start on: **http://localhost:8001**

---

## 📝 Test Steps

### 1. **Health Check**

```bash
curl http://localhost:8001/api/status
```

**Expected Response:**
```json
{
  "status": "ok",
  "missions": 0
}
```

---

### 2. **Create Self-Loop Mission**

```bash
curl -X POST "http://localhost:8001/api/selfloop/create" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Self-Loop Mission",
    "goal": "Analyze the current system architecture and suggest improvements",
    "initial_context": "Sheratan Core v2 with Offgrid Memory integration",
    "max_iterations": 5
  }'
```

**Expected Response:**
```json
{
  "ok": true,
  "mission": {
    "id": "mission_<uuid>",
    "title": "Test Self-Loop Mission",
    "description": "Self-Loop: Analyze the current system architecture...",
    "metadata": {
      "type": "selfloop",
      "max_iterations": 5
    }
  },
  "task": {
    "id": "task_<uuid>",
    "name": "selfloop_iteration",
    "kind": "selfloop"
  },
  "job": {
    "id": "job_<uuid>",
    "status": "pending",
    "payload": {
      "job_type": "sheratan_selfloop",
      "loop_state": {
        "iteration": 1,
        "goal": "Analyze the current system architecture...",
        "max_iterations": 5
      }
    }
  }
}
```

---

### 3. **Check Mission Status**

```bash
curl http://localhost:8001/api/selfloop/<mission_id>/status
```

**Expected Response:**
```json
{
  "ok": true,
  "mission": { ... },
  "tasks": [ ... ],
  "jobs": [ ... ],
  "loop_state": {
    "iteration": 1,
    "goal": "...",
    "max_iterations": 5,
    "history": []
  },
  "iteration": 1,
  "total_jobs": 1
}
```

---

### 4. **List All Missions**

```bash
curl http://localhost:8001/api/missions
```

**Expected Response:**
```json
[
  {
    "id": "mission_<uuid>",
    "title": "Test Self-Loop Mission",
    "description": "Self-Loop: ...",
    "metadata": {
      "type": "selfloop",
      "max_iterations": 5
    }
  }
]
```

---

## ✅ Success Criteria

- [x] Core starts without errors
- [x] Health check returns OK
- [x] Self-Loop mission created successfully
- [x] Job payload contains `job_type: "sheratan_selfloop"`
- [x] Loop state initialized with iteration=1
- [x] Mission status endpoint returns loop state
- [x] Job is dispatched to WebRelay queue

---

## 🔍 What to Verify

### Job Payload Structure
```json
{
  "job_type": "sheratan_selfloop",
  "response_format": "selfloop_markdown",
  "loop_state": {
    "iteration": 1,
    "goal": "...",
    "initial_context": "...",
    "max_iterations": 5,
    "history": [],
    "open_questions": []
  },
  "prompt": "# SHERATAN SELF-LOOP SYSTEM\n\n..."
}
```

### WebRelay Queue
Check that job file is created:
```
c:\Projects\2_sheratan_core\core\sheratan_core_v2\webrelay_out\job_<uuid>.job.json
```

---

## 🐛 Troubleshooting

### Core Won't Start
- Check if port 8001 is already in use
- Verify venv is activated
- Check for import errors

### Mission Creation Fails
- Verify all required fields are provided
- Check Core logs for errors
- Ensure Offgrid path is correct

### Job Not Dispatched
- Check `webrelay_out/` directory exists
- Verify WebRelay bridge is initialized
- Check bridge logs

---

## 📊 Expected File Structure

After successful test:
```
core/sheratan_core_v2/
├── v2.db                    # SQLite database with mission/task/job
├── webrelay_out/
│   └── job_<uuid>.job.json  # Dispatched job
└── data/
    └── events/              # Offgrid events (if enabled)
```

---

## 🎯 Next Steps

If test passes:
1. ✅ Self-Loop API is functional
2. ✅ Job creation works
3. ✅ Loop state tracking works
4. ⚠️ Need Worker to process Self-Loop format

If test fails:
1. Check Core logs
2. Verify imports
3. Check database schema
4. Verify WebRelay bridge init

---

## 💡 Alternative: Python Test Script

```python
import requests

BASE_URL = "http://localhost:8001"

# 1. Health check
response = requests.get(f"{BASE_URL}/api/status")
print("Health:", response.json())

# 2. Create mission
response = requests.post(
    f"{BASE_URL}/api/selfloop/create",
    json={
        "title": "Test Mission",
        "goal": "Test the Self-Loop system",
        "max_iterations": 3
    }
)
result = response.json()
print("Created:", result)

mission_id = result["mission"]["id"]

# 3. Check status
response = requests.get(f"{BASE_URL}/api/selfloop/{mission_id}/status")
print("Status:", response.json())
```

---

## 🎉 Success!

If all tests pass, the Self-Loop system is **100% functional** on the backend!

**Remaining:** Worker needs to understand Self-Loop Markdown format (A/B/C/D sections).
