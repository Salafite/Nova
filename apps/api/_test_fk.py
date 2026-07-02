import re

sql = """
    product_id      INT NOT NULL REFERENCES T0003(id) ON DELETE CASCADE,
    price_list_id   INT REFERENCES T0083(id),
    created_by      INT REFERENCES T0021(id),
"""

def get_tn(s):
    m = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["\']?(\w+)["\']?\s*\(', s, re.I)
    return m.group(1).upper() if m else None

all_fk_alters = []

def repl(m):
    ref_table = m.group(1)
    trail = m.group(3) or ''
    on_cascade = m.group(2) or ''
    pos = m.start()
    before = sql[:pos].rstrip()
    words = before.split()
    col_name = words[0] if words else 'unknown'
    all_fk_alters.append(
        f'ALTER TABLE T0004 ADD CONSTRAINT fk_T0004_{col_name} '
        f'FOREIGN KEY ({col_name}) REFERENCES {ref_table}(id){on_cascade};'
    )
    return trail

result = re.sub(
    r'\s+REFERENCES\s+["\']?(\w+)["\']?\(\w+\)(\s+ON\s+(?:DELETE|UPDATE)\s+CASCADE)?([,\s]*)',
    repl, sql, flags=re.I
)

print("RESULT:")
print(result)
print("FK alters:")
for a in all_fk_alters:
    print(f"  {a}")
