#!/usr/bin/env python3
"""
Script to log into the CloudGenix Controller UI and take screenshots.
Leverages Selenium-wire, headless Chrome, and CloudGenix SDK.
Also uses cloudgenix_config files as the data source.
"""
import sys
import os
import time
import yaml
import pathlib
import cloudgenix
from cloudgenix_config import config_lower_version_get
from seleniumwire import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

# Get CGX auth_token
if "AUTH_TOKEN" in os.environ:
    CLOUDGENIX_AUTH_TOKEN = os.environ.get('AUTH_TOKEN')
else:
    # no AUTH_TOKEN
    print("ERROR: No AUTH_TOKEN available for screenshots. Exiting.")
    sys.exit(1)

# Globals
UI_TOPOLOGY_PAGE = 'https://portal.{0}.cloudgenix.com/#map'
UI_SITE_PAGE = 'https://portal.{0}.cloudgenix.com/#map/site/{1}'
UI_ELEMENT_BASIC = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/basic_info'
UI_ELEMENT_TOOLKIT = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/device_toolkit'
UI_ELEMENT_INTERFACES = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/interfaces'
UI_ELEMENT_BGPPEERS = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/routing/bgp:peers'
UI_ELEMENT_BGPROUTEMAPS = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/routing/bgp:route_maps'
UI_ELEMENT_BGPPREFIXLISTS = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/routing/bgp:prefix_lists'
UI_ELEMENT_BGPASPATHACL = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/routing/bgp:as_path_lists'
UI_ELEMENT_BGPIPCOMMUNITYLISTS = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/routing/bgp:ip_community_lists'
UI_ELEMENT_STATICROUTES = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/routing/static_routes'
UI_ELEMENT_SNMP = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/snmp'
UI_ELEMENT_SYSLOG = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/syslog_export'
UI_ELEMENT_NTP = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/ntp_client'
UI_INTERFACES_DETAIL = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/interfaces/{2}'

XPATH_INTERFACE_ADVANCED_OPTIONS = "/html/body/div[1]/section/div/div[2]/div/div/div[2]/div/div/div[3]/div/div/form/" \
                                   "div[2]/div/div/div[1]/a"
XPATH_CLOSE_WHATS_NEW = "/html/body/div[1]/div[4]/div/div/img"

FILENAME_VALID_CHARS = '-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'


def sanitize_filename(file_name):
    """
    Make sure a filename is only valid filename chars
    :param file_name: String to check
    :return: safer filename string
    """
    return ''.join(char for char in file_name if char in FILENAME_VALID_CHARS)


def is_int(val):
    """
    Check if value is able to be cast to int.
    :param val: String to be tested to int
    :return: Boolean, True if success
    """
    try:
        num = int(val)
    except ValueError:
        return False
    return True


def screenshot_page(page_uri, sel_driver, output_filename, waitfor="time", waitfor_value="30", click_xpath=None,
                    load_wait=20, load_tweak_delay=2):
    """
    Load and save a screnshot from the CGX UI
    :param page_uri: URI of page to get
    :param sel_driver: seleniumwire webdriver instance
    :param output_filename: Filename to save
    :param waitfor: Can be int (raw time), or id or class
    :param waitfor_value: ID or Class Name to wait for, if waitfor set to class or ID
    :param click_xpath
    :param load_wait: Default time for waitfor object to load.
    :param load_tweak_delay:
    :return:
    """

    try:
        # Get page
        sel_driver.get(page_uri)
        # wait static or for id or class
        if isinstance(waitfor, str):
            if waitfor.lower() == 'class':
                _ = WebDriverWait(sel_driver, load_wait).until(
                    EC.presence_of_element_located((By.CLASS_NAME, waitfor_value)))
            elif waitfor.lower() == 'id':
                _ = WebDriverWait(sel_driver, load_wait).until(EC.presence_of_element_located((By.ID, waitfor_value)))
            elif waitfor.lower() == 'time':
                # check if can be cast to int:
                if is_int(waitfor_value):
                    # hard wait
                    time.sleep(int(waitfor_value))

            else:
                # invalid wait, just go
                pass

    except TimeoutException:
        print("WARNING: Loading Page {0}, waiting for {1} '{2}' took longer than {3} seconds. Saving data that exists."
              "".format(page_uri, waitfor, waitfor_value, load_wait))

    if click_xpath is not None:
        # need to click on something quickly.
        click_dom = driver.find_elements_by_xpath(click_xpath)[0]
        click_dom.click()

    # Tweak delay
    time.sleep(load_tweak_delay)
    driver.get_screenshot_as_file(output_filename)

    return


