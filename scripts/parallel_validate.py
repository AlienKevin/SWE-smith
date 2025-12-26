#!/usr/bin/env python3
"""
Parallel validation script - validate 10 repos at a time in parallel.

This script runs validation for JavaScript repos in parallel batches,
significantly speeding up the overall validation process.
"""

import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

# List all JavaScript repos - ONLY 15 REPOS WITH FIXED PARSERS
JS_REPOS = [
    # ====== PARSER FIXES - 15 REPOS TO VALIDATE ======
    "websockets/ws",           # Fixed: Jest → Mocha
    "Modernizr/Modernizr",     # Fixed: default → Mocha
    "Unitech/pm2",             # Fixed: default → Mocha
    "bootstrap-vue/bootstrap-vue",  # Fixed: default → Jest
    "emotion-js/emotion",      # Fixed: default → Jest
    "enzymejs/enzyme",         # Fixed: Jest → Mocha
    "forwardemail/superagent", # Fixed: Jest → Mocha
    "iamkun/dayjs",            # Fixed: Jest → Mocha
    "jquery/jquery",           # Fixed: Mocha → QUnit
    "kriskowal/q",             # Fixed: Jest → Mocha
    "mholt/PapaParse",         # Fixed: Jest → Mocha
    "nock/nock",               # Fixed: Jest → Mocha
    "piskelapp/piskel",        # Fixed: Jest → Karma
    "remy/nodemon",            # Fixed: Jest → Mocha
    "segmentio/evergreen",     # Fixed: default → Jest
    
    # ====== PREVIOUSLY VALIDATED (COMMENTED OUT) ======
    # "balderdashy/sails",  # Already validated: 66/157 valid bugs (42%)
    # "josdejong/jsoneditor",  # 84/647 valid bugs (13%)
    # "layui/layui",  # 0/105 - only 1 test in suite, bugs didn't break it
    # "gka/chroma.js",  # 17/33 valid bugs (52%)
    
    # ====== OTHER REPOS (COMMENTED OUT) ======
    # "jorgebucaran/hyperapp",
    # "serverless/serverless",
    # "louislam/uptime-kuma",
    # "Qix-/color",
    # "marko-js/marko",
    # "brianc/node-postgres",
    # "mdx-js/mdx",
    # "immutable-js/immutable-js",
    # "mrdoob/three.js",
    # "mui/material-ui",
    # "apache/echarts",
    # "nightwatchjs/nightwatch",
    # "facebookexperimental/Recoil",
    # "Shopify/draggable",
    # "akiran/react-slick",
    # "novnc/noVNC",
    # "forwardemail/supertest",
    # "hakimel/reveal.js",
    # "bpampuch/pdfmake",
    # "parallax/jsPDF",
    # "expressjs/multer",
    # "handsontable/handsontable",
    # "pqina/filepond",
    # "hapijs/joi",
    # "foliojs/pdfkit",
    # "reactjs/react-transition-group",
    # "josdejong/mathjs",
    # "impress/impress.js",
    # "remarkjs/react-markdown",
    # "jantimon/html-webpack-plugin",
    # "koajs/koa",
    # "jashkenas/backbone",
    # "mochajs/mocha",
    # "sql-js/sql.js",
    # "advplyr/audiobookshelf",
    # "typicode/json-server",
    # "highlightjs/highlight.js",
    # "necolas/react-native-web",
    # "diegomura/react-pdf",
    # "webpack/webpack",
    # "markedjs/marked",
    # "redux-saga/redux-saga",
    # "babel/babel",
    # "riot/riot",
    # "anuraghazra/github-readme-stats",
    # "svg/svgo",
    # "Automattic/mongoose",
    # "usebruno/bruno",
    # "axios/axios",
    # "webtorrent/webtorrent",
    # "caolan/async",
    # "welldone-software/why-did-you-render",
    # "expressjs/express",
    # "11ty/eleventy",
    # "GoogleChrome/workbox",
    # "sveltejs/svelte",
    # "HabitRPG/habitica",
    # "tj/commander.js",
    # "elbywan/wretch",
    # "Netflix/falcor",
    # "h5bp/html5-boilerplate",
    # "PrismJS/prism",
    # "davila7/claude-code-templates",
]


def repo_already_validated(repo):
    """Check if validation_summary.json exists for this repo."""
    import os
    try:
        from swesmith.profiles import registry
        profile = registry.get(repo)
        summary_path = f"logs/run_validation/{profile.repo_name}/validation_summary.json"
        return os.path.exists(summary_path)
    except Exception:
        # If we can't get the profile, assume not validated
        return False


