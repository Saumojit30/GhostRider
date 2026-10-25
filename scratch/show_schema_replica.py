with open('dataset/evidence/databases/customer_data_read_replica_20260921.sql', encoding='utf-8') as f:
    text = f.read()

# show first 1000 characters
print(text[:1200])
