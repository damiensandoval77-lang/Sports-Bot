"""Retry a prepared research-only commit across unrelated main updates.

Never force-push or replay inference across changed inputs. The caller must
recompute after a nonzero result. Only the two research output files may change.
"""
import subprocess

OUTPUTS={'docs/short_history_model.json','docs/short_history_model_validation.json'}
INPUTS={'docs/current_form.json','docs/prizepicks.json','docs/prizepicks_model_input.json',
        'docs/lagged_matchup_all_market_ledger.json','docs/injury_context.json',
        'docs/underdog_nba_injury_alerts.json','docs/free_nba_injury_watch.json'}

def can_replay(paths):
    return not any(p in INPUTS or p.startswith(('iphone_bot/','models/','data/','.github/workflows/'))
                   or 'requirements' in p for p in paths)

def push(run=subprocess.run):
    def git(*args):
        return run(['git',*args],capture_output=True,text=True,check=False)
    changed=git('diff','--name-only','HEAD^','HEAD')
    if changed.returncode or not set(changed.stdout.splitlines())<=OUTPUTS:
        return 1
    for _ in range(4):
        if git('push','origin','HEAD:main').returncode==0:return 0
        if git('fetch','origin','main').returncode:return 1
        upstream=git('diff','--name-only','HEAD^','origin/main')
        if upstream.returncode or not can_replay(upstream.stdout.splitlines()):return 1
        # Concurrent changes to our output must conflict, never be overwritten.
        if git('rebase','--autostash','origin/main').returncode:
            git('rebase','--abort')
            return 1
    return 1

if __name__=='__main__':raise SystemExit(push())
