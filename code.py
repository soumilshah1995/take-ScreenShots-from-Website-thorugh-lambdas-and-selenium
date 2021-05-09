try:
    import json
    from selenium.webdriver import Chrome
    from selenium.webdriver.chrome.options import Options
    import os
    import shutil
    import uuid
    import boto3
    from datetime import datetime
    import datetime

    print("All Modules are ok ...")

except Exception as e:

    print("Error in Imports ")


# ------------------------------------Settings ---------------------------------------
global AWS_ACCESS_KEY
global AWS_SECRET_KEY
global AWS_REGION_NAME
global BUCKET
global URL
global DESTINATION

AWS_ACCESS_KEY = "XXX"
AWS_SECRET_KEY ="XXX"
AWS_REGION_NAME = "us-east-1"
BUCKET = "XXX"

# ---------------------------------------------------------------------------------------


class SchemaValidator(object):

    def __init__(self, response):
        self.response = response

    def isTrue(self):

        errorMessages = []


        try:
            url = self.response.get("url")
            if url is None:
                raise Exception ("Please pass valid url ")
        except Exception as e:errorMessages.append("Please pass valid url ")

        try:
            destinationPath = self.response.get("destinationPath")

            if destinationPath is None:
                raise Exception ("Please pass valid destinationPath  ")
        except Exception as e:errorMessages.append("Please pass valid destinationPath ")

        return errorMessages


class WebDriver(object):

    def __init__(self):
        self.options = Options()

        self.options.binary_location = '/opt/headless-chromium'
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--start-maximized')
        self.options.add_argument('--start-fullscreen')
        self.options.add_argument('--single-process')
        self.options.add_argument('--disable-dev-shm-usage')

    def get(self):
        driver = Chrome('/opt/chromedriver', options=self.options)
        return driver


class WebDriverScreenshot:

    def __init__(self):

        self._tmp_folder = '/tmp/{}'.format(uuid.uuid4())

        if not os.path.exists(self._tmp_folder):
            os.makedirs(self._tmp_folder)

        if not os.path.exists(self._tmp_folder + '/user-data'):
            os.makedirs(self._tmp_folder + '/user-data')

        if not os.path.exists(self._tmp_folder + '/data-path'):
            os.makedirs(self._tmp_folder + '/data-path')

        if not os.path.exists(self._tmp_folder + '/cache-dir'):
            os.makedirs(self._tmp_folder + '/cache-dir')

    def __get_correct_height(self, url, width=1280):

        driverHelper = WebDriver()
        driver = driverHelper.get()
        driver.get(url)

        height = driver.execute_script("return Math.max( document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight )")
        driver.quit()

        return height

    def save_screenshot(self, url, filename, width=1280, height=None):

        if height == None:
            height = self.__get_correct_height(url, width=width)

        driverHelper = WebDriver()
        driver = driverHelper.get()
        driver.get(url)

        driver.save_screenshot(filename)
        driver.quit()

    def close(self):
        # Remove specific tmp dir of this "run"
        shutil.rmtree(self._tmp_folder)

        # Remove possible core dumps
        folder = '/tmp'

        for the_file in os.listdir(folder):

            file_path = os.path.join(folder, the_file)

            try:
                if 'core.headless-chromi' in file_path and os.path.exists(file_path) and os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(e)


def lambda_handler(event, context):

    try:
        body = json.loads(event.get("body"))

        _instance = SchemaValidator(response=body)
        response = _instance.isTrue()

        if len(response) != 0:
            _response = {
                            "Error":"Please Correct following issue in Json format",
                            "message":response
                        },403
            return _response
        else:

            URL = body.get("url")
            destinationPath = body.get("destinationPath")

            screenshot_file = "{}-{}".format(''.join(filter(str.isalpha, URL)), str(uuid.uuid4()))

            # ===========================Crawling ===========================
            driver = WebDriverScreenshot()
            driver.save_screenshot(url=URL, filename='/tmp/{}-fixed.png'.format(screenshot_file), height=1024)

            driver.save_screenshot(URL, '/tmp/{}-full.png'.format(screenshot_file))
            driver.close()
            #=================================================================================


            # ===================================AWS S3 ==============================
            s3 = boto3.client("s3",aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY,region_name=AWS_REGION_NAME)
            s3.upload_file('/tmp/{}-fixed.png'.format(screenshot_file),BUCKET, '{}/{}-fixed.png'.format(destinationPath, screenshot_file))
            s3.upload_file('/tmp/{}-full.png'.format(screenshot_file), BUCKET,'{}/{}-full.png'.format(destinationPath, screenshot_file))

            return True

    except Exception as e:
        print("Error : {} ".format(e))
        return False