# tests/verify_phase10_1.py
import sys
import os
from pathlib import Path
import json
import uuid

# Add root project to path
sys.path.append(str(Path(__file__).parent.parent))

from core.database import get_db, init_db
from core import storage
from core.job_chain_manager import JobChainManager
from core.result_ref import safe_get

def test_1_chain_context_and_limits():
    print("\n--- TEST 1: Chain Context & Limits ---")
    chain_id = f"test-chain-{uuid.uuid4().hex[:8]}"
    task_id = "test-task"
    
    with get_db() as conn:
        # 1. Ensure context
        ctx = storage.ensure_chain_context(conn, chain_id, task_id)
        print(f"Created context: {ctx['chain_id']}")
        
        # 2. Set artifact with limits (file_list)
        # Default limit is 50
        large_list = [f"file_{i}.txt" for i in range(100)]
        storage.set_chain_artifact(conn, chain_id, "file_list", large_list)
        
        ctx = storage.get_chain_context(conn, chain_id)
        file_list = ctx["artifacts"]["file_list"]["value"]
        meta = ctx["artifacts"]["file_list"]["meta"]
        
        print(f"File list size: {len(file_list)} (Meta truncated: {meta.get('truncated')})")
        assert len(file_list) == 50
        assert meta.get("truncated") is True
        
        # 3. Set artifact with limits (file_blobs)
        # max_total_bytes = 200,000, max_per_file = 50,000
        large_blobs = {
            "big.txt": {"content": "X" * 60000}, # should be truncated to 50k
            "many.txt": {"content": "Y" * 160000} # should hit total budget
        }
        storage.set_chain_artifact(conn, chain_id, "file_blobs", large_blobs)
        
        ctx = storage.get_chain_context(conn, chain_id)
        blobs = ctx["artifacts"]["file_blobs"]["value"]
        blobs_meta = ctx["artifacts"]["file_blobs"]["meta"]
        
        print(f"Stored blobs: {list(blobs.keys())}")
        print(f"Total bytes in meta: {blobs_meta.get('total_bytes')}")
        
        assert len(blobs["big.txt"]["content"]) == 50000
        assert blobs["big.txt"].get("truncated") is True
        # Total bytes should be around 50k because 'many.txt' (160k) + 'big.txt' (50k) > 200k.
        # Wait, if big.txt is 50k, and many.txt is 160k, then 50+160 = 210 > 200.
        # So only big.txt fits? Or many.txt is skipped.
        assert blobs_meta.get("truncated") is True
    print("✅ TEST 1 PASSED")

def test_2_specs_and_deduplication():
    print("\n--- TEST 2: Specs & Deduplication ---")
    chain_id = f"test-chain-{uuid.uuid4().hex[:8]}"
    task_id = "test-task"
    root_job_id = "root-job"
    parent_job_id = "parent-job"
    
    with get_db() as conn:
        specs = [
            {"kind": "read_file", "params": {"path": "a.txt"}},
            {"kind": "read_file", "params": {"path": "a.txt"}}, # Duplicate
            {"kind": "read_file", "params": {"path": "b.txt"}},
        ]
        
        inserted = storage.append_chain_specs(conn, chain_id, task_id, root_job_id, parent_job_id, specs)
        print(f"Inserted spec IDs: {inserted}")
        assert len(inserted) == 2
        
        pending = storage.list_pending_chain_specs(conn, chain_id)
        print(f"Pending specs count: {len(pending)}")
        assert len(pending) == 2
    print("✅ TEST 2 PASSED")

def test_3_resolution():
    print("\n--- TEST 3: Result-Ref Resolution ---")
    chain_id = f"test-chain-{uuid.uuid4().hex[:8]}"
    task_id = "test-task"
    root_job_id = "root-job"
    parent_job_id = "parent-job"
    source_job_id = f"source-job-{uuid.uuid4().hex[:8]}"
    
    # Block 1: Setup context and specs
    with get_db() as conn:
        # Setup context
        storage.ensure_chain_context(conn, chain_id, task_id)
        storage.set_chain_artifact(conn, chain_id, "file_list", ["a.py", "b.py"])
        
    # Block 2: Setup source job (create_job opens its own connection)
    from core.models import Job
    job = Job(
        id=source_job_id,
        task_id=task_id,
        payload={"kind": "walk_tree"},
        status="completed",
        result={"ok": True, "files": [{"name": "deep.js"}]},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z"
    )
    storage.create_job(job)

    # Block 3: Add specs
    spec1_id = f"spec-1-{uuid.uuid4().hex[:4]}"
    spec2_id = f"spec-2-{uuid.uuid4().hex[:4]}"
    with get_db() as conn:
        specs = [
            {
                "spec_id": spec1_id,
                "kind": "read_file_batch",
                "params": {
                    "paths_from_artifact": "file_list",
                    "dummy": "value"
                }
            },
            {
                "spec_id": spec2_id,
                "kind": "analyze",
                "params": {
                    "inputs_from_job_result": {
                        "job_id": source_job_id,
                        "json_path": "files[0].name",
                        "target_param": "target_file"
                    }
                }
            }
        ]
        storage.append_chain_specs(conn, chain_id, task_id, root_job_id, parent_job_id, specs)
        
    # Block 4: Use chain manager to resolve (opens its own connection)
    manager = JobChainManager(chain_dir="data/chains", chain_index=None, storage=storage)
    
    # Resolve spec 1
    params1 = manager.resolve_chain_spec(chain_id=chain_id, spec_id=spec1_id)
    print(f"Resolved spec-1 params: {params1}")
    assert params1["paths"] == ["a.py", "b.py"]
    assert "paths_from_artifact" not in params1
    
    # Resolve spec 2
    params2 = manager.resolve_chain_spec(chain_id=chain_id, spec_id=spec2_id)
    print(f"Resolved spec-2 params: {params2}")
    assert params2["target_file"] == "deep.js"
    assert "inputs_from_job_result" not in params2

    print("✅ TEST 3 PASSED")

if __name__ == "__main__":
    init_db()
    try:
        test_1_chain_context_and_limits()
        test_2_specs_and_deduplication()
        test_3_resolution()
        print("\n✨ ALL PHASE 10.1 VERIFICATION TESTS PASSED! ✨")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
