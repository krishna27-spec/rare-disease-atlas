# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "openai", "pydantic", "python-dotenv", "requests"]
# ///
"""Milestone 6 on molab: run gpt-oss-20b on the GPU and extract facts from abstracts.

Before you run it, upload to the notebook's file area (same folder as this notebook):
  abstracts.jsonl           from data/cache/ on your laptop
  src/llm.py, src/extract.py   (or let the notebook clone the repo, once it is public)
Turn the GPU on in the molab notebook settings first. When it finishes, download
edges_text_mined.jsonl and extractions.jsonl into data/cache/ on your laptop.
"""
import marimo

__generated_with = "0.0.0"
app = marimo.App()


@app.cell
def _():
    import json
    import os
    import subprocess
    import sys
    import time
    from pathlib import Path

    import marimo as mo
    import requests

    return Path, json, mo, os, requests, subprocess, sys, time


@app.cell
def _(mo, subprocess):
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                         capture_output=True, text=True)
    mo.md(f"**GPU:** `{gpu.stdout.strip() or 'NONE FOUND: turn the GPU on in notebook settings'}`")
    return


@app.cell
def _(Path, mo, subprocess):
    # Get src/ : use the uploaded files if they are there, otherwise clone the public repo.
    if not Path("src/extract.py").exists():
        subprocess.run(["git", "clone", "--depth", "1",
                        "https://github.com/krishna27-spec/rare-disease-atlas.git", "repo"], check=True)
        subprocess.run("cp -r repo/src ./src", shell=True, check=True)
    Path("src/__init__.py").touch()
    mo.md("`src/` is ready.")
    return


@app.cell
def _(mo, subprocess):
    # One-time install (several minutes). vLLM brings its own PyTorch.
    install = subprocess.run("pip install -q vllm", shell=True, capture_output=True, text=True)
    mo.md(f"vLLM install exit code: `{install.returncode}`\n\n```\n{install.stderr[-500:]}\n```")
    return


@app.cell
def _(requests, subprocess, time):
    # Start the model server in the background and wait until it answers.
    server = subprocess.Popen(
        ["vllm", "serve", "openai/gpt-oss-20b", "--port", "8000", "--max-model-len", "16384"],
        stdout=open("vllm.log", "w"), stderr=subprocess.STDOUT)
    for _ in range(120):  # up to 20 minutes (first run downloads the weights)
        try:
            if requests.get("http://localhost:8000/v1/models", timeout=2).ok:
                break
        except requests.RequestException:
            pass
        if server.poll() is not None:
            raise RuntimeError("vLLM exited; read vllm.log")
        time.sleep(10)
    else:
        raise RuntimeError("vLLM did not come up in 20 minutes; read vllm.log")
    return (server,)


@app.cell
def _(os, server):
    # Same variables as .env, so src/llm.py works unchanged.
    assert server.poll() is None
    os.environ["LLM_BASE_URL"] = "http://localhost:8000/v1"
    os.environ["LLM_API_KEY"] = "not-needed"
    os.environ["LLM_MODEL"] = "openai/gpt-oss-20b"
    return


@app.cell
def _(mo):
    limit = mo.ui.number(start=0, stop=5000, value=20, label="Abstracts to read (0 = all). Try 20 first.")
    mo.md(f"Start small to check quality, then set to 0 and re-run: {limit}")
    return (limit,)


@app.cell
def _(Path, limit):
    from src.extract import run

    run(Path("abstracts.jsonl"), Path("."), limit=limit.value or None, workers=16)
    return


@app.cell
def _(Path, json, mo):
    rows = [json.loads(l) for l in Path("edges_text_mined.jsonl").read_text().splitlines()]
    mo.md(f"**{len(rows)} verified facts.** Download `edges_text_mined.jsonl` and `extractions.jsonl` "
          "from the file browser into `data/cache/` on your laptop.")
    return


if __name__ == "__main__":
    app.run()
