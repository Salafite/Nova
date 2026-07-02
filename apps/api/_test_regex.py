import re

sql = """
    created_by      INT          REFERENCES T0021(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by      INT          REFERENCES T0021(id),
    update_number   INT          NOT NULL DEFAULT 1
"""

all_fk_alters = []
def repl(m):
    trail = m.group(1) or ''
    pos = m.start()
    before = sql[:pos].rstrip()
    words = before.split()
    col_name = words[0] if words else 'unknown'
    ref_match = re.search(r'REFERENCES\s+["\']?(\w+)["\']?\((\w+)\)', m.group(0), re.I)
    ref_table = ref_match.group(1) if ref_match else '???'
    ref_col = ref_match.group(2) if ref_match else 'id'
    all_fk_alters.append(
        f'ALTER TABLE ? ADD CONSTRAINT fk_?_{col_name} FOREIGN KEY ({col_name}) REFERENCES {ref_table}({ref_col});'
    )
    print(f"Match: '{m.group(0)}' -> trail: '{trail}'")
    return trail

result = re.sub(r'\s+REFERENCES\s+["\']?(\w+)["\']?\(\w+\)([,\s]*)', repl, sql, flags=re.I)

print("RESULT:")
print(repr(result))
print("FK alters:")
for a in all_fk_alters:
    print(f"  {a}")
