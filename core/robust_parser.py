# sheratan_core_v2/robust_parser.py
# Robust JSON extraction from unstructured LLM responses

import json
import re
from typing import Optional, Dict, Any, List, Tuple


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from potentially unstructured text.
    
    Tries multiple strategies:
    1. Direct JSON parse (clean response)
    2. Extract JSON block from markdown code fence
    3. Find JSON object by brace matching
    4. Extract partial JSON structure
    
    Args:
        text: Raw text that may contain JSON
        
    Returns:
        Parsed JSON dict or None if extraction failed
    """
    if not text or not isinstance(text, str):
        return None
    
    text = text.strip()
    
    # Strategy 1: Direct parse (ideal case)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract from markdown code fence
    result = _extract_from_code_fence(text)
    if result:
        return result
    
    # Strategy 3: Find JSON by brace matching
    result = _extract_by_brace_matching(text)
    if result:
        return result
    
    # Strategy 4: Try to fix common JSON errors
    result = _try_fix_json(text)
    if result:
        return result
    
    # Strategy 5: Handle root-less JSON (missing outer braces)
    if '"ok":' in text or '"action":' in text:
        # Wrap in braces and try Strategy 1 again
        try:
            return json.loads("{" + text + "}")
        except:
            pass
    
    return None


def _extract_from_code_fence(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from markdown code fences like ```json ... ```"""
    # Match ```json ... ``` or ``` ... ```
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
    
    return None


def _extract_by_brace_matching(text: str) -> Optional[Dict[str, Any]]:
    """Find JSON object by matching braces { }"""
    # Find first { and try to match closing }
    start_idx = text.find('{')
    if start_idx == -1:
        return None
    
    brace_count = 0
    end_idx = -1
    in_string = False
    escape_next = False
    
    for i, char in enumerate(text[start_idx:], start=start_idx):
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                end_idx = i
                break
    
    if end_idx > start_idx:
        json_candidate = text[start_idx:end_idx + 1]
        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError:
            pass
    
    return None


def _try_fix_json(text: str) -> Optional[Dict[str, Any]]:
    """Try to fix common JSON errors."""
    # Find potential JSON region
    start = text.find('{')
    end = text.rfind('}')
    
    if start == -1 or end == -1 or end <= start:
        return None
    
    json_region = text[start:end + 1]
    
    # Strategy: Try to fix and parse
    fixes = [
        # Fix 1: Replace single quotes with double quotes
        lambda s: s.replace("'", '"'),
        # Fix 2: Remove trailing commas before } or ]
        lambda s: re.sub(r',\s*([\}\]])', r'\1', s),
        # Fix 3: Add missing commas between objects/keys
        lambda s: re.sub(r'\}\s*"\s*([a-zA-Z_])', r'},\n"\1', s), # Missing comma between } and "key"
        # Fix 4: Fix single backslashes in Windows paths (e.g. C:\path -> C:\\path)
        # Avoid fixing valid escapes like \", \\, \n, \t, etc.
        lambda s: re.sub(r'\\(?![\\/bfnrtu"])', r'\\\\', s),
        # Fix 5: Add missing quotes around keys
        lambda s: re.sub(r'(\{|\,)\s*(\w+)\s*:', r'\1"\2":', s),
    ]
    
    current = json_region
    for fix in fixes:
        try:
            current = fix(current)
            return json.loads(current)
        except:
            pass
            
    # Try applying all fixes sequentially
    try:
        current = json_region
        for fix in fixes:
            current = fix(current)
        return json.loads(current)
    except:
        pass
    
    return None


