from urllib.parse import urlencode

BASE_URL = "https://hirify.me"


def build_url(**params) -> str:
    clean_params = {k: v for k, v in params.items() if v not in [None, ""]}
    return f"{BASE_URL}?{urlencode(clean_params)}" if clean_params else BASE_URL
