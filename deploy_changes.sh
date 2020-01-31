#!/bin/bash
#
# Execute all config changes in a repo from the last 'in_prod' tag.
# Update 'in_prod' if successful.
#
# Script assumes CWD is a git repo and has the branch/commit that should be compared to 'in_prod' checked out.
# Script also assumes cloudgenix_config is installed and working (pip install cloudgenix_config)
#
# Variables expected set by the CI/CD before this script:
# AUTH_TOKEN = Valid tenant_super CloudGenix Auth Token
# TRAVIS_COMMIT = Current commit hash

# Debug script (if needed)
set -x

# Set up git for log commit back to master.
git config --global user.email "travisci-worker-ebob9@travis-ci.org"
git config --global user.name "travisci-worker-ebob9"

# Remove existing "origin"
git remote rm origin
# Add new "origin" with access token in the git URL for authentication
git remote add origin "https://travisci-worker-ebob9:${GITHUB_REPO_TOKEN}@github.com/ebob9/travis-sandbox.git" > /dev/null 2>&1

# DEBUG - find out why things arent working
git remote get-url --all origin
git show-ref -s in_prod


# Get latest commit tagged in production
CGX_COMMIT_IN_PROD=$(git show-ref -s in_prod)


# Get modified from current master commit and latest in_prod commit.
MODIFIED_CONFIGS=$(git diff "${CGX_COMMIT_IN_PROD}" "${TRAVIS_COMMIT}" --diff-filter=ACMR --name-status | cut -f2 \
                   | grep 'configurations\/.*\.yml')

# execute the changes
echo "PROD_TO_CURRENT: ${CGX_COMMIT_IN_PROD}...${TRAVIS_COMMIT}"
echo "MODIFIED_CONFIGS: ${MODIFIED_CONFIGS}"
for SITE_CONFIG in ${MODIFIED_CONFIGS}
  do
    echo "${SITE_CONFIG}" > "log/$(basename "${SITE_CONFIG}")" 2>&1
  done

# push logs to master
git add logs/*
git commit -m 'Build Log Results [ci skip]'
git push -f origin master:logs

# delete current in_prod tag
git tag -d in_prod
git push origin :refs/tags/in_prod

# add new in_prod tag to current build
git tag in_prod
git push origin refs/tags/in_prod
