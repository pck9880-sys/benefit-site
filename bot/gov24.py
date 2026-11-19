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


def support_conditions(service_id):
    """서비스별 자격 조건 코드 (JA0101 남성, JA0110 나이 시작 ...). {'codes': [...Y인 코드], 'age_min', 'age_max'}"""
    if config.MOCK:
        return {"codes": ["JA0412", "JA0204"], "age_min": 19, "age_max": 39}
    res = _get("supportConditions", {"cond[서비스ID::EQ]": service_id})
    data = (res.get("data") or [{}])[0]
    codes = sorted(k for k, v in data.items() if k.startswith("JA") and str(v).upper() == "Y")
    def num(k):
        try:
            return int(data.get(k)) if data.get(k) not in (None, "", 0, "0") else None
        except (TypeError, ValueError):
            return None
    return {"codes": codes, "age_min": num("JA0110"), "age_max": num("JA0111")}


def list_services_by_id(service_id):
    """서비스 1건의 목록 정보 (수정일시 등)."""
    if config.MOCK:
        return []
    res = _get("serviceList", {"cond[서비스ID::EQ]": service_id})
    return res.get("data") or []


def search(keyword):
    """서비스명에 키워드가 들어간 공공서비스 목록."""
    if config.MOCK:
        return [s for s in list_services() if keyword in (s.get("서비스명") or "")]
    res = _get("serviceList", {"page": 1, "perPage": 100, "cond[서비스명::LIKE]": keyword})
    return res.get("data") or []
