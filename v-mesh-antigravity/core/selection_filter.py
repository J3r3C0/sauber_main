import json
import time
import os
import re
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# V-Mesh Selection Filter (Router Brain)
# Part of the V-Mesh Genesis Phase

PROJECT_ROOT = r"C:\projectroot"
LIVE_STREAM_PATH = os.path.join(PROJECT_ROOT, "v_mesh_output", "live_stream.txt")
WATCH_DIR = os.path.join(PROJECT_ROOT, "v_mesh_output")

class SelectionFilter(FileSystemEventHandler):
    def __init__(self):
        self.last_target = "Host_A"
        print(f"Selection Filter active. Watching: {WATCH_DIR}")

    def get_latest_resonance(self):
        """Gets the latest resonance target from the live stream pulses."""
        if not os.path.exists(LIVE_STREAM_PATH):
            return self.last_target
            
        try:
            with open(LIVE_STREAM_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
                # Find the last pulse block
                pulses = re.findall(r"--- \[V-MESH PULSE.*?\] ---\n(.*?)\n(?=---|$)", content, re.DOTALL)
                if pulses:
                    last_pulse_json = pulses[-1]
                    data = json.loads(last_pulse_json)
                    return data.get('resonance_target', self.last_target)
        except Exception as e:
            print(f"Error reading resonance: {e}")
        return self.last_target

    def on_created(self, event):
        self.handle_event(event)
        
    def on_modified(self, event):
        self.handle_event(event)

    def handle_event(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.json') and "status_restored" not in event.src_path:
            # Avoid processing the status confirmed file or its results
            self.process_job(event.src_path)

    def process_job(self, file_path):
        # Give the file a moment to be fully written
        time.sleep(1.0)
        
        try:
            if not os.path.exists(file_path):
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                job = json.load(f)
            
            # If the job is already routed, skip
            if 'v_metadata' in job and 'routed_to' in job['v_metadata']:
                return

            target = self.get_latest_resonance()
            print(f"Routing Job {os.path.basename(file_path)} -> {target}")

            if 'v_metadata' not in job:
                job['v_metadata'] = {}
            
            job['v_metadata']['routed_to'] = target
            job['v_metadata']['routing_timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(job, f, indent=2)
            
            print(f"Job {os.path.basename(file_path)} successfully tagged for {target}")

        except Exception as e:
            # Use ASCII only for error messages to be safe
            print(f"Error processing job: {str(e)}")

def run():
    event_handler = SelectionFilter()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    run()
