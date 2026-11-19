"""접수 링크를 '제출 직전'까지 채워주는 도우미.

- 구글폼: 미리 채워진(prefill) 링크 생성 → 열면 이름·연락처·출품작·설명이 채워져 있음
- 이메일: 받는사람·제목·본문이 채워진 메일 작성 화면을 여는 링크 (GitHub Pages 중계 페이지, 내용은 # 뒤에 있어 서버로 전송되지 않음)
- 네이버폼 등: 미리 채우기를 지원하지 않아 탭-복사용 블록 제공
최종 '제출/보내기' 버튼은 항상 사람이 누릅니다.
"""
import json
import os
import re
from urllib.parse import quote, urlencode

import requests

from . import config

UA = {"User-Agent": "Mozilla/5.0"}
GFORM = re.compile(r"https?://(?:forms\.gle/[\w-]+|docs\.google\.com/forms/[^\s\"'<>]+)")
NFORM = re.compile(r"https?://(?:form\.naver\.com/[^\s\"'<>]+|naver\.me/[\w]+)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]*\w")


def me():
    """GitHub Secrets 에 저장한 제출용 개인정보 (없으면 빈 값)."""
    g = lambda k: (os.environ.get(k) or "").strip()
    return {"name": g("SUBMIT_NAME"), "phone": g("SUBMIT_PHONE"), "email": g("SUBMIT_EMAIL"),
            "address": g("SUBMIT_ADDRESS"), "birth": g("SUBMIT_BIRTH")}


def find_targets(raw_html, detail_text, home):
    blob = (raw_html or "") + "\n" + (detail_text or "") + "\n" + (home or "")
    emails = [e for e in dict.fromkeys(EMAIL.findall(detail_text or "")) if not e.endswith((".png", ".jpg"))]
    return {"gforms": list(dict.fromkeys(m.rstrip(").,") for m in GFORM.findall(blob))),
            "nforms": list(dict.fromkeys(m.rstrip(").,") for m in NFORM.findall(blob))),
            "emails": emails}


ROLE_RULES = [
    ("consent", r"동의"),
    ("explanation", r"설명|의미|의도|취지|이유|소개"),
    ("entry", r"슬로건|네이밍|명칭|표어|응모작|출품작|작품명|제안\s*이름|이름\s*제안|캐치프레이즈|문구"),
    ("name", r"^\s*(이름|성명|성함)|응모자\s*(이름|성명)|참가자\s*(이름|성명)"),
    ("phone", r"연락처|전화|휴대폰|핸드폰|휴대전화"),
    ("email", r"이메일|e-?mail|메일"),
    ("birth", r"생년월일|출생|나이|연령"),
    ("address", r"주소|거주"),
]


def _role(title):
    t = (title or "").lower()
    for role, pat in ROLE_RULES:
        if re.search(pat, t, re.I):
            return role
    return None


def gform_prefill(url, values):
    """구글폼 문항을 읽어 미리 채운 링크를 만든다. 실패하면 None."""
    try:
        r = requests.get(url, headers=UA, timeout=30, allow_redirects=True)
    except requests.RequestException:
        return None
    if "closedform" in r.url or "accounts.google" in r.url:
        return None
    m = re.search(r"FB_PUBLIC_LOAD_DATA_\s*=\s*(.*?);\s*</script>", r.text, re.S)
    if not m:
        return None
    try:
        items = json.loads(m.group(1))[1][1]
    except (ValueError, IndexError, TypeError):
        return None
    params, filled = [], []
    for q in items:
        try:
            title, entry = q[1], q[4][0][0]
        except (IndexError, TypeError):
            continue
        role = _role(title)
        if role in values and values[role] and role != "consent":
            params.append((f"entry.{entry}", values[role]))
            filled.append(role)
    if not params:
        return None
    base = re.sub(r"/viewform.*$|/$", "", r.url.split("?")[0])
    return {"url": f"{base}/viewform?usp=pp_url&{urlencode(params)}", "filled": filled}


def email_link(to, subject, body):
    """메일 작성 화면을 바로 여는 링크 (GitHub Pages 중계)."""
    frag = urlencode({"to": to, "s": subject, "b": body}, quote_via=quote)
    return f"{config.SITE_URL}/static/mail.html#{frag}"