def extract_lcp_response(text: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Extract LCP-formatted response with error tracking.
    
    Returns:
        Tuple of (parsed_json, list_of_extraction_attempts)
    """
    attempts = []
    
    # Try standard extraction
    result = extract_json_from_text(text)
    if result:
        attempts.append("direct_extraction: success")
        return result, attempts
    
    attempts.append("direct_extraction: failed")
    
    # Try extracting only the LCP-relevant fields using a more robust brace-matching finder
    lcp_fields = ["ok", "action", "new_jobs", "commentary", "files", "error"]
    partial = {}
    
    for field in lcp_fields:
        # Search for "field": pattern
        field_marker = f'"{field}"'
        start_search = text.find(field_marker)
        if start_search == -1:
            # Try case-insensitive
            field_marker = field_marker.lower()
            start_search = text.lower().find(field_marker)
            if start_search == -1:
                continue
        
        # Find the colon
        colon_idx = text.find(':', start_search + len(field_marker))
        if colon_idx == -1:
            continue
        
        # Find value start (first non-whitespace)
        value_start = -1
        for i in range(colon_idx + 1, len(text)):
            if not text[i].isspace():
                value_start = i
                break
        
        if value_start == -1:
            continue
            
        # If it's a string, find end quote
        if text[value_start] == '"':
            end_quote = -1
            escape = False
            for i in range(value_start + 1, len(text)):
                if escape:
                    escape = False
                    continue
                if text[i] == '\\':
                    escape = True
                    continue
                if text[i] == '"':
                    end_quote = i
                    break
            if end_quote != -1:
                partial[field] = text[value_start+1:end_quote]
        
        # If it's an object or array, use brace matching
        elif text[value_start] in ('{', '['):
            opener = text[value_start]
            closer = '}' if opener == '{' else ']'
            depth = 0
            end_idx = -1
            in_str = False
            esc = False
            
            for i in range(value_start, len(text)):
                c = text[i]
                if esc:
                    esc = False
                    continue
                if c == '\\':
                    esc = True
                    continue
                if c == '"':
                    in_str = not in_str
                    continue
                if in_str:
                    continue
                
                if c == opener:
                    depth += 1
                elif c == closer:
                    depth -= 1
                    if depth == 0:
                        end_idx = i
                        break
            
            if end_idx != -1:
                value_str = text[value_start:end_idx + 1]
                try:
                    partial[field] = json.loads(value_str)
                except:
                    # Try to fix partial value JSON too
                    fixed = _try_fix_json(value_str)
                    if fixed is not None:
                        partial[field] = fixed
                    else:
                        partial[field] = value_str # Fallback to raw string
        
        # If it's a primitive
        else:
            # Find next delimiter (comma, newline, or closing brace/bracket)
            match = re.search(r'([^\n,}\]]+)', text[value_start:])
            if match:
                value_str = match.group(1).strip()
                if value_str.lower() == 'true': partial[field] = True
                elif value_str.lower() == 'false': partial[field] = False
                elif value_str.isdigit(): partial[field] = int(value_str)
                else: partial[field] = value_str
    
    if partial:
        attempts.append(f"partial_extraction: found {list(partial.keys())}")
        return partial, attempts
    
    attempts.append("partial_extraction: no LCP fields found")
    return None, attempts


def create_safe_mode_diagnostic_jobs(error_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Create diagnostic job specifications for Safe-Mode.
    
    When the system enters Safe-Mode due to repeated errors,
    instead of just stopping, create diagnostic jobs to analyze the problem.
    
    Args:
        error_context: Information about what went wrong
        
    Returns:
        List of job specifications for diagnostic analysis
    """
    jobs = []
    
    # Job 1: Analyze recent logs
    jobs.append({
        "kind": "read_file",
        "name": "Diagnostic: Read recent logs",
        "params": {
            "path": "/workspace/project/logs/latest.log",
            "max_lines": 100
        },
        "diagnostic": True
    })
    
    # Job 2: Check system state
    jobs.append({
        "kind": "llm_call",
        "name": "Diagnostic: Analyze error pattern",
        "params": {
            "prompt": f"""Analyze this error context and suggest fixes:

Error Type: {error_context.get('error_type', 'unknown')}
Error Message: {error_context.get('error_message', 'N/A')}
Failed Attempts: {error_context.get('failed_attempts', 0)}
Last Successful Action: {error_context.get('last_success', 'unknown')}

Provide specific, actionable recommendations.""",
            "response_format": "lcp"
        },
        "diagnostic": True
    })
    
    # Job 3: List project files for context
    jobs.append({
        "kind": "list_files",
        "name": "Diagnostic: List project structure",
        "params": {
            "root": "/workspace/project",
            "patterns": ["*.py", "*.json", "*.md"],
            "max_depth": 2
        },
        "diagnostic": True
    })
    
    return jobs


def validate_lcp_response(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that a parsed response conforms to LCP format.
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    if not isinstance(data, dict):
        return False, ["Response is not a dictionary"]
    
    # Check required field: ok
    if "ok" not in data:
        issues.append("Missing 'ok' field")
    elif not isinstance(data["ok"], bool):
        issues.append("'ok' field should be boolean")
    
    # Check action field
    if "action" not in data:
        issues.append("Missing 'action' field")
    elif not isinstance(data.get("action"), str):
        issues.append("'action' field should be string")
    
    # If action is create_followup_jobs, check new_jobs
    if data.get("action") == "create_followup_jobs":
        if "new_jobs" not in data:
            issues.append("Action 'create_followup_jobs' requires 'new_jobs' field")
        elif not isinstance(data.get("new_jobs"), list):
            issues.append("'new_jobs' should be a list")
        else:
            for i, job in enumerate(data["new_jobs"]):
                if not isinstance(job, dict):
                    issues.append(f"new_jobs[{i}] should be a dictionary")
                elif "kind" not in job:
                    issues.append(f"new_jobs[{i}] missing 'kind' field")
    
    return len(issues) == 0, issues
