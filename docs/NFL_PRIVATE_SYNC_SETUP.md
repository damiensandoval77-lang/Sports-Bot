# Enable unattended NFL PrizePicks snapshot sync

The private NFL repository already collects and freezes PrizePicks lines. The
public NFL website grades only frozen pre-kickoff predictions that reached
`docs/nfl/data/`; the sync must run without copying private credentials into
browser code.

## One-time GitHub configuration

1. In GitHub, create a **fine-grained personal access token** scoped to the
   private `damiensandoval77-lang/Nfl-Bot` repository only. Give it the
   minimum repository permission **Contents: Read-only**. Do not grant write
   access or access to all repositories. Set an expiration/rotation policy.
2. Open the public `damiensandoval77-lang/Sports-Bot` repository and choose
   **Settings → Secrets and variables → Actions → New repository secret**.
   Name it exactly `NFL_PRIVATE_READ_TOKEN`. Paste the token only into
   GitHub's secret input, never into chat, JavaScript, a commit or logs.
3. Merge the validated sync pull request after that secret exists (or have
   a maintainer merge it), then open
   **Actions → Sync private NFL lines for public grading → Run workflow**.
4. Confirm the job says how many validated rows were copied. Then check
   **NFL frozen-pick grading and accuracy ledger** and the NFL dashboard.

## Expected behavior

- Private data is read using the token inside GitHub Actions; the token is
  not shipped to the public site.
- Every six hours during the NFL season, the latest complete snapshot is
  checked, copied atomically and archived before kickoff.
- Finalized games are graded from verified public player box scores.
  Missing results stay pending; no backfilled predictions or false losses.
- If the token is missing or expires, sync fails with a clear job error and
  **keeps the last-good public snapshot**. The dashboard may show stale
  odds until the token is rotated.
- Avoid committing an incomplete feed and avoid deployment churn when the
  private snapshot has not changed.

This is a deliberate one-time credential requirement. The GitHub
`GITHUB_TOKEN` belonging to public Sports-Bot does not automatically have
access to a different private repository.
