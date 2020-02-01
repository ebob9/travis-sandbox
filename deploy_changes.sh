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

EXIT_CODE=0

# Debug script (if needed)
#set -x

# Set up git for log commit back to master.
echo "Setting GIT authentication/origin.."
git config --global user.email "travisci-worker-ebob9@travis-ci.org"
git config --global user.name "travisci-worker-ebob9"

# Remove existing "origin"
git remote rm origin
# Add new "origin" with access token in the git URL for authentication
git remote add origin "https://travisci-worker-ebob9:${GITHUB_REPO_TOKEN}@github.com/ebob9/travis-sandbox.git" > /dev/null 2>&1

## DEBUG - find out why things arent working
#git remote get-url --all origin
#git show-ref -s in_prod

# Get latest commit tagged in production
CGX_COMMIT_IN_PROD=$(git show-ref -s in_prod)
echo "Latest 'in_prod' commit: ${CGX_COMMIT_IN_PROD}"

# Get modified from current master commit and latest in_prod commit.
MODIFIED_CONFIGS=$(git diff "${CGX_COMMIT_IN_PROD}" "${TRAVIS_COMMIT}" --diff-filter=ACMR --name-status | cut -f2 \
                   | grep 'configurations\/.*\.yml')

# execute the changes
echo "Commit diff check range: ${CGX_COMMIT_IN_PROD}...${TRAVIS_COMMIT}"
echo "Configuration Files Modified: ${MODIFIED_CONFIGS}"

# create tmp logs
mkdir /tmp/logs

for SITE_CONFIG in ${MODIFIED_CONFIGS}
  do
    SITE_CONFIG_FILE=$(basename "${SITE_CONFIG}")
    echo -n "Executing ${SITE_CONFIG_FILE} Configuration: "
    if echo "${SITE_CONFIG}-$RANDOM" > "/tmp/logs/${SITE_CONFIG_FILE}.log" 2>&1
      then
        echo "Success. "
      else
        echo "Failed, code $?. "
        EXIT_CODE=1
    fi
  done

# delete current in_prod tag
echo "Updating 'in_prod' tag in Github.."
git tag -d in_prod
git push origin :refs/tags/in_prod

# add new in_prod tag to current build
git tag in_prod
git push origin refs/tags/in_prod


# switch to logs
echo "Saving logs to origin/logs.."
git checkout -b logs
git fetch --all
git branch -u origin/logs
git reset --hard origin/logs

# merge (w/overwrite) master to logs.
git pull --no-commit -X theirs origin master

# copy logs to logs directory
cp -a /tmp/logs/* logs/

# push logs to logs repository
git add logs/*
git commit -m 'Configuration Log Results [ci skip]'
git push origin logs

## Debug push items
#git log --full-history
#git reflog
#git remote -v

echo "Finished!"
exit ${EXIT_CODE}


