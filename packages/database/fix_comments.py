import re

with open('database/schema.sql', 'r', encoding='utf-8') as f:
    content = f.read()

# Move COMMENT ON TABLE to after the corresponding CREATE TABLE for each table
# Pattern: COMMENT ON TABLE T0001 IS '...';   (BEFORE CREATE TABLE)
# Fix: move to immediately after the CREATE TABLE's closing );

for num in range(1, 24):
    tid = f'T{num:04d}'
    # Find the comment line before CREATE TABLE
    comment_match = re.search(
        rf"(COMMENT ON TABLE {tid} IS '[^']*';)\s*(?=\n-- .*\nCREATE TABLE {tid}\b)",
        content
    )
    if comment_match:
        comment_line = comment_match.group(1)
        # Remove it from current position
        content = content.replace(comment_line + '\n\n', '', 1)
        # Insert it after the CREATE TABLE closing );
        # Find the closing ); of the CREATE TABLE
        create_match = re.search(
            rf"(CREATE TABLE {tid}[\s\S]*?^\);)\s*",
            content
        )
        if create_match:
            insert_pos = create_match.end()
            content = content[:insert_pos] + '\n' + comment_line + content[insert_pos:]

with open('database/schema.sql', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
