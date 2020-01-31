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

# Get latest commit tagged in production
CGX_COMMIT_IN_PROD=$(git show-ref -s in_prod)


# Get modified from current master commit and latest in_prod commit.
MODIFIED_CONFIGS=$(git diff "${CGX_COMMIT_IN_PROD}" "${TRAVIS_COMMIT}" --diff-filter=ACMR --name-status | cut -f2 \
                   | grep '\.yml$')

# execute the changes
echo "PROD_TO_CURRENT: ${CGX_COMMIT_IN_PROD}...${TRAVIS_COMMIT}"
echo "MODIFIED_CONFIGS: ${MODIFIED_CONFIGS}"
for SITE_CONFIG in ${MODIFIED_CONFIGS}
  do
    echo "${SITE_CONFIG}" > log/$(basename "${SITE_CONFIG}")
  done

# push logs to master
git add logs/*
git commit -m 'Build Log Results [ci skip]'
git push origin master

# delete current in_prod tag
git tag -d in_prod
git push origin :refs/tags/in_prod

# add new in_prod tag to current build
git tag in_prod
git push origin refs/tags/in_prod
