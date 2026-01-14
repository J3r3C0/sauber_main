"""
E2E Test Suite: Spec→Job Pipeline Verification
Simplified version using proven smoke test pattern
"""
import sys
import time
from pathlib import Path
from datetime import datetime
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_db
from core import storage
from core.models import Task

class E2ETestSuite:
    def __init__(self):
        self.db_path = Path("ledger.json")
        
    def log(self, msg):
        print(f"[E2E] {msg}")
        
    def test_2_spec_to_jobs(self):
        """Test: Spec creates 2 jobs (critical gap test)"""
        self.log("=" * 60)
        self.log("TEST: Spec → Jobs Creation (CRITICAL GAP)")
        self.log("=" * 60)
        
        # Create unique IDs
        task_id = f"e2e_task_{uuid.uuid4().hex[:8]}"
        chain_id = f"e2e_chain_{uuid.uuid4().hex[:8]}"
        
        # Create task
        task = Task(
            id=task_id,
            mission_id="e2e_test",
            name="E2E Spec Test",
            description="Spec to jobs test",
            kind="test",
            params={},
            created_at=datetime.utcnow().isoformat() + "Z"
        )
        storage.create_task(task)
        self.log(f"✓ Created task: {task_id}")
        
        # Create chain context and specs
        with get_db() as conn:
            storage.ensure_chain_context(conn, chain_id, task_id)
            self.log(f"✓ Created chain context: {chain_id}")
            
            specs = [
                {
                    "spec_id": f"spec1_{uuid.uuid4().hex[:8]}",
                    "kind": "read_file",
                    "params": {"path": "core/main.py"}
                },
                {
                    "spec_id": f"spec2_{uuid.uuid4().hex[:8]}",
                    "kind": "read_file",
                    "params": {"path": "README.md"}
                }
            ]
            
            storage.append_chain_specs(conn, chain_id, task_id, "root", "", specs)
            storage.set_chain_needs_tick(conn, chain_id, True)
            self.log(f"✓ Registered 2 specs, needs_tick=True")
        
        # Verify specs in database
        with get_db() as conn:
            spec_count = conn.execute(
                "SELECT COUNT(*) FROM chain_specs WHERE chain_id=?", (chain_id,)
            ).fetchone()[0]
            self.log(f"✓ Verified: {spec_count} specs in database")
        
        self.log("⏳ Waiting 10s for ChainRunner to create jobs...")
        
        # Wait for ChainRunner
        deadline = time.time() + 10
        jobs_created = False
        
        while time.time() < deadline:
            with get_db() as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE task_id=?", (task_id,)
                ).fetchone()[0]
                
                if count >= 2:
                    self.log(f"✓ ChainRunner created {count} jobs!")
                    jobs_created = True
                    break
            time.sleep(0.5)
        
        if not jobs_created:
            with get_db() as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE task_id=?", (task_id,)
                ).fetchone()[0]
                self.log(f"❌ FAIL: ChainRunner created only {count}/2 jobs")
                
                # Debug
                needs_tick = conn.execute(
                    "SELECT needs_tick FROM chain_contexts WHERE chain_id=?", (chain_id,)
                ).fetchone()
                if needs_tick:
                    self.log(f"   Debug: needs_tick={needs_tick[0]}")
                
                pending = conn.execute(
                    "SELECT COUNT(*) FROM chain_specs WHERE chain_id=? AND status='pending'",
                    (chain_id,)
                ).fetchone()[0]
                self.log(f"   Debug: {pending} specs still pending")
            
            return False
        
        # Wait for completion
        self.log("⏳ Waiting 20s for jobs to complete...")
        deadline = time.time() + 20
        
        while time.time() < deadline:
            with get_db() as conn:
                completed = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE task_id=? AND status IN ('completed', 'done')",
                    (task_id,)
                ).fetchone()[0]
                
                if completed >= 2:
                    self.log(f"✅ PASS: {completed} jobs completed")
                    return True
            time.sleep(0.5)
        
        # Timeout
        with get_db() as conn:
            statuses = conn.execute(
                "SELECT status, COUNT(*) FROM jobs WHERE task_id=? GROUP BY status",
                (task_id,)
            ).fetchall()
            self.log(f"❌ FAIL: Jobs did not complete. Status:")
            for status, count in statuses:
                self.log(f"   {status}: {count}")
        
        return False
    
    def run_all(self):
        """Run test and report"""
        self.log("╔" + "=" * 58 + "╗")
        self.log("║" + " E2E Test: Spec→Job Pipeline ".center(58) + "║")
        self.log("╚" + "=" * 58 + "╝")
        self.log("")
        
        test_pass = self.test_2_spec_to_jobs()
        
        self.log("")
        self.log("=" * 60)
        self.log("RESULT")
        self.log("=" * 60)
        self.log(f"Spec→Jobs Test: {'✅ PASS' if test_pass else '❌ FAIL'}")
        self.log("=" * 60)
        
        if test_pass:
            self.log("✅ TEST PASSED")
            self.log("ChainRunner creates jobs from specs correctly!")
            return 0
        else:
            self.log("❌ TEST FAILED")
            self.log("Next: ChainRunner Investigation (T1)")
            return 1

