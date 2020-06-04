import json
import os

import requests


class BitlyBasicAuthClient(object):
    def __init__(self, username=os.environ.get('USERNAME'), password=os.environ.get('PASSWORD')):
        """
        Initialize BitlyBasicAuthClient with required auth credentials
        :param username: Bitly username, this value should not be hardcoded
        :type username:
        :param password: Bitly password, this value should not be hardcoded
        :type password:
        """
        attr_errors = []
        if not username:
            attr_errors.append({'username': 'Bitly api auth username required field'})
        if not password:
            attr_errors.append({'password': 'Bitly api auth password required field'})
        if attr_errors:
            raise ValueError(attr_errors)
        self.__bitly_api_username = username
        self.__bitly_api_password = password
        self.__bitly_api_base_url = 'https://api-ssl.bitly.com'
        self.__api_token = self.__auth_token()

    def __auth_token(self):
        """
        A POST request is made to /oauth/access_token with username, password, set to the Authorization header in exchange for an access token
        NOTE: You should only make this call once and store the returned token securely. as token never expires,
        You may want to enhance this function so that it caches token, and check for token invalidation in the event
        token is invalidated by the bitly account admin responsible for this token
        :return: str containing access_token
        :rtype: str
        """
        r = requests.post('{}/oauth/access_token'.format(self.__bitly_api_base_url), headers={'Content-Type': 'application/x-www-form-urlencoded', 'cache-control': 'no-cache'}, auth=(self.__bitly_api_username, self.__bitly_api_password))
        return r.text

    def get_token(self):
        return self.__api_token

    def groups(self, access_token=None):
        """
        Get list of groups  associated with your bitly account free tier defaults to 1 group
        :param access_token:
        :type access_token:
        :return: dict object containing array of dict groups
        :rtype: dict
        """
        r = requests.get('{}/v4/groups'.format(self.__bitly_api_base_url), headers={'Content-Type':'application/json', 'Authorization': 'Bearer {}'.format(self.get_token() if not (access_token) else access_token)})
        return r.json()

    def shorten_url(self, uri, group_guid , access_token=None):
        """
        Creates a bitly shorten url link for a given long url, see rate limiting to avoid errors when invoking reqquest calls to the bitly api
        https://dev.bitly.com/rate_limiting.html
        :param uri: users long url
        :type uri:
        :param access_token: Optional bitly api access_token
        :type access_token:
        """
        r = requests.post('{}/v4/shorten'.format(self.__bitly_api_base_url), data=json.dumps({'long_url': uri, 'domain': 'bit.ly', 'group_guid':group_guid}), headers={'Content-Type':'application/json', 'Authorization': 'Bearer {}'.format(self.get_token() if not (access_token) else access_token)})
        return r.json()