import json
import requests
import os
import argparse
import logging

# Setup logger
logger = logging.getLogger('smoke-test')
file_handler = logging.FileHandler('smoke-test.log')
console_hanlder = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_hanlder)
logger.setLevel(logging.INFO)


# Get the json file if no json file throws error
def get_json(tests):
    data = tests + ".json"
    try:
        with open(data) as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.info("File not found")
    return data


# Get the access token
def get_access_token():

    # Get the api info from the context in CircleCI
    URL = os.getenv('URL')
    EMAIL = os.getenv('EMAIL')
    PASSWORD = os.getenv('PASSWORD')
    AUTHORIZATION = os.getenv('AUTHORIZATION')

    payload = {
        "email": EMAIL,
        "password": PASSWORD
    }
    headers = {
        'authorization': AUTHORIZATION,
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", URL, headers=headers, data=payload)

    logger.info('Login status code:' + str(response.status_code))
    logger.info('Login body:' + str(response.content))
    if response.status_code == 200:
        logger.info('*** Logged in...')
    else:
        logger.info('*** Login failed...Please try again')
        raise Exception("Login failed...Please try again")
    access_token = 'Bearer ' + response.json()['access_token']

    return access_token


# Test
def test_all_methods(env, fail_on_first, tests):

    logger.info("Smoke test starts!")
    # Read json file in the root directory
    data = get_json(tests=tests)

    # Get all the endpoints
    endpoints = data["endpoints"][env]
    # Get access_token
    access_token = get_access_token()

    # Test
    errors = []

    for endpoint in endpoints:
        # header
        headers = {'authorization': access_token}
        # GET
        if (endpoint["type"] == "get"):
            response = requests.get(
                endpoint["url"], headers=headers, data={})
            check_status_code(type=endpoint["type"].upper(
            ), response=response, endpoint=endpoint, errors=errors, fail_on_first=fail_on_first)
        # PATCH
        elif (endpoint["type"] == "patch"):
            response = requests.patch(
                endpoint["url"], headers=headers, data={})
            check_status_code(type=endpoint["type"].upper(
            ), response=response, endpoint=endpoint, errors=errors, fail_on_first=fail_on_first)
        # POST
        elif (endpoint["type"] == "post"):
            response = requests.post(
                endpoint["url"], headers=headers, data=endpoint["body"])
            check_status_code(type=endpoint["type"].upper(
            ), response=response, endpoint=endpoint, errors=errors, fail_on_first=fail_on_first)

    # Show the result
    if (len(errors) == 0):
        logger.info("Everything pass!!")
    else:
        logger.info("Here are the tests ")
        for error in errors:
            logger.info(error)
        raise Exception("Test fail! Rollback is triggered automatically!")
    logger.info("Test success!")


# Check status code
def check_status_code(type, response, endpoint, errors, fail_on_first):
    if fail_on_first:
        assert response.status_code == endpoint["expectedResultCode"]
    else:
        try:
            assert response.status_code == endpoint["expectedResultCode"]
        except AssertionError:
            errors.append("%s method: %s (Expected status code is %s but got %s). " % (type, endpoint["url"], endpoint["expectedResultCode"], response.status_code))


# API call
def trigger_rollback():
    # Get the approval_request_id
    workflow_id = os.getenv('CIRCLE_WORKFLOW_ID')
    url = "https://circleci.com/api/v2/workflow/" + workflow_id + "/job"

    payload = "{}"
    headers = {
        'authorization': 'Basic OWUzNWI1YzdiODRkNGI0ODkxNmRhYTM1OGJhNGNhNjUwMmM5NGUzNjo=',
        'Content-Type': 'application/json',
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    logger.info(response.text)
    approval_request_id = response.json()["items"][1]["approval_request_id"]
    logger.info(approval_request_id)

    # Approve the rollback if smoke test fail.
    url = "https://circleci.com/api/v2/workflow/" + \
        workflow_id + "/approve/" + approval_request_id
    logger.info(url)
    response = requests.request("POST", url, headers=headers, data=payload)
    logger.info(response.text)


# __name__
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--function', help="do smoke test or trigger rollback", required=True)
    parser.add_argument('-t', '--flag', help="true for fail on first otherwise false", required=True)
    parser.add_argument('-e', '--env', help="specify the test env (stg or prd)", required=True)
    parser.add_argument('-n', '--name', help="json file name", required=True)

    io_args = parser.parse_args()

    do_func = io_args.function
    flag = io_args.flag
    env = io_args.env   
    tests = io_args.name

    if do_func == "test":
        test_all_methods(env=env, fail_on_first=flag, tests=tests)
    elif do_func == "rollback":
        trigger_rollback()
    else:
        logger.info("No function to run", do_func)
