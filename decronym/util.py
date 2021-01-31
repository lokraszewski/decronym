import re
import requests
import hashlib
import os

URL_REGEX = re.compile(
    "^"
    # protocol identifier
    "(?:(?:https?|ftp)://)"
    # user:pass authentication
    "(?:\S+(?::\S*)?@)?" "(?:"
    # IP address exclusion
    # private & local networks
    "(?!(?:10|127)(?:\.\d{1,3}){3})"
    "(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})"
    "(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})"
    # IP address dotted notation octets
    # excludes loopback network 0.0.0.0
    # excludes reserved space >= 224.0.0.0
    # excludes network & broadcast addresses
    # (first & last IP address of each class)
    "(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])"
    "(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}"
    "(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))"
    "|"
    # host name
    "(?:(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)"
    # domain name
    "(?:\.(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)*"
    # TLD identifier
    "(?:\.(?:[a-z\u00a1-\uffff]{2,}))" ")"
    # port number
    "(?::\d{2,5})?"
    # resource path
    "(?:/\S*)?" "$",
    re.UNICODE,
)


def is_url_valid(input) -> bool:
    return bool(URL_REGEX.match(input))


def is_url_online(input)-> bool:
    try:
        r = requests.head(input, allow_redirects=True,timeout=0.4)
        return r.status_code == 200
    except:
        return False
        

def generate_cache_filepath(input: str):
    hash_object = hashlib.md5(input.encode("utf-8"))
    dir = get_cache_dir()
    filename = f"{hash_object.hexdigest()}.json"
    return os.path.join(dir, filename)


def get_cache_dir():
    return os.path.join(os.environ["HOME"], ".config/decronym", "cache")
