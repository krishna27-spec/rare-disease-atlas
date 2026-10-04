# Setup: molab + Claude Code for the Rare Disease Atlas

## Short answer: yes, with one twist

**Use molab for the heavy AI work, and your own laptop (with Claude Code) for everything else.**

What I checked about molab ([docs](https://docs.marimo.io/guides/molab/), [GPU announcement](https://marimo.io/blog/reintroducing-molab)):
- It's free, "GPUs and all, as long as usage is reasonable".
- Each notebook gets 4 CPUs and 32 GB RAM, and you can switch on an **NVIDIA RTX Pro 6000 with 96 GB of GPU memory**. That's big enough to run **gpt-oss-20b, and even gpt-oss-120b**, for free. Your laptop's 8 GB GPU can't do that.
- Limits: a notebook stops after 12 hours, or after 90 minutes of doing nothing. File storage is limited and not guaranteed to last, **so always download your results.**
- Claude Code can connect to a running molab notebook through **"Pair with an agent"** in the notebook menu (marimo pair).

Why not do *everything* on molab: your code, data and app need to live in a GitHub repo for judging, and Claude Code works best on files on your own computer. molab sessions also stop and lose files. So:

| Where | What happens there |
|---|---|
| **Your laptop + Claude Code** | Write all the code, download the free data files, build the graph, build the app, push to GitHub |
| **molab (free GPU)** | One big run: gpt-oss reads hundreds of abstracts and pulls out facts. You download the results file |
| **Groq / OpenRouter (free API)** | Backup for extraction, and the live "explain this to Maria" button in the app |
| **Streamlit Cloud or Hugging Face Spaces** | Hosts the finished app for the judges |

**Is gpt-oss OK for the prize rule?** gpt-oss is OpenAI's own open-weight model, so it should count as "leveraging OpenAI's models". Confirm once with the organisers.

---

## Step 1. Install the tools on your laptop (20 min)

Your screenshot shows Ubuntu. Open a terminal and run these one at a time.

```bash
# 1. Basic tools
sudo apt update && sudo apt install -y git curl jq

# 2. uv: installs Python and packages for you
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Node.js (needed for the marimo skills installer)
sudo apt install -y nodejs npm

# 4. Claude Code
curl -fsSL https://claude.ai/install.sh | bash
```

Close and reopen the terminal, then check: `uv --version`, `claude --version`.

**Optional backup: Ollama** (runs gpt-oss on your laptop, slowly, because your GPU has only 8 GB):
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gpt-oss:20b      # about 13 GB download
```

---

## Step 2. Get your free accounts and keys (20 min, do it while things install)

| What | Where | What to copy |
|---|---|---|
| GitHub repo | github.com → New repository → name `rare-disease-atlas`, **Public**, add a README | The repo URL |
| molab | [molab.marimo.io](https://molab.marimo.io/) → sign in | Nothing, just be logged in |
| Groq key | console.groq.com → API Keys | `gsk_...` key |
| OpenRouter key | openrouter.ai → Keys | `sk-or-...` key |
| NCBI key (PubMed, 10 requests/s instead of 3) | ncbi.nlm.nih.gov → sign in → Account settings → API Key Management | The key |
| Claude key (second reviewer, your $25) | platform.claude.com → API keys | `sk-ant-...` key |

Groq's free tier (checked today): about 30 requests/minute and **200,000 tokens/day** for `openai/gpt-oss-20b`, enough for roughly 150 abstracts a day. That's why the big run goes on molab. OpenRouter's free model allows 50 requests/day.

---

## Step 3. Set up the project folder (10 min)

```bash
cd ~
git clone https://github.com/<your-username>/rare-disease-atlas.git
cd rare-disease-atlas
```

1. Download [CLAUDE.md](CLAUDE.md) from this project and put it in this folder. Claude Code reads it automatically every time it starts here.
2. Create a file called `.env` in the folder (Claude Code will also make an `.env.example`):

```
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_your_groq_key
LLM_MODEL=openai/gpt-oss-20b
OPENROUTER_API_KEY=sk-or-your_key
NCBI_API_KEY=your_ncbi_key
NCBI_EMAIL=your_email_here
ANTHROPIC_API_KEY=sk-ant-your_key
```

⚠️ Never paste these keys into chat, screenshots or GitHub.

3. Add the marimo helpers for Claude Code:
```bash
npx skills add marimo-team/skills
```
Then start Claude Code (`claude`) and type these two lines inside it:
```
/plugin marketplace add marimo-team/marimo-pair
/plugin install marimo-pair@marimo-pair
```

---

## Step 4. Start building with Claude Code

```bash
cd ~/rare-disease-atlas
claude
```

Your first message to Claude Code:

> Read CLAUDE.md. I'm a beginner. Do Milestone 1, explain each step in simple words, and stop when the hello test works.

After that, one milestone at a time:

> Do Milestone 2. Show me the disease table before moving on.

Tips:
- Let it run commands; it will ask permission. Read what it asks.
- After each milestone say: *"Commit and push this milestone to GitHub."*
- If something breaks, paste the error and say *"fix this and explain what went wrong."*
- To watch a notebook while Claude edits it: `uv run marimo edit --watch notebooks/explore.py` in a second terminal.

**You don't download any data by hand.** Claude Code writes scripts that download everything in the CLAUDE.md data table (MONDO, HPO, Orphadata, HGNC, Reactome, ClinVar, PubMed, ClinicalTrials.gov, NIH RePORTER). The only manual data is the patient organisation list (20–30 rows from NORD, Global Genes and EURORDIS). Claude Code can draft it, but you must open each website to confirm it's real and active.

---

## Step 5. The big extraction run on molab (Milestone 6)

When Claude Code has made `notebooks/extract_molab.py` and `data/cache/abstracts.jsonl`:

1. Go to molab.marimo.io and create a new notebook (or upload `extract_molab.py`).
2. Click the **notebook specs button in the header** and switch the **GPU on**.
3. Upload `abstracts.jsonl` with the file panel in the sidebar.
4. Run the notebook. It installs vLLM, loads gpt-oss-20b (the first load takes several minutes), then processes the abstracts.
5. **Download `edges_text_mined.jsonl` as soon as it finishes** and put it in `data/cache/` on your laptop. molab can delete files.
6. Keep the tab active; molab stops a notebook after 90 minutes of no activity.

Optional: in the molab notebook menu, choose **"Pair with an agent"**, copy the prompt it shows, and paste it into Claude Code. Claude Code can then run and fix cells in the molab notebook directly.

If molab is busy or fails, run the same extraction through Groq or OpenRouter on your laptop, over two days or with fewer abstracts.

---

## Step 6. Finish

- Milestones 7–9 in Claude Code: connections, app, 10× page, README.
- Deploy: share.streamlit.io → New app → pick your GitHub repo → `app/app.py`. Add your keys under **Secrets** there, not in the code.
- Record the 1-minute walkthrough following Maria.

## Rough timeline

| When | What |
|---|---|
| Now (1 hour) | Steps 1–3, plus Milestone 1 |
| Next 4 hours | Milestones 2–5 (data and graph) |
| Then 2 hours | Milestone 6 on molab |
| Then 5 hours | Milestones 7–8 (connections and app) |
| Last 2–3 hours | Milestone 9, deploy, video |
