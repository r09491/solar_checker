import os
import hashlib
import hmac
import json
import random
import time
import binascii

from typing import Optional

def hmac_sha256(data, key):
    if (data is None) or (key is None):
        return None
    hashed = hmac.new(
        key.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).digest()
    sign = binascii.hexlify(
        hashed
    ).decode('utf-8')
    return sign

def get_map(json_obj, prefix=""):
  def flatten(obj, pre=""):
    result = {}
    if isinstance(obj, dict):
      for k, v in obj.items():
        result.update(flatten(v, f"{pre}.{k}" if pre else k))
    elif isinstance(obj, list):
      for i, item in enumerate(obj):
        result.update(flatten(item, f"{pre}[{i}]"))
    else: result[pre] = obj
    return result
  return flatten(json_obj, prefix)

def get_qstr(params): return '&'.join([f"{key}={params[key]}" for key in sorted(params.keys())])

def get_headers(key: str, secret:str, params: dict) -> dict:
    nonce     = str(random.randint(100000, 999999))
    timestamp = str(int(time.time() * 1000))
    headers   = {'accessKey':key,'nonce':nonce,'timestamp':timestamp}
    sign_str  = (get_qstr(get_map(params)) + '&' if params else '') + get_qstr(headers)
    ##print(f"qStr: {sign_str}")
    headers['sign'] = hmac_sha256(sign_str, secret)
    return headers


def get_dot_ecoflow_api() -> Optional[list]:
    home = os.path.expanduser('~')
    enames = [".ecoflow_api", os.path.join(home, ".ecoflow_api" )]
    for en in enames:
        try:
            with open(en, "r") as ef:
                efapi = json.load(ef)
            break
        except FileNotFoundError:
            efapi = None
    return efapi.values() if efapi is not None else None
