with open('dataset/evidence/logs/service_events_ap_south_20260915.log', encoding='utf-8') as f:
    lines = [f.readline() for _ in range(30)]

for line in lines:
    print(line.strip())
