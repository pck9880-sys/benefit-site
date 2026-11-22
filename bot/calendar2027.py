"""2027 지원금 달력: 폰 잠금화면 배경(1179x2556) 12장 + A4 인쇄용. 일정은 2026년 실제 일정 기준 '예상'."""
import calendar
from pathlib import Path

YEAR = 2027
# (월, [(이름, 기간 표기, 강조일 목록, 태그)])  — 날짜는 2026년 일정 기준 예상
MONTHS = {
    1: [("연말정산 간소화 서비스 개통", "1월 15일경", [15], "직장인"),
        ("에너지바우처 동절기 사용", "~5월 31일", [], "저소득")],
    2: [("연말정산 환급", "2월 급여일", [], "직장인"),
        ("국가장학금 1학기 2차 신청", "2월 초 ~ 3월 중순", [3], "대학생")],
    3: [("근로장려금 반기 신청 (하반기분)", "3월 1일 ~ 15일", [1, 15], "근로자"),
        ("국가장학금 1학기 2차 마감", "3월 중순", [16], "대학생")],
    4: [("근로·자녀장려금 안내문 확인", "4월 말 발송 예상", [], "근로자"),
        ("종합소득세 신고 준비", "5월 신고 대비", [], "프리랜서")],
    5: [("근로·자녀장려금 정기 신청", "5월 1일 ~ 31일", [1, 31], "근로자"),
        ("종합소득세 신고", "5월 1일 ~ 31일", [], "프리랜서"),
        ("국가장학금 2학기 1차 신청", "5월 말 시작", [24], "대학생")],
    6: [("에너지바우처 신청 시작", "6월 중순 ~ 12월 31일", [15], "저소득"),
        ("청년미래적금 가입 모집", "6월", [], "청년"),
        ("국가장학금 2학기 1차 마감", "6월 말", [22], "대학생")],
    7: [("에너지바우처 하절기 사용 시작", "7월 1일 ~ 9월 30일", [1], "저소득")],
    8: [("국가장학금 2학기 2차 신청", "8월 중순 ~ 9월 초", [12], "대학생")],
    9: [("근로장려금 반기 신청 (상반기분)", "9월 1일 ~ 15일", [1, 15], "근로자"),
        ("어르신·어린이 독감 무료접종 시작", "9월 말~10월", [], "가족")],
    10: [("에너지바우처 동절기 사용 시작", "10월 초 ~ 다음해 5월", [1], "저소득")],
    11: [("국가장학금 1학기 1차 신청", "11월 말 시작", [23], "대학생")],
    12: [("에너지바우처 신청 마감", "12월 31일", [31], "저소득"),
         ("청년미래적금 가입 모집", "12월", [], "청년"),
         ("국가장학금 1학기 1차 마감", "12월 말", [28], "대학생")],
}
EN = ["", "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
HOLI = {1: [1], 2: [6, 7, 8, 9], 3: [1, 3], 5: [5, 13], 6: [3, 6], 8: [15, 16], 9: [14, 15, 16], 10: [3, 4, 9, 11], 12: [25]}  # 2027 공휴일(대체 포함, 예정)
ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"


def mark_svg(size):
    g = {1: ('#8fd3ff', '#6b4cf5', '#2a0e6e', '0 0 1 1'), 2: ('#ffd6a0', '#ff5fae', '#5b1fd0', '1 0 0 1'), 3: ('#3b5bff', '#c25cf0', '#ffb3d1', '.5 1 .5 0')}
    defs = "".join(f'<linearGradient id="c{i}" x1="{v[3].split()[0]}" y1="{v[3].split()[1]}" x2="{v[3].split()[2]}" y2="{v[3].split()[3]}"><stop offset="0" stop-color="{v[0]}"/><stop offset=".5" stop-color="{v[1]}"/><stop offset="1" stop-color="{v[2]}"/></linearGradient>' for i, v in g.items())
    tf = {1: "translate(-14,-8)", 2: "translate(16,-4) rotate(40)", 3: "translate(0,14) rotate(80)"}
    polys = "".join(f'<g transform="{tf[i]}"><polygon points="0,-100 87,50 -87,50" fill="url(#c{i})" stroke="url(#c{i})" stroke-width="70" stroke-linejoin="round" style="mix-blend-mode:screen" opacity=".92"/></g>' for i in (1, 2, 3))
    return f'<svg width="{size}" height="{size}" viewBox="-170 -170 340 340" style="overflow:visible;filter:drop-shadow(0 0 {size//14}px rgba(160,130,255,.75))"><defs>{defs}</defs>{polys}</svg>'


CSS = f"""
@font-face{{font-family:P;src:url(file://{FONTS}/NanumSquareRoundR.woff2);font-weight:400}}
@font-face{{font-family:P;src:url(file://{FONTS}/NanumSquareRoundB.woff2);font-weight:600 700}}
@font-face{{font-family:P;src:url(file://{FONTS}/NanumSquareRoundEB.woff2);font-weight:800}}
@font-face{{font-family:Q;src:url(file://{FONTS}/quicksand-700.woff2);font-weight:700}}
*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:P,sans-serif;-webkit-font-smoothing:antialiased}}
"""


def wallpaper_html(m):
    cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
    weeks = cal.monthdayscalendar(YEAR, m)
    items = MONTHS[m]
    hi = {d for _, _, ds, _ in items for d in ds}
    cells = ""
    for w in weeks:
        for i, d in enumerate(w):
            if not d:
                cells += "<i></i>"
                continue
            cls = ("sun " if i == 0 or d in HOLI.get(m, []) else "sat " if i == 6 else "") + ("hi" if d in hi else "")
            cells += f'<i class="{cls}">{d}</i>'
    rows = "".join(f'<li><b>{n}</b><span>{p}</span><em>{t}</em></li>' for n, p, _, t in items)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}
