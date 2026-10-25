with open('dataset/evidence/databases/customer_data_read_replica_20260921.sql', encoding='utf-8') as f:
    for line in f:
        if any(k in line for k in ['994', '1007', '9528', 'user_53', 'diya.k']):
            print(line.strip())