def validate_single_repo(repo_info):
    """Validate a single repo and return the result."""
    idx, repo = repo_info
    start_time = datetime.now()
    
    # Check if already validated
    if repo_already_validated(repo):
        return {
            "repo": repo,
            "status": "SKIPPED",
            "result": "Already validated (validation_summary.json exists)",
            "elapsed_seconds": 0
        }
    
    try:
        result = subprocess.run(
            [
                "uv", "run", "python", "scripts/bug_gen.py",
                "--language", "javascript",
                "--repos", repo,
                "--validate-only"
            ],
            capture_output=True,
            text=True,
            timeout=1200  # 20 minutes per repo
        )
        
        # Extract validation summary from output
        output = result.stdout
        for line in output.split("\n"):
            if "valid bugs" in line and repo in line:
                elapsed = (datetime.now() - start_time).total_seconds()
                return {
                    "repo": repo,
                    "status": "SUCCESS",
                    "result": line.strip(),
                    "elapsed_seconds": elapsed
                }
        
        # If we didn't find the summary, return the last few lines
        elapsed = (datetime.now() - start_time).total_seconds()
        last_lines = "\n".join(output.split("\n")[-5:])
        return {
            "repo": repo,
            "status": "UNKNOWN",
            "result": f"No summary found. Last output:\n{last_lines}",
            "elapsed_seconds": elapsed
        }
                
    except subprocess.TimeoutExpired:
        elapsed = (datetime.now() - start_time).total_seconds()
        return {
            "repo": repo,
            "status": "TIMEOUT",
            "result": "TIMEOUT after 20 minutes",
            "elapsed_seconds": elapsed
        }
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        return {
            "repo": repo,
            "status": "ERROR",
            "result": f"ERROR: {e}",
            "elapsed_seconds": elapsed
        }


def main():
    start_idx = 0  # Start from the beginning
    if len(sys.argv) > 1:
        start_idx = int(sys.argv[1])
    
    repos_to_validate = JS_REPOS[start_idx:]
    total_repos = len(repos_to_validate)
    
    print(f"\n{'='*80}")
    print(f"PARALLEL VALIDATION - Processing {total_repos} repos with max 5 concurrent")
    print(f"{'='*80}\n")
    
    results = {}
    completed = 0
    
    # Process repos in parallel with max 5 workers
    max_workers = 5
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_repo = {
            executor.submit(validate_single_repo, (i + start_idx, repo)): repo
            for i, repo in enumerate(repos_to_validate)
        }
        
        # Process results as they complete
        for future in as_completed(future_to_repo):
            repo = future_to_repo[future]
            try:
                result_data = future.result()
                completed += 1
                
                # Print progress
                status_symbol = {
                    "SUCCESS": "✓",
                    "TIMEOUT": "⏱",
                    "ERROR": "✗",
                    "UNKNOWN": "?",
                    "SKIPPED": "⊘"
                }[result_data["status"]]
                
                elapsed_min = result_data["elapsed_seconds"] / 60
                print(f"[{completed}/{total_repos}] {status_symbol} {repo} ({elapsed_min:.1f}min)")
                if result_data["status"] == "SUCCESS":
                    print(f"    {result_data['result']}")
                else:
                    print(f"    {result_data['result']}")
                print()
                
                results[repo] = result_data
                
            except Exception as e:
                completed += 1
                print(f"[{completed}/{total_repos}] ✗ {repo}: Unexpected error: {e}\n")
                results[repo] = {
                    "repo": repo,
                    "status": "ERROR",
                    "result": f"Unexpected error: {e}",
                    "elapsed_seconds": 0
                }
    
    # Print final summary
    print(f"\n\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}\n")
    
    success_count = sum(1 for r in results.values() if r["status"] == "SUCCESS")
    timeout_count = sum(1 for r in results.values() if r["status"] == "TIMEOUT")
    error_count = sum(1 for r in results.values() if r["status"] == "ERROR")
    skipped_count = sum(1 for r in results.values() if r["status"] == "SKIPPED")
    
    print(f"Total: {len(results)} repos")
    print(f"  ✓ Success: {success_count}")
    print(f"  ⊘ Skipped: {skipped_count}")
    print(f"  ⏱ Timeout: {timeout_count}")
    print(f"  ✗ Error: {error_count}")
    print()
    
    # Print successful validations
    if success_count > 0:
        print("Successful validations:")
        for repo, data in sorted(results.items()):
            if data["status"] == "SUCCESS":
                print(f"  {repo}: {data['result']}")
    
    # Print timeouts
    if timeout_count > 0:
        print("\nTimeouts:")
        for repo, data in sorted(results.items()):
            if data["status"] == "TIMEOUT":
                print(f"  {repo}")
    
    # Print errors
    if error_count > 0:
        print("\nErrors:")
        for repo, data in sorted(results.items()):
            if data["status"] == "ERROR":
                print(f"  {repo}: {data['result']}")


if __name__ == "__main__":
    main()
