#!/bin/bash

# Modified from https://github.com/mhausenblas/mkdocs-deploy-gh-pages

set -e

function print_info() {
    echo -e "\e[36mINFO: ${1}\e[m"
}

if ! git config --get user.name; then
    git config --global user.name "github-actions[bot]"
fi

print_info "setup with GITHUB_TOKEN"
remote_repo="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"

if ! git config --get user.email; then
    git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"
fi

git remote rm origin
git remote add origin "${remote_repo}"

mkdocs gh-deploy --config-file "/documentation/mkdocs.yml" --force
