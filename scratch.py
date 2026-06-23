import re

file_path = r'd:\graphmind-\graphmind\app\modules\knowledge_bases\service.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r',\s*status_code=(\d+)\)', r', meta={"status_code": \1})', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Replaced successfully')
