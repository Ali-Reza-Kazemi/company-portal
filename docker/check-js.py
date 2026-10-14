import pathlib
import re
import subprocess
import tempfile
for file in pathlib.Path('/workspace/apps/saein_portal/saein_portal/www').glob('*.html'):
    for code in re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',file.read_text(),re.S):
        if not code.strip(): continue
        with tempfile.NamedTemporaryFile(mode='w',suffix='.js') as tmp:
            tmp.write(code);tmp.flush()
            subprocess.run(['node','--check',tmp.name],check=True)
print('Inline JavaScript syntax checks passed')
