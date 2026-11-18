"""행정안전부 대한민국 공공서비스(혜택) 정보 API (data.go.kr 15113968)."""
import json
import time

import requests

from . import config

BASE = "https://api.odcloud.kr/api/gov24/v3"


def _get(path, params):
    params = {"serviceKey": config.DATA_GO_KR_KEY, "returnType": "JSON", **params}
    last = None
    for attempt in range(4):
        try:
            r = requests.get(f"{BASE}/{path}", params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            last = RuntimeError(f"gov24 {path} HTTP {r.status_code}: {r.text[:200]}")
        except requests.RequestException as e:
            last = e
        time.sleep(2 ** attempt)
    raise last


def list_services(max_pages=20, per_page=500):
    """전체 서비스 목록 (약 1만 건)."""
    if config.MOCK:
        return json.loads((config.ROOT / "tests" / "sample_list.json").read_text("utf-8"))
    items, page = [], 1
    while page <= max_pages:
        res = _get("serviceList", {"page": page, "perPage": per_page})
        data = res.get("data") or []
        items.extend(data)
        if not data or page * per_page >= int(res.get("totalCount", 0)):
            break
        page += 1
    return items


def service_detail(service_id):
    if config.MOCK:
        return json.loads((config.ROOT / "tests" / "sample_detail.json").read_text("utf-8"))
    res = _get("serviceDetail", {"cond[서비스ID::EQ]": service_id})
    data = res.get("data") or []
    return data[0] if data else {}
