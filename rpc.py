# Performs Remote Procedure Calls to the Bitcoin Core

import requests
import base64
import json

class BitcoinRPC:
    
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password
        authpair = self.user.encode("utf-8") + b":" + self.password.encode("utf-8")
        self.authheader = b'Basic ' + base64.b64encode(authpair)
        self.command_id = 0

    def issueCommand(self, method, params=None):
        self.command_id += 1

        headers = { "Content-type": "text/plain",
                    "Authorization" : self.authheader }
        
        command = { "jsonrpc": "1.0",
                    "id": self.command_id,
                    "method": method,
                    "params": params }
        
        r = requests.post(self.host, headers=headers, data=json.dumps(command))
        return json.loads(r.text)["result"]

    def getBlockTemplate(self):
        params = [{"rules": ["segwit"]}]
        return self.issueCommand("getblocktemplate", params)

    def getMiningInfo(self):
        params = []
        return self.issueCommand("getmininginfo", params)
    
    def submitBlock(self, data):
        params = [data]
        return self.issueCommand("submitblock", params)
    
