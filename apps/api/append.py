with open('database/schema.sql', 'a', encoding='utf-8') as f1, open('database/schema_restore.sql', 'r', encoding='utf-8') as f2:
    f1.write('\n' + f2.read())
