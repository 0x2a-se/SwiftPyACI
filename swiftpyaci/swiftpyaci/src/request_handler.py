import requests
import logging

class RequestHandler:

    def __init__(self, url: str, verify_ssl = True):
        self.base_url = url
        self.log = logging.getLogger()
        self.session = requests.Session()
        self.session.verify = verify_ssl
        if not self.session.verify:
            from urllib3.exceptions import InsecureRequestWarning
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    def raise_for_status(self, resp):
        if not resp.ok:
            print(resp.text)
        resp.raise_for_status()

    def list(self, uri, params = None, data_format = "json", use_api_uri = True):
        return self.get(uri,params = params, data_format = "json").get("imdata", [])


    def get(self, uri, params = None, data_format = "json", use_api_uri = True):
        if use_api_uri:
            url = f"{self.base_url}/api/{uri}.{data_format}"
        else:
            url = f"{self.base_url}/{uri}.{data_format}"

        self.log.debug(f"Getting from '{url}'")
        resp = self.session.get(url, params=params)
        self.raise_for_status(resp)
        return resp.json() if data_format == "json" else resp.text

    def get_mo(self, uri, params = None):
        resp = self.get(uri,params = params, data_format = "json").get("imdata", [])
        if len(resp) == 0:
            return {}
        if len(resp) > 1:
            raise ValueError(f"To many results in respone, expected 1 result got {len(resp)}")
        return resp[0]
    
    def post(self, uri, data = None, data_format = "json"):
        url = f"{self.base_url}/api/{uri}.{data_format}"
        self.log.debug(f"Posting to '{url}'")

        if data_format == "json":
            resp = self.session.post(url, json=data)
        else:
            resp = self.session.post(url, data=data)
        
        self.raise_for_status(resp)
        return resp
    
    