"""Free AI sahara (backup) for when Gemini does not answer: GitHub Models.
Uses GitHub's own token inside GitHub Actions (workflow needs `permissions: models: read`), no extra key.
"""
import json
import os
import re
import time

import requests

# ---- AWS Bedrock (sirf free credit). Tabhi chalta hai jab secret AWS_BEARER_TOKEN_BEDROCK ho aur variable AWS_AI = on. ----
AWS_MODEL = "global.anthropic.claude-opus-4-6-v1"
AWS_REGION = "ap-southeast-2"
AWS_UNTIL = "2027-05-20"
AWS_DAILY = 30   # har channel (workflow) ki apni din ki ginti (UTC); atke loop par rok, paise ki seema NAHI


def _aws_slot(tok):
    repo, sha = os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_SHA", "")
    if not (repo and sha and tok):
        return False
    name = re.sub(r"[^a-z0-9]+", "-", os.environ.get("GITHUB_WORKFLOW", "").lower()).strip("-") or "channel"
    path = f"aws-use-{name}/{time.strftime('%Y-%m-%d', time.gmtime())}"
    head = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
    r = requests.get(f"https://api.github.com/repos/{repo}/git/matching-refs/{path}/", headers=head, timeout=30)
    if r.status_code != 200:
        print("AWS baari nahi mili: GitHub HTTP", r.status_code)
        return False
    for n in range(max([int(x["ref"].rsplit("/", 1)[1]) for x in r.json()], default=0) + 1, AWS_DAILY + 1):
        r = requests.post(f"https://api.github.com/repos/{repo}/git/refs", headers=head, timeout=30,
                          json={"ref": f"refs/{path}/{n}", "sha": sha})
        if r.status_code == 201:
            print(f"AWS baari {n}/{AWS_DAILY} ({name})")
            return True
        if r.status_code != 422 or "already exists" not in r.text:
            print("AWS baari nahi mili: GitHub HTTP", r.status_code)
            return False
    print("AWS: aaj ki seema poori")
    return False


def aws_json(prompt, ok, tok):
    """AWS se JSON. Na mile to None (kabhi error nahi uthata). Public log mein key ya poora error nahi."""
    key = os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "").strip()
    if os.environ.get("AWS_AI", "").strip().lower() != "on" or not key or time.strftime("%Y-%m-%d", time.gmtime()) > AWS_UNTIL:
        return None
    try:
        if not _aws_slot(tok):
            return None
        r = requests.post(f"https://bedrock-runtime.{AWS_REGION}.amazonaws.com/model/{AWS_MODEL}/converse", timeout=(15, 180),
                          headers={"Authorization": "Bearer " + key},
                          json={"messages": [{"role": "user", "content": [{"text": prompt}]}],
                                "inferenceConfig": {"maxTokens": 4000, "temperature": 0.7}})
        if r.status_code != 200:
            print("AWS fail: HTTP", r.status_code, r.headers.get("x-amzn-errortype", "").split(":")[0])
            return None
        body = r.json()
        if body.get("stopReason") != "end_turn":
            print("AWS fail: jawab adhoora")
            return None
        txt = "".join(c.get("text", "") for c in body["output"]["message"]["content"])
        data = json.loads(re.search(r"\{.*\}", txt, re.DOTALL).group(0))
        if ok(data):
            print("Script generated using AWS:", AWS_MODEL)
            return data
        print("AWS fail: JSON mein zaroori cheezein nahi")
    except Exception as e:
        print("AWS fail:", type(e).__name__)
    return None


MODELS = ["openai/gpt-4.1-mini", "openai/gpt-4o-mini", "deepseek/DeepSeek-V3-0324", "meta/Llama-3.3-70B-Instruct"]


def fallback_json(prompt, ok=lambda d: True):
    """Backup: pehle AWS (on ho to), phir GitHub Models. Returns the dict, or raises if nothing worked."""
    tok = (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()
    data = aws_json(prompt, ok, tok)
    if data is not None:
        return data
    if not tok:
        raise RuntimeError("GitHub token nahi (GH_TOKEN), sahara nahi chal sakta")
    last = None
    for m in MODELS:
        try:
            r = requests.post("https://models.github.ai/inference/chat/completions", timeout=180,
                              headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json", "Accept": "application/vnd.github+json",
                                       "X-GitHub-Api-Version": "2022-11-28"}, allow_redirects=False,
                              json={"model": m, "temperature": 0.9, "response_format": {"type": "json_object"},
                                    "messages": [{"role": "user", "content": prompt}]})
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
            body = r.json() if r.text.strip().startswith("{") else {}
            if not body.get("choices"):
                raise RuntimeError(f"jawab samajh nahi aaya: HTTP {r.status_code} {r.headers.get('location', '')} {r.text[:200]!r}")
            txt = (body["choices"][0]["message"].get("content") or "").strip()
            mt = re.search(r"\{.*\}", txt, re.DOTALL)
            data = json.loads(mt.group(0) if mt else txt)
            if ok(data):
                print("Script generated using GitHub Models:", m)
                return data
            raise ValueError("JSON mein zaroori cheezein nahi")
        except Exception as e:
            last = e
            print(f"GitHub Models {m} nahi chala: {str(e)[:160]}")
    raise RuntimeError(f"GitHub Models bhi nahi chala: {last}")


if __name__ == "__main__":   # self-test: python free_ai.py (inside GitHub Actions)
    print(fallback_json('Return only this JSON: {"segments": ["jai shri ram"]}', lambda d: bool(d.get("segments"))))