# quick check we have 1 argument.
if len(sys.argv) != 2:
    print("ERROR: This script takes exactly 1 command line argument. Got the following: ")
    for arg in sys.argv:
        print(arg)
    sys.exit(1)

# just one argument, it hopefully is the config file.
config_file = sys.argv[1]

# Try open config file, get list of site names, element names
try:
    with open(config_file, 'r') as datafile:
        loaded_config = yaml.safe_load(datafile)
except IOError as e:
    print("ERROR: Could not open file {0}: {1}".format(config_file, e))
    sys.exit(1)

# let user know it worked.
print("    Loaded Config File {0}.".format(config_file))

# create a site name-> ID dict and element name->ID dict.
sdk = cloudgenix.API()
sdk.interactive.use_token(CLOUDGENIX_AUTH_TOKEN)
region = sdk.controller_region
sites_n2id = sdk.build_lookup_dict(sdk.extract_items(sdk.get.sites()))
elements_n2id = sdk.build_lookup_dict(sdk.extract_items(sdk.get.elements()))


sites_dict = {}
config_sites, sites_api_version = config_lower_version_get(loaded_config, "sites", sdk.get.sites)
for site, config_site_cnf in config_sites.items():
    # get the list of element names
    elements_list = []
    config_elements, elements_api_version = config_lower_version_get(config_site_cnf, "elements", sdk.get.elements)
    for element, config_element_cnf in config_elements.items():
        elements_list.append(element)
    # update the sites dict with the site/element(s)
    sites_dict[site] = elements_list


# Create a new instance of the Chrome driver
# Headless mode of Chrome, ChromeDriver, and Selenium
options = webdriver.ChromeOptions()
options.add_argument('headless')
# long window, lots of room
options.add_argument('window-size=1920x1080')
driver = webdriver.Chrome(chrome_options=options)

# Interactive launch of the above, for debugging.
# driver = webdriver.Chrome()

# wait for 30 secs for all operations.
driver.implicitly_wait(30)
# default dom wait timer
delay = 20  # seconds
# default post dom wait timer
tweak_delay = 2  # seconds

# Set the request header using the `header_overrides` attribute
driver.header_overrides = {
    'X-Auth-Token': CLOUDGENIX_AUTH_TOKEN,
}

# Get map page to process and cache login
print("    Logging in and taking topology screenshot: ", end="")
uri = UI_TOPOLOGY_PAGE.format(region)
filename = "screenshots/map.png"
# add a bit for tweak delay as tiles may take a while to load.
screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='leaflet-map-pane',
                click_xpath=XPATH_CLOSE_WHATS_NEW, load_tweak_delay=8)
print("Done")


