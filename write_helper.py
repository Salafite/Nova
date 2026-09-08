import os, sys, base64
def write_file(path, content):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Successfully written {path} ({len(content)} chars)')

if __name__ == '__main__':
    target_path = sys.argv[1]
    b64_content = sys.argv[2]
    text = base64.b64decode(b64_content).decode('utf-8')
    write_file(target_path, text)
