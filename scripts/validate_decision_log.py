"""
validate_decision_log.py - Robust Decision Trace Log Validator

Validates every line in logs/decision_trace.jsonl against the schema.
Exit code 0 = all valid, 1 = validation errors found.

Usage:
    python scripts/validate_decision_log.py
    python scripts/validate_decision_log.py --log logs/custom.jsonl
    python scripts/validate_decision_log.py --verbose
"""

import json
import sys
from pathlib import Path
import jsonschema
from typing import Tuple, List


def load_schema(schema_path: Path) -> dict:
    """Load and return the JSON schema"""
    if not schema_path.exists():
        print(f"❌ Schema not found: {schema_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_log(
    log_path: Path,
    schema: dict,
    verbose: bool = False
) -> Tuple[int, int, List[dict]]:
    """
    Validate decision trace log.
    
    Returns:
        (valid_count, invalid_count, errors)
    """
    if not log_path.exists():
        print(f"ℹ️  Log file not found: {log_path}")
        return 0, 0, []
    
    valid_count = 0
    invalid_count = 0
    errors = []
    
    with open(log_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                # Parse JSON
                event = json.loads(line)
                
                # Validate against schema
                jsonschema.validate(instance=event, schema=schema)
                
                valid_count += 1
                
                if verbose:
                    node_id = event.get('node_id', 'unknown')[:8]
                    intent = event.get('intent', 'unknown')
                    status = event.get('result', {}).get('status', 'unknown')
                    print(f"  ✓ Line {line_num:3d}: {intent:15s} {status:10s} (node={node_id}...)")
                
            except json.JSONDecodeError as e:
                invalid_count += 1
                errors.append({
                    'line': line_num,
                    'error': 'Invalid JSON',
                    'message': str(e),
                    'content': line[:100]
                })
                
            except jsonschema.ValidationError as e:
                invalid_count += 1
                errors.append({
                    'line': line_num,
                    'error': 'Schema Validation Failed',
                    'message': e.message,
                    'path': '/' + '/'.join(str(p) for p in e.absolute_path) if e.absolute_path else '/',
                    'validator': e.validator
                })
    
    return valid_count, invalid_count, errors


def main():
    """Main validation routine"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate decision trace log')
    parser.add_argument('--log', default='logs/decision_trace.jsonl', help='Path to log file')
    parser.add_argument('--schema', default='schemas/decision_trace_v1.json', help='Path to schema')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    log_path = Path(args.log)
    schema_path = Path(args.schema)
    
    print("=" * 60)
    print("Decision Trace Log Validator")
    print("=" * 60)
    print(f"Log:    {log_path}")
    print(f"Schema: {schema_path}")
    print()
    
    # Load schema
    schema = load_schema(schema_path)
    
    # Validate log
    valid_count, invalid_count, errors = validate_log(log_path, schema, args.verbose)
    
    # Report
    print()
    print("=" * 60)
    print("Validation Results")
    print("=" * 60)
    print(f"✓ Valid events:   {valid_count}")
    print(f"✗ Invalid events: {invalid_count}")
    
    if errors:
        print()
        print("Errors:")
        for err in errors:
            print(f"\n  Line {err['line']}:")
            print(f"    Error: {err['error']}")
            print(f"    Message: {err['message']}")
            if 'path' in err:
                print(f"    Path: {err['path']}")
            if 'validator' in err:
                print(f"    Validator: {err['validator']}")
            if 'content' in err:
                print(f"    Content: {err['content']}...")
    
    print("=" * 60)
    
    if invalid_count > 0:
        print("❌ VALIDATION FAILED")
        sys.exit(1)
    else:
        print("✅ VALIDATION PASSED")
        sys.exit(0)


if __name__ == '__main__':
    main()
