import os
import time
import zipfile
import pandas as pd
from mnemonic import Mnemonic
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


PASSWORD = "password"
MNEMO = Mnemonic("english")
MAIN_ETH_ADDRESS = "0xDc65e20C2e6399Ad90738fe7eb47B26DD4DBbC5F"

PROXY_HOST = '45.140.13.119'  # rotating proxy
PROXY_PORT = 9132
PROXY_USER = 'user'
PROXY_PASS = 'pass'


def load_proxy():
    # Proxy in form IP:PORT:USER:PASS
    proxy_dict = {}
    dir_path = os.path.dirname(os.path.realpath(__file__))
    try:
        with open(dir_path + '/proxy.txt') as f:
            try:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    line_split = line.split(":")
                    proxy_dict[i] = [x.strip() for x in line_split]
            except Exception as e:
                pass
    except Exception:
        print("File proxy.txt doesn't exist!")
    return proxy_dict

def crete_selenium_driver(use_proxy=False):
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = """
    var config = {
            mode: "fixed_servers",
            rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
            },
            bypassList: ["localhost"]
            }
        };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {urls: ["<all_urls>"]},
                ['blocking']
    );
    """ % (PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS)

    chrome_options = Options()
    chrome_options.add_extension('metamask.crx')
    prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ['enable-automation'])
    chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36")
    chrome_options.add_argument('--disable-gpu')
    #chrome_options.add_argument('--headless')
    if use_proxy:
        pluginfile = 'proxy_auth_plugin.zip'
        with zipfile.ZipFile(pluginfile, 'w') as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", background_js)
        chrome_options.add_extension(pluginfile)
    
    driver = webdriver.Chrome(options=chrome_options)
    main_window = driver.current_window_handle
    driver.switch_to.window(driver.window_handles[1])
    return driver

def metamask_seed_balance(seed):
    try:
        ##########  ETH  ##########

        driver = crete_selenium_driver(use_proxy=False)
        driver.get('chrome-extension://nkbihfbeogaeaoehlefnkodbefgpgknn/home.html#initialize/create-password/import-with-seed-phrase')

        el = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "MuiInputBase-input")))
        el.send_keys(seed)

        elp1 = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "password")))
        elp1.send_keys(PASSWORD)

        elp2 = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "confirm-password")))
        elp2.send_keys(PASSWORD)

        check_mark = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "first-time-flow__terms")))
        check_mark.click()

        import_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "first-time-flow__button")))
        import_button.click()

        done_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'All Done')]")))
        done_button.click()

        network_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "chip__right-icon")))
        network_button.click()

        rinkeby_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Rinkeby Test Network']")))
        rinkeby_button.click()

        copy_address = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "selected-account__address")))
        copy_address.click()

        eth_address = str(pd.read_clipboard().iloc[:, 0]).split(":")[1].split(",")[0].strip()
        print("ETH address: {}".format(eth_address))


        driver_proxy = crete_selenium_driver(use_proxy=False)
        driver_proxy.get('https://rinkebyfaucet.com/')

        eth_address_input = WebDriverWait(driver_proxy, 20).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div/div[1]/div[2]/div[2]/div[2]/div/span/div[1]/div[1]/input')))
        eth_address_input.send_keys(eth_address)

        send_button = WebDriverWait(driver_proxy, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "alchemy-faucet-table-body")))
        send_button.click()

        time.sleep(1)
        
        driver_proxy.close()
        driver_proxy.quit()


        balance = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "currency-display-component__text"))).text
        print("ETH balance: {}".format(balance))

        if balance == "0":
            print("Waiting for coins...")
        while balance == "0":
            balance = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "currency-display-component__text"))).text
            print("ETH balance recheck: {}".format(balance))
            time.sleep(5)

        if balance != "0":
            print("Sending coins...")
            send_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div/div[4]/div/div/div/div[2]/div/div[2]/button[2]/div')))
            send_button.click()

            input_rec_address = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div/div[4]/div/div[2]/div/input")))
            input_rec_address.send_keys(MAIN_ETH_ADDRESS)

            max_amount_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div/div[3]/div/div[3]/div/div[3]/div[1]/button/div')))
            max_amount_button.click()


        ##########  ETH  ##########

        time.sleep(9999)

        driver.close()
        driver.quit()
    except Exception as e:
        print("Selenium Exception {}".format(e))
        driver.close()
        driver.quit()
        driver_proxy.close()
        driver_proxy.quit()
        """ os.system('killall -9 chrome')
        os.system('killall -9 chromium') """


if __name__ == "__main__":
    while True:
        proxy_list = load_proxy()
        words = MNEMO.generate(strength=128)  # 128 bit for 12 word seed
        for i, (k,v) in enumerate(proxy_list.items()):
            #print("**************************** proxy_list  ***************************")
            PROXY_HOST = v[0]
            #print("Proxy: {}".format(PROXY_HOST))
            PROXY_PORT = v[1]
            #print("Port: {}".format(PROXY_PORT))
            PROXY_USER = v[2]
            #print("User: {}".format(PROXY_USER))
            PROXY_PASS = v[3]
            #print("Pass: {}".format(PROXY_PASS))
            #print("**************************** proxy_list  ***************************")
        metamask_seed_balance(words)
