import sys
sys.path.insert(0, '.')

from core import storage
from core.database import get_db

# Check latest jobs
jobs = sorted(storage.list_jobs(), key=lambda x: x.created_at, reverse=True)[:5]
print(f'Latest 5 jobs:')
for j in jobs:
    print(f'  {j.id[:8]} | status={j.status} | created={j.created_at}')
    if j.result:
        print(f'    result: {str(j.result)[:80]}')

# Check chain specs
with get_db() as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT chain_id, needs_tick FROM chain_context ORDER BY rowid DESC LIMIT 5')
    rows = cursor.fetchall()
    print(f'\nRecent chains: {len(rows)}')
    for r in rows:
        chain_id = r[0]
        needs_tick = r[1]
        print(f'  {chain_id[:30]} | needs_tick={needs_tick}')
        
        # Check specs for this chain
        cursor.execute('SELECT spec_id, status FROM chain_specs WHERE chain_id=? LIMIT 3', (chain_id,))
        specs = cursor.fetchall()
        for s in specs:
            print(f'    spec {s[0][:12]} | status={s[1]}')
