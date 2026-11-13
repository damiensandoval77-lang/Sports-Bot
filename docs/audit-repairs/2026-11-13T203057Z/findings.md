# PARTIAL: three monitoring repairs merged



Run 2026-11-13T20:30:57+00:00 to 2026-11-13T20:38:41.264144+00:00 (464 seconds). Three new defects repaired; two verified through actual production behavior, future-time rejection verified through regression tests.



[PR426](https://github.com/damiensandoval77-lang/Sports-Bot/pull/426). Merge cd6bed804d99c761fa743eec92760bc831050c66. Public release unchanged: dp-public-qa-labels-20261113-r36.



## D1 (medium)

Future odds/tracker timestamps accepted as fresh.

Reject observations more than five minutes ahead; preserve bounded clock skew.

16 targeted tests pass locally and in production job; future rejection itself regression-tested, not observed against real future-dated provider data.



## D2 (medium)

Failed health jobs discarded machine-readable results.

Write JSON and upload with always(), failing visibly if evidence missing.

Production run43503079373 fails honestly for stale retired sportsbook feeds; artifact14075525833 downloaded and verified.



## D3 (high)

Phone test passed zero cards when games were outside three-hour near-tip window; fixed five-second loading wait.

Require rendered cards for authentic saved forecasts in next24hours, wait up to45seconds for rendering, retain failure screenshot.

Before run43501919665 passed0cards and skipped footer. After run43503079393 passes395cards/608expected saved picks, nine checks pass and footer verified.



## Coverage and remaining work

426 existing active heads and425 historical PRtips fetched and compared. Four older conflicts remain. All174workflow definitions statically audited;396recent run observations reconciled with preceding full inventory. [Workflow table](workflows.md). [Exact conflicts](open-pr-conflicts.json).

Static audit:1253files,571Python,266JSON,38JavaScript syntax targets;0errors,45warnings,384mutable action references. Not a complete vulnerability scan.

NBA9/9games have saved quotes/forecasts.634standardquotes,345/362currentoffers matched,17missing.29archived threshold gaps include12researchreceipts and17noAIreceipt.904AI-only and608line-backed records.

November12NBA:388AIrecords=332graded+56DNP;327researchrecords=318settled+9void.0overdue captured records. NFL135standardgrades including3pushes;52wins/80losses=39.39%;0standardpending.932alternategrades and4alternatepending excluded. Missing never-captured pretip evidence remains unrecoverable, countunknown.

Fresh ESPN checks match9NBAidentities/tips and18NFLplayerrows. Published calendars1200NBAfixedfixtures/272NFLfixtures.

Production feed-health failure43503079373 now retains artifact14075525833; it still truthfully flags legacy odds8445minutesold and0/12sportsbookcoverage. This is distinct from current PrizePicks coverage. Cross-domain failure43496519907 reports incomplete primary captures, not missing standard NFL grades. Readiness failure43499675627 and capture43500671731 remain data failures.

Phone before43501919665:0cards,footerSKIP,falsePASS. Phone after43503079393:395cards,9checksPASS,608upcoming saved picks,exact asset match,noJSerrors. PhysicalSafari/active-gamepacing unverified.



17current primary offers missing;29archived thresholds have no validated primary model (12research receipts,17withoutAIreceipt). Missing authentic evidence never fabricated.

Paid source refresh forbidden; legacy sportsbook feed remains stale and gates remain red.

Pages branch-mode cancellations remain; available connector cannot change admin source setting. Owner action: Settings > Pages > Source > GitHub Actions.

Four older PR conflicts and384mutable action references/45architecture warnings remain; this run does not complete all repair work.

No active games: live30-second pacing unobserved; physical Safari and full Underdog pipeline unverified.

Exhaustive dependency vulnerability scans and execution of every historical tip not performed.



Please notify Damien using enabled ChatGPT mobile notifications; delivery unconfirmed.