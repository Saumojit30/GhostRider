with open('dataset/evidence/logs/service_events_ap_south_20260915.log', encoding='utf-8') as f:
    for line in f:
        if 'data_flow_' in line or 'backup_' in line:
            print(line.strip())
