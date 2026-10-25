with open('dataset/evidence/logs/service_events_ap_south_20260915.log', encoding='utf-8') as f:
    for line in f:
        if 'minjun' in line or 'user_12' in line or '9914' in line or '9797' in line or '2945' in line:
            print(line.strip())
