# ITD Free Daily Discovery Radar — opt-in only

This is a **standalone**, standard-library-only GitHub metadata collector. It is **NOT running automatically** until a repository owner enables the workflow and verifies a successful first run.

### Deploy safely (requires the user's permission)
1. Make an **independent** GitHub repository dedicated solely to **public tool-catalog data**. Do **not** use HALFAYA, CPF1/2/3, Local Market Price, or a repository with secrets. A public repo with only these generic URLs/data offers a documented free path for standard GitHub-hosted Actions. Do not publish private user details or project data.
2. Copy `scripts/`, `data/`, `registry/`, `discover_tests.py`, and `.github/workflows/` to that repository, preserving paths. Do not edit existing production repositories.
3. On GitHub, authorize Actions on this repository and run **Actions → ITD Free Daily Repository Radar → Run workflow** manually. Verify first success, actual runtime, billing eligibility and `data/latest.json` timestamp before claiming it works.
4. The UTC cron `37 2 * * *` targets 05:37 Iraq time daily. Scheduled Actions may be delayed, skipped or disabled. Verify the `generated_at_utc` timestamp; never promise perfect daily execution.
5. After a successful run, provide `https://raw.githubusercontent.com/OWNER/REPO/BRANCH/data/latest.json` (public catalog only) to ITD and configure `registry/discovery-config.json`'s `remote_snapshot_url` **through an authorized plugin update**. ChatGPT can then fetch verified catalog data on demand if it has web/GitHub access; the ChatGPT plugin does **not** self-update in the background.

### Cost protection
No model inference, API subscriptions, tokens, credits, coins, SaaS trials or payments. The GitHub workflow uses the built-in `GITHUB_TOKEN` for read-only public metadata. Public standard hosted runners are documented as free; private-repo included minutes vary and are not a guaranteed no-cost choice. Third-party repository names or GitHub stars never mean zero-cost execution.

### Trust protection
Scans GitHub repository metadata and a few bounded README links. No cloning, no install scripts, no code execution from linked projects, no automatic licenses accepted, no automatic upgrades, merges, or deployments. A discovered repo remains a candidate pending full audit. API rate limits and GitHub availability can cause partial results.

Run locally (when internet works):
```
python -m unittest discover_tests.py -v
python scripts/discover_github.py --max-api-calls 50
```
