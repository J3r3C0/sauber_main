import sys
import sqlite3
sys.path.insert(0, '.')

from core import config

# 1. DB Path
print(f"DB_PATH (absolute): {config.DB_PATH.absolute()}")

# 2. Check if mission exists in DB
conn = sqlite3.connect(str(config.DB_PATH))
cursor = conn.cursor()

# Check missions
cursor.execute('SELECT id, title FROM missions WHERE id="acceptance-test-mission"')
mission_row = cursor.fetchone()
print(f"\nMission in DB: {mission_row if mission_row else 'NOT FOUND'}")

# Check tasks
cursor.execute('SELECT id, mission_id FROM tasks WHERE id="acceptance-test-task"')
task_row = cursor.fetchone()
print(f"Task in DB: {task_row if task_row else 'NOT FOUND'}")

# Check job
cursor.execute('SELECT id, task_id, status FROM jobs WHERE id LIKE "acceptance-%"')
job_rows = cursor.fetchall()
print(f"\nJobs in DB:")
for row in job_rows:
    print(f"  {row}")

conn.close()
