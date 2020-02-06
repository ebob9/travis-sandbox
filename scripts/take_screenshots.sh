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

# create screenshots of all new items.
for SITE_CONFIG in ${MODIFIED_CONFIGS}
  do
    echo -e "${WHITE}Taking Screenshots of objects in ${SITE_CONFIG}.. ${NC}"
    if python3 ./scripts/screenshot.py "${SITE_CONFIG}"
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
  echo "## Updated CloudGenix Topology ($(date))"
  echo "from commit:${TRAVIS_COMMIT} "
  echo '<img alt="Map Image" src="map.png?raw=1" width="1110">'
  echo ''
  echo "### All Sites (updated in this commit and previous commits):"
  echo ""
  echo '<ul>'
} > README.md

# iterate directories.
for DIRECTORY in $(ls -d */ | cut -f1 -d'/')
  do
    echo "<li><A href=\"${DIRECTORY}/README.md\">${DIRECTORY}</A>" >> README.md
  done
echo '' >> README.md

# return back to parent directory
cd .. || { echo -e "${RED}Could not cd to parent directory. Exiting.${NC}"; exit 1; }

if [ ${EXIT_CODE} == 0 ]
  then
    echo -e "${GREEN}Finished! (Success)${NC}"
  else
    echo -e "${RED}Finished! (Failed)${NC}"
fi
exit ${EXIT_CODE}