# start getting sites, elements, interfaces
for site_name, elements_list in sites_dict.items():
    site_id = sites_n2id.get(site_name)
    if site_id is None:
        # something wrong with this site. Print and continue.
        print("WARNING: Could not get Site ID for Site {0}, skipping..".format(site_name))
        continue
    site_filesafer_name = sanitize_filename(site_name)
    site_directory = "screenshots/{0}/".format(site_filesafer_name)
    # make a directory
    pathlib.Path(site_directory).mkdir(parents=True, exist_ok=True)

    # Get SITE page
    print("    Taking Screenshot of Site '{0}' Site Map Card: ".format(site_name), end="")
    uri = UI_SITE_PAGE.format(region, site_id)
    filename = site_directory + "{0}.site-info.png".format(site_name)
    screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='site-info')
    print("Done")

    for element_name in elements_list:
        element_id = elements_n2id.get(element_name)
        if element_id is None:
            # something wrong with this element. Print and continue.
            print("WARNING: Could not get Element ID for Element {0}, skipping..".format(element_name))
            continue
        element_filesafer_name = sanitize_filename(element_name)
        element_directory = site_directory + "{0}/".format(element_filesafer_name)
        pathlib.Path(element_directory).mkdir(parents=True, exist_ok=True)
        # Get ELEMENT pages.
        # Note, static/bgp pages can get stuck, if we navigate to any other page after, it works fine.

        # Static Routes
        print("      Taking Screenshot of Element '{0}' Static Routes: ".format(element_name), end="")
        uri = UI_ELEMENT_STATICROUTES.format(region, element_id)
        filename = element_directory + "static_routes.png"
        # first element item can take a bit while modal/backend stuff is cached. wait longer. Not needed mostly.
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='static-routing-table', load_wait=60)
        print("Done")

        # Basic config
        print("      Taking Screenshot of Element '{0}' Basic Config: ".format(element_name), end="")
        uri = UI_ELEMENT_BASIC.format(region, element_id)
        filename = element_directory + "basic_info.png"
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='form-group')
        print("Done")

        # BGP Peers table
        print("      Taking Screenshot of Element '{0}' BGP Peers: ".format(element_name), end="")
        uri = UI_ELEMENT_BGPPEERS.format(region, element_id)
        filename = element_directory + "bgp_peers.png".format(site_name, element_name)
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='bgpPeersTable')
        print("Done")

        # Device toolkit
        print("      Taking Screenshot of Element '{0}' Device Toolkit: ".format(element_name), end="")
        uri = UI_ELEMENT_TOOLKIT.format(region, element_id)
        filename = element_directory + "device_toolkit.png".format(site_name, element_name)
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='form-group')
        print("Done")

        # BGP Route Maps
        print("      Taking Screenshot of Element '{0}' BGP Route Maps: ".format(element_name), end="")
        uri = UI_ELEMENT_BGPROUTEMAPS.format(region, element_id)
        filename = element_directory + "bgp_route_maps.png"
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='routeMapsTable')
        print("Done")

        # Interfaces summary
        print("      Taking Screenshot of Element '{0}' Interfaces Summary: ".format(element_name), end="")
        uri = UI_ELEMENT_INTERFACES.format(region, element_id)
        filename = element_directory + "interfaces_summary.png"
        # bump window size up for Interfaces screen.
        driver.set_window_size(1920, 2160)
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='interface_name-wrapper')
        # Set size back..
        driver.set_window_size(1920, 1080)
        print("Done")

        # BGP Prefixlists
        print("      Taking Screenshot of Element '{0}' BGP Prefix Lists: ".format(element_name), end="")
        uri = UI_ELEMENT_BGPPREFIXLISTS.format(region, element_id)
        filename = element_directory + "bgp_prefix_lists.png"
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='prefixListsTable')
        print("Done")

        # SNMP
        uri = UI_ELEMENT_SNMP.format(region, element_id)
        print("      Taking Screenshot of Element '{0}' SNMP: ".format(element_name), end="")
        filename = element_directory + "snmp.png".format(site_name, element_name)
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='snmpAgentView')
        print("Done")

        # BGP ASPATH ACL
        print("      Taking Screenshot of Element '{0}' BGP AS-PATH Access Lists: ".format(element_name), end="")
        uri = UI_ELEMENT_BGPASPATHACL.format(region, element_id)
        filename = element_directory + "bgp_aspath_acl.png"
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='asPathListsTable')
        print("Done")

        # SYSLOG
        print("      Taking Screenshot of Element '{0}' SYSLOG:  ".format(element_name), end="")
        uri = UI_ELEMENT_SYSLOG.format(region, element_id)
        filename = element_directory + "syslog.png"
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='syslog-export-table')
        print("Done")

        # BGP IP COMMUNITY Lists
        print("      Taking Screenshot of Element '{0}' BGP IP Community Lists: ".format(element_name), end="")
        uri = UI_ELEMENT_BGPIPCOMMUNITYLISTS.format(region, element_id)
        filename = element_directory + "bgp_ip_community_lists.png"
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='ipCommunityListsTable')
        print("Done")

        # NTP
        print("      Taking Screenshot of Element '{0}' NTP: ".format(element_name), end="")
        uri = UI_ELEMENT_NTP.format(region, element_id)
        filename = element_directory + "ntp.png"
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='ntp-servers-table')
        print("Done")

        # get some interface screenshots.
        interfaces_cache = sdk.extract_items(sdk.get.interfaces(site_id, element_id))
        if len(interfaces_cache) >= 1:
            # create interfaces directory, lets get some interface info.
            interface_directory = element_directory + "{0}/".format("interfaces")
            pathlib.Path(interface_directory).mkdir(parents=True, exist_ok=True)

            # bump window size up for Interfaces screen.
            driver.set_window_size(1920, 2160)

            for interface_record in interfaces_cache:
                interface_id = interface_record.get('id')
                interface_name = interface_record.get('name')
                interface_filesafer_name = sanitize_filename(interface_name)

                # interface get!
                print("        Taking Screenshot of Interface '{0}' Configuration: ".format(interface_name), end="")
                uri = UI_INTERFACES_DETAIL.format(region, element_id, interface_id)
                filename = interface_directory + "{0}.png".format(interface_filesafer_name)
                screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='port_config_form_nav',
                                click_xpath=XPATH_INTERFACE_ADVANCED_OPTIONS)
                print("Done")

            # Set window size back..
            driver.set_window_size(1920, 1080)

driver.close()
