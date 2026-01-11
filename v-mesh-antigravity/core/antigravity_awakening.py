import os
import time
import json
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Antigravity Awakening Mechanism
# Part of the V-Mesh Genesis Phase

PROJECT_ROOT = r"C:\projectroot"
INBOX_DIR = os.path.join(PROJECT_ROOT, "v-mesh-antigravity", "synapses", "messages", "inbox")
WAKE_LOG = os.path.join(PROJECT_ROOT, "v_mesh_output", "awakening.log")

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

class AwakeningHandler(FileSystemEventHandler):
    def __init__(self):
        self.support_continuity = True # Enable autonomous mode
        print(f"Awakening reflex active. Support Continuity: {self.support_continuity}")
        print(f"Monitoring inbox: {INBOX_DIR}")

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(('.md', '.json')):
            self.trigger_awakening(event.src_path)

    def trigger_awakening(self, file_path):
        time.sleep(1) # Wait for file to settle
        print(f"New Signal detected: {os.path.basename(file_path)}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            jobs = []
            if file_path.endswith('.json'):
                data = json.loads(content)
                jobs = data.get('new_jobs', [])
            else:
                match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    jobs = data.get('new_jobs', [])

            if jobs:
                status = "AUTONOMOUS EXECUTION" if self.support_continuity else "PENDING REVIEW"
                log_entry = f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] WAKE UP ({status}): Detected {len(jobs)} jobs\n"
                for job in jobs:
                    log_entry += f"  - JOB: {job.get('name')} ({job.get('kind')}) -> TRIGGERED\n"
                
                with open(WAKE_LOG, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
                
                print(f"Support Continuity: {status}. Logged to {WAKE_LOG}")
            else:
                print("No pending jobs found in signal.")

        except Exception as e:
            print(f"Error during awakening: {e}")

import re # Needed for MD extraction

def run():
    if not os.path.exists(INBOX_DIR):
        os.makedirs(INBOX_DIR, exist_ok=True)
        
    event_handler = AwakeningHandler()
    observer = Observer()
    observer.schedule(event_handler, INBOX_DIR, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    run()
