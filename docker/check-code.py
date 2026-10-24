"""Portable CI checks. Integration tests run separately inside an installed bench."""

import ast
import subprocess
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "saeenaria_portal" / "saeenaria_portal"


class InlineScripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inline = False
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.inline = "src" not in dict(attrs)

    def handle_endtag(self, tag):
        if tag == "script":
            self.inline = False

    def handle_data(self, data):
        if self.inline:
            self.scripts.append(data)


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


run("ruff", "check", ".")
run("ruff", "format", "--check", ".")
for path in [*APP.rglob("*.py"), *ROOT.joinpath("docker").glob("*.py")]:
    ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
for path in APP.joinpath("public", "js").glob("*.js"):
    run("node", "--check", str(path))
parser = InlineScripts()
parser.feed(APP.joinpath("www", "portal.html").read_text(encoding="utf-8"))
for script in parser.scripts:
    subprocess.run(
        ["node", "--check"], input=script, text=True, encoding="utf-8", cwd=ROOT, check=True
    )
print(
    "PASS scoped lint/format, all Python syntax, all public JavaScript and dashboard inline scripts"
)
