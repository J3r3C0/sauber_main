from typing import Any, Dict, Optional

def update_context_from_job_result(
    conn,
    *,
    chain_id: str,
    job_kind: str,
    job_id: str,
    result: Dict[str, Any],
    set_chain_artifact_fn,
) -> Optional[str]:
    """
    Updates the chain context artifacts based on the type of job result received.
    
    Args:
        conn: The database connection.
        chain_id: ID of the chain.
        job_kind: Kind of the job (e.g., 'walk_tree', 'read_file_batch').
        job_id: ID of the source job.
        result: The result payload from the worker.
        set_chain_artifact_fn: Callback to the storage function for setting artifacts.
        
    Returns:
        The artifact key that was updated, or None if no update occurred.
    """
    if not isinstance(result, dict):
        return None

    # Handle walk_tree or list_files results: populate the file_list artifact
    if job_kind in ["walk_tree", "list_files"] and result.get("ok"):
        # The worker might return 'paths' or 'files'
        paths = result.get("paths") or result.get("files") or []
        meta = {"source_job_id": job_id, "kind": job_kind}
        set_chain_artifact_fn(conn, chain_id, "file_list", paths, meta)
        return "file_list"

    # Handle read_file (singular) results
    if job_kind == "read_file" and result.get("ok"):
        content = result.get("content", "")
        path = result.get("path") or result.get("rel_path")
        if path:
            # Store in a per-file artifact map or just update file_blobs
            # Let's keep a 'file_blobs' map for all content
            ctx = storage.get_chain_context(conn, chain_id)
            blobs = ctx.get("artifacts", {}).get("file_blobs", {}).get("value", {})
            blobs[path] = content
            
            meta = {"source_job_id": job_id, "updated_file": path}
            set_chain_artifact_fn(conn, chain_id, "file_blobs", blobs, meta)
            return "file_blobs"

    # Handle read_file_batch results: populate the file_blobs artifact
    if job_kind == "read_file_batch" and result.get("ok"):
        files = result.get("files") or {}
        meta = {
            "source_job_id": job_id, 
            "total_bytes": result.get("total_bytes"),
            "kind": "read_file_batch"
        }
        set_chain_artifact_fn(conn, chain_id, "file_blobs", files, meta)
        return "file_blobs"

    return None
