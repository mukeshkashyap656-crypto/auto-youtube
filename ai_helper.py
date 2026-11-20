"""
AI Helper - free (Gemini key se chalta hai).

Do kaam karta hai:
  1. fix  : koi video workflow fail ho to log padhkar wajah dhoondhta hai.
            Thodi der ki gadbad (network/quota) ho to ek baar dobara chalata hai,
            code ki galti ho to fix banakar alag branch + Pull Request bhejta hai.
  2. task : GitHub Issue ya comment mein "@ai <kaam>" likho, ye kaam karke
            Pull Request bhejta hai (ya sawal ka jawab deta hai).

Main code mein seedha kuch nahi daalta. Aap PR dekhkar "Merge" dabate ho.
"""
import json
import os
import py_compile
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

from google import genai
from google.genai import types

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

REPO = os.environ["GITHUB_REPOSITORY"]
MODELS = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
TEXT_EXT = (".py", ".yml", ".yaml", ".json", ".txt", ".md")
MAX_FILE_CHARS = 60000
MAX_ROUNDS = 3
IST = timezone(timedelta(hours=5, minutes=30))


def run(args, check=True, input_text=None):
    r = subprocess.run(args, capture_output=True, text=True, input=input_text)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed: {r.stderr.strip()[:500]}")
    return r.stdout


def repo_files():
    files = {}
    for path in run(["git", "ls-files"]).splitlines():
        if not path.endswith(TEXT_EXT) or path.startswith("history_"):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        if len(content) <= MAX_FILE_CHARS:
            files[path] = content
    return files


RULES = """You are a careful senior engineer who maintains a small GitHub repo that
automatically makes and uploads YouTube Shorts (Python + GitHub Actions).
The owner is not a programmer and reads Hinglish (Hindi in Roman script).

Reply with ONLY valid JSON in this exact shape:
{"action": "fix" | "rerun" | "none",
 "summary": "Hinglish, simple everyday words, 2-6 short lines: kya hua, kyun hua, kya kiya",
 "files": [{"path": "file/path.py", "content": "THE COMPLETE NEW FILE CONTENT"}]}

Rules:
- "rerun": the failure is temporary (network error, timeout, 429/quota, 5xx, service
  unavailable, model overloaded). No code change. files must be [].
- "fix": a real bug in the code. Change as little as possible and return the FULL
  content of every changed file (never a partial file, never "..." placeholders).
- "none": nothing to change (or the request is only a question - answer it in summary).
- Never touch anything inside .github/ (you are not allowed to push workflow files).
- Never remove features, never put secrets or keys in code, never invent model or
  library names - keep the Gemini model names already used in the repo.
- Keep existing style, logic and URLs unless they are the bug.
"""


