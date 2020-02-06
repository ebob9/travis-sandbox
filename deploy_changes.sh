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
# GITHUB_REPO_TOKEN = Valid personal token that has Repository access to commit.
# TRAVIS_COMMIT = Current commit hash

# Color constants
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
NC='\033[0m'

EXIT_CODE=0

# Indent and pretty-fi function
indent() { sed 's/^/    /'; }

# Debug script (if needed)
#set -x

# Set up git for log commit back to master.
echo -e "${WHITE}Setting GIT authentication/origin..${NC}"
git config --global user.email "travisci-worker-ebob9@travis-ci.org" 2>&1 2>&1 | indent
git config --global user.name "travisci-worker-ebob9" 2>&1 | indent

# Remove existing "origin"
git remote rm origin 2>&1 | indent
# Add new "origin" with access token in the git URL for authentication
git remote add origin "https://travisci-worker-ebob9:${GITHUB_REPO_TOKEN}@github.com/ebob9/travis-sandbox.git" > /dev/null 2>&1

## DEBUG - find out why things arent working
#git remote get-url --all origin
#git show-ref -s in_prod

# Get latest commit tagged in production
CGX_COMMIT_IN_PROD=$(git show-ref -s in_prod)
echo -e "${WHITE}Latest 'in_prod' commit:${NC} ${CGX_COMMIT_IN_PROD}"

# Set IFS to LF to handle spaces.
IFS=$'\n'

# Get modified from current master commit and latest in_prod commit.
MODIFIED_CONFIGS=$(git diff "${CGX_COMMIT_IN_PROD}" "${TRAVIS_COMMIT}" --diff-filter=ACMR --name-status | cut -f2 \
                   | grep 'configurations\/.*\.yml')

# execute the changes
echo -e "${WHITE}Commit diff check range:${NC} ${CGX_COMMIT_IN_PROD}...${TRAVIS_COMMIT}"
echo -e "${WHITE}Configuration Files Added or Modified:${NC}"
echo "${MODIFIED_CONFIGS}" 2>&1 | indent

# create tmp logs
mkdir /tmp/logs

for SITE_CONFIG in ${MODIFIED_CONFIGS}
  do
    SITE_CONFIG_FILE=$(basename "${SITE_CONFIG}")
    echo -e -n "${WHITE}Executing ${SITE_CONFIG_FILE} Configuration: ${NC}"
    if echo "${SITE_CONFIG}-$RANDOM" > "/tmp/logs/${SITE_CONFIG_FILE}.log" 2>&1
      then
        echo -e "${GREEN}Success. ${NC}"
      else
        echo -e "${RED}Failed, code $?. ${NC}"
        EXIT_CODE=1
    fi
  done

# delete current in_prod tag
echo -e "${WHITE}Updating 'in_prod' tag in Github..${NC}"
git tag -d in_prod 2>&1 | indent
git push origin :refs/tags/in_prod 2>&1 | indent

# add new in_prod tag to current build
git tag in_prod 2>&1 | indent
git push origin refs/tags/in_prod 2>&1 | indent


# switch to logs
echo -e "${WHITE}Preping to save logs and screenshots to origin/results.. ${NC}"
git checkout -b results 2>&1 | indent
git fetch --all 2>&1 | indent
git branch -u origin/results 2>&1 | indent
git reset --hard origin/results 2>&1 | indent

# merge (w/overwrite) master to logs.
git pull --no-commit -X theirs origin master 2>&1 | indent

# copy logs to logs directory
echo -e "${WHITE}Updating logs/ with new logs..${NC}"
cp -a /tmp/logs/* logs/ 2>&1 | indent

# create screenshots of all new items.
for SITE_CONFIG in ${MODIFIED_CONFIGS}
  do
    echo "${WHITE}Taking Screenshots of objects in ${SITE_CONFIG}.. ${NC}"
    if python3 ./screenshot.py "${SITE_CONFIG}"
      then
        echo -e "${GREEN}Success. ${NC}"
      else
        echo -e "${RED}Failed, code $?. ${NC}"
        EXIT_CODE=1
    fi
  done

# create index of site screenshots.
echo -e "${WHITE}Creating Screenshot index README.md${NC}"
cd screenshots || { echo -e "${RED}Could not cd to screenshots. Exiting.${NC}"; exit 1; }
{
  echo "## Updated CloudGenix Topology from commit ${TRAVIS_COMMIT}:"
  echo '<img alt="Map Image" src="map.png" width="1110">'
  echo ''
  echo "### Updated Sites in commit ${TRAVIS_COMMIT}:"
  echo '<ul>'
} > README.md

# iterate directories.
for DIRECTORY in $(ls -d */ | cut -f1 -d'/')
  do
    {
     echo '<li>'
     echo "<A href=\"${DIRECTORY}/README.md\">${DIRECTORY}</A>"
     echo '<\li>'
    } >> README.md
  done
echo '<\ul>' >> README.md

# push logs and screenshots to results repository
git add -A logs/* 2>&1 | indent
git add -A screenshots/* 2>&1 | indent
git commit -m 'Configuration Log and Screenshot Results [ci skip]' 2>&1 | indent
git push origin results 2>&1 | indent

## Debug push items
#git log --full-history
#git reflog
#git remote -v

if [ ${EXIT_CODE} == 0 ]
  then
    echo "${GREEN}Finished! (Success)${NC}"
  else
    echo "${RED}Finished! (Failed)${NC}"
fi
exit ${EXIT_CODE}


