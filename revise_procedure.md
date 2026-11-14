## Improved Alpha Research Procedure — For Claude Review and Revision

This is a revised procedure document based on actual findings from the alpha_research project (as of Oct-Nov 2026). Please review and revise where needed.

### What We Found (Real Data)

1. 30 alpha signal folders exist (alpha_01 through alpha_30, some duplicates: alpha_03_new, alpha_17_new, etc.)
2. 33 data files (CSV/JSON) in data/ folder being generated daily
3. Data files are named like: iv_rank_latest.csv, iv_skew_latest.csv, gamma_exposure_latest.csv, iv_term_structure_latest.csv
4. Some alpha folders are marked "Active" but have no corresponding data file (e.g., alpha_05_iv_rank_percentile needs iv_percentile_latest.csv not iv_rank_latest.csv)
5. Some folders are duplicates (alpha_28_iv_skew_dynamics duplicates alpha_02)
6. The review script (review_project.py) uses wrong file matching logic

### New Requirements (Based on User Requests)

A. **Data source expanded**: Now includes both yfinance (US options) and AKShare (China options — 510300 CSI 300 ETF, 510050 SSE 50 ETF, etc.)
B. **Scope expanded**: Includes SPY and QQQ as index ETFs (already covered), but also now China ETF options
C. **Two-track approach**: 
   - Options-based alpha (existing 20 signals)
   - Fundamental/value alpha (new: price vs MA256 & MA180 screening — fundamental_alpha/ repo)
D. **Daily build + review + validation + cleanup** (4 separate cron jobs)
E. **Clean duplicates and standardize file naming**

### Revised Cron Job Structure

1. **Nightly Build (2AM)**: Build new signals, fix broken ones, generate data
2. **Nightly Review (3AM)**: Audit quality, check file naming, validate CSV structure
3. **Nightly Validation (4AM)**: Run IC analysis on signals with ≥30 days of history
4. **Nightly Cleanup (5AM)**: Remove duplicates, standardize naming, update README

### Revised Task Descriptions (Clear and Actionable)

For Claude Code: please review these descriptions and revise them for clarity, accuracy, and completeness. Specifically:

- Check that each task description clearly states: which repo to work in, which tickers, which data source, which file naming convention, and what the output should be
- Ensure descriptions mention: yfinance + AKShare, 6 US tickers + 4 China ETF tickers, data/ folder, git commit
- Add error handling instructions
- Make sure the descriptions are not ambiguous about file naming (e.g., clearly state that output files must be named `{signal_name}_latest.csv` in data/)

Please execute this review and make revisions to:
- /Users/znding04/Work/alpha_research/README.md (update status table)
- The cron job descriptions (create/update 4 cron jobs with improved descriptions)
- Any relevant scripts

Then commit all changes.