def ask_gemini(prompt):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"].strip(),
                          http_options=types.HttpOptions(timeout=120000))  # 2 min per try
    last_err = None
    for attempt in range(8):
        model = MODELS[attempt % len(MODELS)]
        try:
            res = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2),
            )
            txt = (res.text or "").strip()
            match = re.search(r"\{.*\}", txt, re.DOTALL)
            data = json.loads(match.group(0) if match else txt)
            if data.get("action") in ("fix", "rerun", "none"):
                print("Answer from:", model)
                data.setdefault("files", [])
                data.setdefault("summary", "")
                return data
            raise ValueError("bad action field")
        except Exception as e:
            last_err = e
            wait = min(60, 10 * (attempt + 1))
            print(f"Attempt {attempt + 1} ({model}) failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)
    raise last_err or RuntimeError("Gemini se jawab nahi mila")


def check_changes(changes, old_files):
    """Gemini ke badlaav ki jaanch. Galti ho to list lautata hai."""
    problems = []
    for item in changes:
        path, content = item.get("path", ""), item.get("content", "")
        if not path or path.startswith((".github/", "/")) or ".." in path:
            problems.append(f"{path}: is file ko badalne ki ijazat nahi hai")
            continue
        old = old_files.get(path)
        if old is not None and len(content) < 0.6 * len(old):
            problems.append(f"{path}: nayi file purani se bahut chhoti hai (kat gayi lagti hai) - poori file do")
        if old and '__name__ == "__main__"' in old and '__name__ == "__main__"' not in content:
            problems.append(f'{path}: end ka `if __name__ == "__main__":` hissa gayab hai - poori file do')
        if path.endswith(".py"):
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as t:
                t.write(content)
            try:
                py_compile.compile(t.name, doraise=True)
            except py_compile.PyCompileError as e:
                problems.append(f"{path}: Python syntax galti: {str(e)[-300:]}")
            finally:
                os.unlink(t.name)
        if path.endswith(".json"):
            try:
                json.loads(content)
            except ValueError as e:
                problems.append(f"{path}: JSON galat hai: {e}")
    return problems


def solve(task_text):
    old_files = repo_files()
    files_block = "\n\n".join(f"===== FILE: {p} =====\n{c}" for p, c in old_files.items())
    prompt = f"{RULES}\n\n# REPO FILES\n{files_block}\n\n# TASK\n{task_text}"
    for rnd in range(MAX_ROUNDS):
        data = ask_gemini(prompt)
        if data["action"] != "fix":
            return data
        if not data["files"]:
            data["action"] = "none"
            return data
        problems = check_changes(data["files"], old_files)
        if not problems:
            return data
        print("Fix mein dikkat, dobara maang rahe hain:", problems)
        prompt += "\n\n# YOUR PREVIOUS ANSWER WAS REJECTED. Fix these problems and answer again:\n- " + "\n- ".join(problems)
    return {"action": "none", "files": [],
            "summary": "Maine 3 baar fix banane ki koshish ki par har baar jaanch mein galti mili, isliye kuch nahi badla. Claude chat mein ye link bhejiye."}


def open_pr(data, title):
    branch = "ai-fix/" + datetime.now(IST).strftime("%Y%m%d-%H%M%S")
    run(["git", "config", "user.name", "github-actions[bot]"])
    run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"])
    run(["git", "checkout", "-b", branch])
    for item in data["files"]:
        d = os.path.dirname(item["path"])
        if d:
            os.makedirs(d, exist_ok=True)
        with open(item["path"], "w", encoding="utf-8") as f:
            f.write(item["content"])
        run(["git", "add", item["path"]])
    run(["git", "commit", "-m", f"AI Helper: {title}"])
    run(["git", "push", "origin", branch])
    body = data["summary"] + "\n\n---\nAI Helper ne banaya. Theek lage to **Merge pull request** dabaiye, nahi to **Close** kar dijiye."
    r = subprocess.run(["gh", "pr", "create", "--repo", REPO, "--base", "main", "--head", branch,
                        "--title", f"AI Fix: {title}", "--body", body], capture_output=True, text=True)
    if r.returncode == 0:
        return r.stdout.strip()
    print("PR nahi bana:", r.stderr.strip()[:300])
    return (f"https://github.com/{REPO}/compare/main...{branch}?expand=1\n"
            "(Settings → Actions → General mein 'Allow GitHub Actions to create and approve pull requests' "
            "on kar dijiye, taaki agli baar PR apne aap bane.)")


def mode_fix():
    run_id = os.environ["RUN_ID"]
    run_name = os.environ.get("RUN_NAME", "Video workflow")
    attempt = int(os.environ.get("RUN_ATTEMPT", "1"))
    run_url = f"https://github.com/{REPO}/actions/runs/{run_id}"
    log = run(["gh", "run", "view", run_id, "--repo", REPO, "--log-failed"], check=False)
    log_tail = "\n".join(re.sub(r"^[^\t]*\t[^\t]*\t\S+Z ", "", l) for l in log.splitlines()[-250:])
    task = (f'The GitHub Actions workflow "{run_name}" FAILED (attempt {attempt}). '
            f"Find the cause from this log and decide rerun / fix / none.\n\n# FAILED LOG (last lines)\n{log_tail}")
    data = solve(task)

    extra = ""
    if data["action"] == "rerun":
        if attempt < 2:
            run(["gh", "run", "rerun", run_id, "--repo", REPO, "--failed"], check=False)
            extra = "\n\n🔁 Ye thodi der ki gadbad lagi, isliye maine run **ek baar dobara chala diya** hai."
        else:
            extra = "\n\n⚠️ Ye pehle hi dobara chal chuka tha, isliye ab dobara nahi chalaya. Kal subah ka run apne aap chalega."
    elif data["action"] == "fix":
        extra = "\n\n🛠️ Fix taiyar hai, dekhkar Merge kijiye:\n" + open_pr(data, f"{run_name} ki galti")

    today = datetime.now(IST).strftime("%d %b")
    body = f"**{run_name}** fail hua — [run dekhiye]({run_url})\n\n{data['summary']}{extra}"
    run(["gh", "issue", "create", "--repo", REPO, "--title", f"🤖 {run_name} fail hua ({today})", "--body", body], check=False)
    print(body)


def mode_task():
    number = os.environ["ISSUE_NUMBER"]
    request = os.environ.get("REQUEST", "")
    title = os.environ.get("ISSUE_TITLE", "")
    task = f"The owner asked (Hinglish):\nIssue title: {title}\nRequest: {request}\n\nDo it, or answer it if it is only a question."
    data = solve(task)
    msg = data["summary"] or "Ho gaya."
    if data["action"] == "fix":
        msg += "\n\n🛠️ Badlaav taiyar hai, dekhkar Merge kijiye:\n" + open_pr(data, title[:60] or "kaam")
    run(["gh", "issue", "comment", number, "--repo", REPO, "--body", msg], check=False)
    print(msg)


if __name__ == "__main__":
    {"fix": mode_fix, "task": mode_task}[sys.argv[1]]()