if __name__ == "__main__":
    suite = E2ETestSuite()
    sys.exit(suite.run_all())

    def __init__(self):
        self.results = []
        self.db_path = Path("ledger.json")
        
    def log(self, msg):
        print(f"[E2E] {msg}")
        
    def test_1_single_job(self):
        """Test 1: Single job completes (baseline)"""
        self.log("=" * 60)
        self.log("TEST 1: Single Job Processing")
        self.log("=" * 60)
        
        # Create task
        task_id = f"e2e_task_{int(time.time())}"
        task = Task(
            id=task_id,
            mission_id="e2e_test",
            name="E2E Single Job",
            description="Baseline job test",
            kind="test",
            params={},
            created_at=datetime.utcnow().isoformat() + "Z"
        )
        storage.create_task(task)
        self.log(f"✓ Created task: {task_id}")
        
        # Create job using storage API
        job_id = f"e2e_job_{int(time.time())}"
        from core.models import Job
        
        job = Job(
            id=job_id,
            task_id=task_id,
            kind="read_file",
            params={"path": "core/main.py"},
            depends_on=[],
            status="pending",
            created_at=datetime.utcnow().isoformat() + "Z",
            payload={}
        )
        
        with get_db() as conn:
            storage.create_job(conn, job)
        
        self.log(f"✓ Created job: {job_id}")
        self.log("⏳ Waiting 20s for completion...")
        
        # Wait for completion
        deadline = time.time() + 20
        while time.time() < deadline:
            with get_db() as conn:
                result = conn.execute(
                    "SELECT status FROM jobs WHERE id=?", (job_id,)
                ).fetchone()
                
                if result:
                    status = result[0]
                    if status in ('completed', 'done'):
                        self.log(f"✅ PASS: Job completed (status={status})")
                        return True
                    elif status == 'failed':
                        self.log(f"❌ FAIL: Job failed")
                        return False
            time.sleep(0.5)
        
        # Timeout - check final status
        with get_db() as conn:
            result = conn.execute(
                "SELECT status FROM jobs WHERE id=?", (job_id,)
            ).fetchone()
            if result:
                self.log(f"❌ FAIL: Job stuck in status={result[0]}")
            else:
                self.log(f"❌ FAIL: Job disappeared")
        
        return False
    
    def test_2_spec_to_jobs(self):
        """Test 2: Spec creates 2 jobs (critical gap test)"""
        self.log("")
        self.log("=" * 60)
        self.log("TEST 2: Spec → Jobs Creation (CRITICAL GAP)")
        self.log("=" * 60)
        
        # Create task
        task_id = f"e2e_spec_task_{int(time.time())}"
        chain_id = f"e2e_chain_{int(time.time())}"
        
        task = Task(
            id=task_id,
            mission_id="e2e_test",
            name="E2E Spec Test",
            description="Spec to jobs test",
            kind="test",
            params={},
            created_at=datetime.utcnow().isoformat() + "Z"
        )
        storage.create_task(task)
        self.log(f"✓ Created task: {task_id}")
        
        # Create chain context and specs
        with get_db() as conn:
            storage.ensure_chain_context(conn, chain_id, task_id)
            self.log(f"✓ Created chain context: {chain_id}")
            
            specs = [
                {
                    "spec_id": f"spec1_{int(time.time())}",
                    "kind": "read_file",
                    "params": {"path": "core/main.py"},
                    "parent_job_id": ""
                },
                {
                    "spec_id": f"spec2_{int(time.time())}",
                    "kind": "read_file",
                    "params": {"path": "README.md"},
                    "parent_job_id": ""
                }
            ]
            
            storage.append_chain_specs(conn, chain_id, task_id, "root", "", specs)
            storage.set_chain_needs_tick(conn, chain_id, True)
            self.log(f"✓ Registered 2 specs, needs_tick=True")
        
        # Verify specs are in database
        with get_db() as conn:
            spec_count = conn.execute(
                "SELECT COUNT(*) FROM chain_specs WHERE chain_id=?", (chain_id,)
            ).fetchone()[0]
            self.log(f"✓ Verified: {spec_count} specs in database")
        
        self.log("⏳ Waiting 10s for ChainRunner to create jobs...")
        
        # Wait for ChainRunner to create jobs
        deadline = time.time() + 10
        jobs_created = False
        
        while time.time() < deadline:
            with get_db() as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE task_id=?", (task_id,)
                ).fetchone()[0]
                
                if count >= 2:
                    self.log(f"✓ ChainRunner created {count} jobs!")
                    jobs_created = True
                    break
            time.sleep(0.5)
        
        if not jobs_created:
            with get_db() as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE task_id=?", (task_id,)
                ).fetchone()[0]
                self.log(f"❌ FAIL: ChainRunner created only {count}/2 jobs")
                
                # Debug info
                needs_tick = conn.execute(
                    "SELECT needs_tick FROM chain_contexts WHERE chain_id=?", (chain_id,)
                ).fetchone()
                if needs_tick:
                    self.log(f"   Debug: needs_tick={needs_tick[0]}")
                
                pending_specs = conn.execute(
                    "SELECT COUNT(*) FROM chain_specs WHERE chain_id=? AND status='pending'",
                    (chain_id,)
                ).fetchone()[0]
                self.log(f"   Debug: {pending_specs} specs still pending")
            
            return False
        
        # Jobs created - now wait for completion
        self.log("⏳ Waiting 20s for jobs to complete...")
        deadline = time.time() + 20
        
        while time.time() < deadline:
            with get_db() as conn:
                completed = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE task_id=? AND status IN ('completed', 'done')",
                    (task_id,)
                ).fetchone()[0]
                
                if completed >= 2:
                    self.log(f"✅ PASS: {completed} jobs completed")
                    return True
            time.sleep(0.5)
        
        # Timeout - check final status
        with get_db() as conn:
            statuses = conn.execute(
                "SELECT status, COUNT(*) FROM jobs WHERE task_id=? GROUP BY status",
                (task_id,)
            ).fetchall()
            self.log(f"❌ FAIL: Jobs did not complete. Status breakdown:")
            for status, count in statuses:
                self.log(f"   {status}: {count}")
        
        return False
    
    def test_3_why_api_verification(self):
        """Test 3: WHY-API shows diagnostic traces"""
        self.log("")
        self.log("=" * 60)
        self.log("TEST 3: WHY-API Verification")
        self.log("=" * 60)
        
        try:
            from core.main import diagnostic_engine, baseline_tracker
            
            # Check diagnostic report
            report = diagnostic_engine.get_latest_report()
            if report:
                health = report.get('health_score', 'N/A')
                self.log(f"✓ Diagnostic report exists (health={health})")
            else:
                self.log(f"⚠ No diagnostic report (expected on first run)")
            
            # Check baselines
            baselines = baseline_tracker.get_all_baselines(recompute=False)
            metrics = baselines.get('metrics', [])
            self.log(f"✓ Baseline tracker has {len(metrics)} metrics")
            
            # Check state transitions
            log_path = Path("logs/state_transitions.jsonl")
            if log_path.exists():
                lines = log_path.read_text().strip().split('\n')
                self.log(f"✓ State transitions log has {len(lines)} entries")
            else:
                self.log(f"⚠ No state transitions log yet")
            
            self.log(f"✅ PASS: WHY-API components accessible")
            return True
            
        except Exception as e:
            self.log(f"❌ FAIL: WHY-API error: {e}")
            return False
    
    def run_all(self):
        """Run all tests and report results"""
        self.log("╔" + "=" * 58 + "╗")
        self.log("║" + " E2E Test Suite: Spec→Job Pipeline ".center(58) + "║")
        self.log("╚" + "=" * 58 + "╝")
        self.log("")
        
        # Run tests
        test1_pass = self.test_1_single_job()
        test2_pass = self.test_2_spec_to_jobs()
        test3_pass = self.test_3_why_api_verification()
        
        # Summary
        self.log("")
        self.log("=" * 60)
        self.log("RESULTS")
        self.log("=" * 60)
        self.log(f"Test 1 (Single Job):       {'✅ PASS' if test1_pass else '❌ FAIL'}")
        self.log(f"Test 2 (Spec→Jobs):        {'✅ PASS' if test2_pass else '❌ FAIL'}")
        self.log(f"Test 3 (WHY-API):          {'✅ PASS' if test3_pass else '❌ FAIL'}")
        self.log("=" * 60)
        
        all_pass = test1_pass and test2_pass and test3_pass
        
        if all_pass:
            self.log("✅ ALL TESTS PASSED")
            self.log("")
            self.log("System is ready for Asymmetry scoping!")
            return 0
        else:
            self.log("❌ SOME TESTS FAILED")
            self.log("")
            
            if not test1_pass:
                self.log("Next step: Check Dispatcher/Worker logs")
            elif not test2_pass:
                self.log("Next step: ChainRunner Investigation (T1)")
                self.log("  - Check claim_next_pending_spec() logic")
                self.log("  - Check _process_spec() job creation")
                self.log("  - Verify needs_tick flag handling")
            
            return 1

if __name__ == "__main__":
    suite = E2ETestSuite()
    sys.exit(suite.run_all())