body{{width:1179px;height:2556px;background:#000;color:#fff;position:relative;overflow:hidden;display:flex;flex-direction:column;padding:900px 96px 140px}}
.hd{{display:flex;justify-content:space-between;align-items:center}}
.mon b{{display:block;font-size:190px;font-weight:800;letter-spacing:-.04em;line-height:1}}
.mon span{{display:block;margin-top:16px;font-family:Q;font-size:42px;letter-spacing:.18em;color:#8f86c9}}
.grid{{margin-top:70px;display:grid;grid-template-columns:repeat(7,1fr);row-gap:10px;text-align:center}}
.grid .h{{font-size:30px;font-weight:600;color:#5d5a78;height:56px;line-height:56px}}
.grid i{{font-style:normal;font-size:40px;font-weight:600;color:#cfcde6;height:74px;line-height:74px;position:relative;z-index:0}}
.grid i.sun{{color:#ff8fb0}}.grid i.sat{{color:#9db4ff}}
.grid i.hi{{color:#fff}}.grid i.hi::before{{content:"";position:absolute;left:50%;top:50%;width:72px;height:72px;margin:-36px;border-radius:50%;background:radial-gradient(circle,#7a5cff,#5b3fe0);box-shadow:0 0 26px rgba(130,100,255,.75);z-index:-1}}
.list{{margin-top:44px;list-style:none}}
.list li{{display:grid;grid-template-columns:1fr auto;column-gap:20px;padding:24px 0;border-top:1px solid #1d1b2e}}
.list b{{font-size:38px;font-weight:700;line-height:1.3}}.list span{{grid-column:1;font-size:31px;color:#8c89a8;margin-top:6px}}
.list em{{grid-row:1/3;grid-column:2;align-self:center;font-style:normal;font-size:27px;font-weight:700;color:#b9a8ff;border:1.5px solid #3a3366;border-radius:999px;padding:8px 22px}}
.foot{{margin-top:auto;display:flex;justify-content:space-between;align-items:center;font-size:27px;color:#55526e}}
.foot b{{font-family:Q;color:#a99ff0;font-size:34px}}
</style></head><body>
<div class="hd"><div class="mon"><b>{m}월</b><span>{EN[m]} {YEAR}</span></div>{mark_svg(210)}</div>
<div class="grid">{"".join(f'<i class="h">{d}</i>' for d in "일월화수목금토")}{cells}</div>
<ul class="list">{rows}</ul>
<div class="foot"><span>2026년 일정 기준 예상 · 공고 확인 필수</span><b>benefy.kr</b></div>
</body></html>"""


def a4_html():
    blocks = ""
    for m in range(1, 13):
        items = "".join(f'<li><b>{n}</b><span>{p} · {t}</span></li>' for n, p, _, t in MONTHS[m])
        blocks += f'<section><h3>{m}월 <small>{EN[m][:3]}</small></h3><ul>{items}</ul></section>'
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}
@page{{size:A4;margin:0}}
body{{width:2480px;height:3508px;background:#fff;color:#14152b;padding:170px 150px}}
header{{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:6px solid #14152b;padding-bottom:40px}}
header h1{{font-size:120px;font-weight:800;letter-spacing:-.03em;line-height:1.1}}header h1 em{{font-style:normal;color:#5b3fe0}}
header p{{font-size:40px;color:#6b6d86;margin-top:16px}}
.brand{{display:flex;align-items:center;gap:24px;font-family:Q;font-size:64px;color:#14152b}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:46px 60px;margin-top:70px}}
section{{border-top:3px solid #e4e2ef;padding-top:26px;min-height:560px}}
h3{{font-size:64px;font-weight:800}}h3 small{{font-family:Q;font-size:32px;color:#8f86c9;letter-spacing:.12em;margin-left:10px}}
ul{{list-style:none;margin-top:20px}}li{{padding:16px 0 16px 34px;position:relative}}
li::before{{content:"";position:absolute;left:0;top:30px;width:16px;height:16px;border-radius:50%;background:#6b4cf5}}
li b{{display:block;font-size:38px;font-weight:700;line-height:1.35}}li span{{font-size:32px;color:#6b6d86}}
footer{{position:absolute;left:150px;right:150px;bottom:120px;display:flex;justify-content:space-between;font-size:32px;color:#8a8ca3;border-top:3px solid #e4e2ef;padding-top:30px}}
footer b{{color:#5b3fe0}}
</style></head><body>
<header><div><h1>2027 <em>지원금</em> 달력</h1><p>매달 놓치면 안 되는 신청 일정 · 냉장고에 붙여두세요</p></div><div class="brand">{mark_svg(120).replace('drop-shadow(0 0 8px rgba(160,130,255,.75))','none')}Benefy</div></header>
<div class="grid">{blocks}</div>
<footer><span>2026년 실제 일정을 기준으로 한 예상 일정이에요. 정확한 날짜는 각 기관 공고를 꼭 확인하세요.</span><b>benefy.kr에서 내 지원금 30초 진단</b></footer>
</body></html>"""


def render(out_dir, months=range(1, 13), a4=True):
    from playwright.sync_api import sync_playwright
    import glob
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    exe = (glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome") or [None])[0]
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe, args=["--disable-dev-shm-usage", "--allow-file-access-from-files"]) if exe else p.chromium.launch()
        pg = b.new_page(viewport={"width": 1179, "height": 2556})
        for m in months:
            f = out / f"_w{m}.html"; f.write_text(wallpaper_html(m), encoding="utf-8")
            pg.goto(f.as_uri()); pg.wait_for_timeout(250); pg.screenshot(path=str(out / f"2027-{m:02d}.png")); f.unlink()
        if a4:
            pg.set_viewport_size({"width": 2480, "height": 3508})
            f = out / "_a4.html"; f.write_text(a4_html(), encoding="utf-8")
            pg.goto(f.as_uri()); pg.wait_for_timeout(300); pg.screenshot(path=str(out / "2027-a4.png"))
            pg.pdf(path=str(out / "2027-benefy-calendar-a4.pdf"), width="210mm", height="297mm", print_background=True, scale=0.3198)
            f.unlink()
        b.close()
