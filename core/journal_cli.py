import sys
import argparse
import json
from pathlib import Path
from core.ledger_journal import LedgerJournal

def main():
    parser = argparse.ArgumentParser(description="Sheratan Ledger Journal CLI")
    parser.add_argument("--journal", type=Path, default=Path("ledger_events.jsonl"), help="Path to journal file")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # Verify command
    subparsers.add_parser("verify", help="Verify the hash chain integrity")
    
    # Replay command
    replay_parser = subparsers.add_parser("replay", help="Replay history to reconstruct state")
    replay_parser.add_argument("--out", type=Path, help="Optional path to save replayed state")
    
    args = parser.parse_args()
    
    if not args.journal.exists():
        print(f"Error: Journal file {args.journal} not found.")
        sys.exit(1)
        
    journal = LedgerJournal(args.journal)
    
    if args.command == "verify":
        print(f"Verifying journal: {args.journal}...")
        if journal.verify_chain():
            print("SUCCESS: Hash chain is intact.")
        else:
            print("FAILURE: Hash chain is broken or tampered with.")
            sys.exit(1)
            
    elif args.command == "replay":
        print(f"Replaying journal: {args.journal}...")
        try:
            state = journal.replay()
            print("Replay completed.")
            print("\nReconstructed Account Balances:")
            for acc, bal in state.items():
                print(f"  {acc}: {bal}")
                
            if args.out:
                with open(args.out, "w") as f:
                    json.dump({"accounts": {acc: {"balance": bal} for acc, bal in state.items()}}, f, indent=2)
                print(f"\nReplayed state saved to {args.out}")
        except Exception as e:
            print(f"Error during replay: {e}")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
