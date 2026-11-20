"""Free AI sahara (backup) for when Gemini does not answer: GitHub Models.
Uses GitHub's own token inside GitHub Actions (workflow needs `permissions: models: read`), no extra key.
"""
import json
import os
import re

import requests

MODELS = ["openai/gpt-4.1-mini", "openai/gpt-4o-mini", "deepseek/DeepSeek-V3-0324", "meta/Llama-3.3-70B-Instruct"]


def fallback_json(prompt, ok=lambda d: True):
    """Ask GitHub Models for JSON. Returns the dict, or raises if none of the free models worked."""
    tok = (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()
    if not tok:
        raise RuntimeError("GitHub token nahi (GH_TOKEN), sahara nahi chal sakta")
    last = None
    for m in MODELS:
        try:
            r = requests.post("https://models.github.ai/inference/chat/completions", timeout=180,
                              headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                              json={"model": m, "temperature": 0.9, "response_format": {"type": "json_object"},
                                    "messages": [{"role": "user", "content": prompt}]})
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
            txt = r.json()["choices"][0]["message"]["content"].strip()
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
