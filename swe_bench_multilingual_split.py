import os
from datasets import load_dataset, DatasetDict

# Define the repository to language mapping
repo_to_lang = {
    "redis/redis": "c",
    "jqlang/jq": "c",
    "micropython/micropython": "c",
    "valkey-io/valkey": "c",
    "nlohmann/json": "cpp",
    "fmtlib/fmt": "cpp",
    "caddyserver/caddy": "go",
    "hashicorp/terraform": "go",
    "prometheus/prometheus": "go",
    "gohugoio/hugo": "go",
    "gin-gonic/gin": "go",
    "google/gson": "java",
    "apache/druid": "java",
    "projectlombok/lombok": "java",
    "apache/lucene": "java",
    "reactivex/rxjava": "java",
    "javaparser/javaparser": "java",
    "babel/babel": "jsts",
    "vuejs/core": "jsts",
    "facebook/docusaurus": "jsts",
    "immutable-js/immutable-js": "jsts",
    "mrdoob/three.js": "jsts",
    "preactjs/preact": "jsts",
    "axios/axios": "jsts",
    "phpoffice/phpspreadsheet": "php",
    "laravel/framework": "php",
    "php-cs-fixer/php-cs-fixer": "php",
    "briannesbitt/carbon": "php",
    "jekyll/jekyll": "ruby",
    "fluent/fluentd": "ruby",
    "fastlane/fastlane": "ruby",
    "jordansissel/fpm": "ruby",
    "faker-ruby/faker": "ruby",
    "rubocop/rubocop": "ruby",
    "tokio-rs/tokio": "rust",
    "uutils/coreutils": "rust",
    "nushell/nushell": "rust",
    "tokio-rs/axum": "rust",
    "burntsushi/ripgrep": "rust",
    "sharkdp/bat": "rust",
    "astral-sh/ruff": "rust",
}

# Invert keys to list of repos for easier filtering if needed, or just iterate.
# We want to iterate by language to create splits.
langs = sorted(list(set(repo_to_lang.values())))

def main():
    print("Loading SWE-bench/SWE-bench_Multilingual dataset...")
    # Load the test split
    dataset = load_dataset("SWE-bench/SWE-bench_Multilingual", split="test")
    
    # We will upload to this repo
    target_repo = "AlienKevin/SWE-bench_Multilingual"
    print(f"Target repository: {target_repo}")

    for lang in langs:
        print(f"Processing language: {lang}")
        
        # Get repos for this language
        lang_repos = [repo for repo, l in repo_to_lang.items() if l == lang]
        
        # Filter dataset
        def filter_fn(example):
            return example["repo"] in lang_repos
            
        lang_dataset = dataset.filter(filter_fn)
        
        print(f"  Found {len(lang_dataset)} examples for {lang}")
        
        if len(lang_dataset) > 0:
            print(f"  Pushing split '{lang}' to {target_repo}...")
            # Push as a split named after the language
            lang_dataset.push_to_hub(target_repo, split=lang)
            print(f"  Successfully pushed {lang}")
        else:
            print(f"  Warning: No examples found for {lang}!")

if __name__ == "__main__":
    main()
