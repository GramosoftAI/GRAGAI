import pathlib
import urllib.parse

p = pathlib.Path('v:/graphmind/app/core/config.py')
text = p.read_text('utf-8')

old = 'return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"'
new = '''import urllib.parse
        encoded_pw = urllib.parse.quote_plus(urllib.parse.unquote_plus(self.postgres_password))
        return f"postgresql+asyncpg://{self.postgres_user}:{encoded_pw}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"'''

if old in text:
    p.write_text(text.replace(old, new), 'utf-8')
    print("Successfully replaced.")
else:
    print("Old text not found.")
