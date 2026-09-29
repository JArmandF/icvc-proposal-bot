# ICVC proposal bot

Posts every new ICVC SNS proposal to a Slack channel and @mentions the people you choose.

- Checks every 10 minutes (GitHub Actions, free).
- Data source: the public ICP dashboard API for the ICVC SNS (root `nuywj-oaaaa-aaaaq-aadta-cai`).
- Remembers the last proposal it posted in `state/last_seen.json` (currently `180`, so the first alert will be #181).

## Setup (about 10 minutes)

### 1. Create the Slack webhook
1. Go to https://api.slack.com/apps and click **Create New App** > **From scratch**.
2. Name it `ICVC Proposal Bot`, pick the DFINITY workspace, click **Create App**.
3. In the left menu open **Incoming Webhooks**, switch it **On**.
4. Click **Add New Webhook to Workspace**, choose the channel, click **Allow**.
   (If the workspace needs admin approval, Slack will show a "Request" button; an admin must approve.)
5. Copy the webhook URL (`https://hooks.slack.com/services/...`). Treat it like a password.
6. Invite the app to the channel if it's private: type `/invite @ICVC Proposal Bot` in the channel.

### 2. Get the two Slack member IDs
For each person: click their name in Slack > **View full profile** > **⋮** (More) > **Copy member ID**.
IDs look like `U01AB2CD3EF`.

### 3. Put the code on GitHub
1. Create a new repository at https://github.com/new (e.g. `icvc-proposal-bot`). Public is recommended:
   Actions minutes are free and unlimited, and nothing sensitive is in the code (the webhook lives in encrypted secrets).
2. Upload `notify.py`, `README.md`, `state/last_seen.json` and `.github/workflows/icvc-proposals.yml`
   keeping the same folder structure.
   Tip: the `.github` folder is hidden on macOS. Use **Add file > Create new file**, type
   `.github/workflows/icvc-proposals.yml` as the name, and paste the file's content.

### 4. Add the secrets
Repository **Settings > Secrets and variables > Actions > New repository secret**:

| Name | Value |
|---|---|
| `SLACK_WEBHOOK_URL` | the webhook URL from step 1 |
| `SLACK_MENTION_IDS` | the two member IDs, comma-separated: `U01AB2CD3EF,U04XY5ZW6VU` |

### 5. Test it
**Actions** tab > **ICVC proposal alerts** > **Run workflow** > tick *Send a test message* > **Run workflow**.
A message for proposal #180 should appear in the channel within a minute, with both people tagged.

From then on it runs by itself every 10 minutes.

## Notes
- GitHub may delay scheduled runs by a few minutes at busy times.
- In a private repo on a free GitHub plan, change the cron to `*/30 * * * *` to stay within the 2,000 free minutes/month.
- GitHub pauses scheduled workflows in public repos with no activity for 60 days; if that happens, click **Enable workflow** in the Actions tab.
- To add or remove people, just edit the `SLACK_MENTION_IDS` secret.
- Run locally: `SLACK_WEBHOOK_URL=... SLACK_MENTION_IDS=... python3 notify.py --test` (or `--dry-run` to print without posting).
