import csv
from datetime import datetime

with open("dataset/system_activity.csv", encoding="utf-8") as f:
    acts = list(csv.DictReader(f))

# Let's find all deletion_worker activities
worker_acts = [a for a in acts if a['source_system'] == 'deletion_worker']
print(f"Total deletion_worker activities: {len(worker_acts)}")

# Group activities into contiguous blocks/sessions (where activities are within 15 minutes of each other)
sessions = []
cur_session = []
for a in sorted(worker_acts, key=lambda x: x['event_time']):
    t = datetime.fromisoformat(a['event_time'].replace('Z', '+00:00'))
    if not cur_session:
        cur_session.append((t, a))
    else:
        last_t = cur_session[-1][0]
        if (t - last_t).total_seconds() <= 900: # within 15 mins
            cur_session.append((t, a))
        else:
            sessions.append([x[1] for x in cur_session])
            cur_session = [(t, a)]
if cur_session:
    sessions.append([x[1] for x in cur_session])

print(f"Total deletion worker sessions: {len(sessions)}")
for idx, s in enumerate(sessions[:10]):
    print(f"Session {idx+1} ({len(s)} acts): {s[0]['event_time']} to {s[-1]['event_time']}")
    res_in_s = [f"{a['target_system']}:{a['resource_id']}" for a in s]
    print(f"  {res_in_s[:6]}")
