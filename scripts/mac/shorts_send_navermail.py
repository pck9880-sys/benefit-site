"""완성 영상을 네이버 메일 '내게쓰기'로 보내기 (2026-11-22 사용자: 전달 채널 고정) — SMTP(smtp.naver.com:587, STARTTLS).
사용: python3 scripts/mac/shorts_send_navermail.py <영상.mp4> <제목>
비밀값: ~/쇼츠작업/navermail.env  (NAVER_ID=아이디, NAVER_APP_PW=애플리케이션 비밀번호 또는 비밀번호) — 깃·채팅 금지.
네이버 메일 환경설정 > POP3/IMAP 설정 > IMAP/SMTP 사용함 이 켜져 있어야 함. 받는 사람 = 본인(NAVER_ID@naver.com)만."""
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

env = Path.home() / "쇼츠작업" / "navermail.env"
cfg = {}
if env.exists():
    for line in env.read_text("utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip().strip("'\"")
uid, pw = cfg.get("NAVER_ID", ""), cfg.get("NAVER_APP_PW", "")
if not uid or not pw:
    print(f"실패(네이버메일): {env} 에 NAVER_ID·NAVER_APP_PW 없음"); sys.exit(1)
uid = uid.split("@")[0]
f, subj = Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else ""
if not f.exists():
    print("실패(네이버메일): 파일 없음", f); sys.exit(1)
me = f"{uid}@naver.com"
m = EmailMessage()
m["From"], m["To"], m["Subject"] = me, me, subj or f.parent.name
m.set_content(f"{subj}\n\n(유튜브 제목 복사용 — 첨부 영상을 길게 눌러 저장하면 갤러리로 들어가요)")
name = (f.parent.name[:30] + f.suffix) if f.stem == "영상" else f.name
m.add_attachment(f.read_bytes(), maintype="video" if f.suffix.lower() == ".mp4" else "application",
                 subtype="mp4" if f.suffix.lower() == ".mp4" else "octet-stream", filename=name)
try:
    with smtplib.SMTP("smtp.naver.com", 587, timeout=60) as s:
        s.starttls(); s.login(uid, pw); s.send_message(m)
    print(f"성공(네이버메일): 내게쓰기로 '{m['Subject']}' + 첨부 {f.stat().st_size // 1024}KB")
except smtplib.SMTPAuthenticationError:
    print("실패(네이버메일): 로그인 거부 — SMTP 사용함 설정·애플리케이션 비밀번호 확인"); sys.exit(1)
except Exception as ex:
    print(f"실패(네이버메일): {type(ex).__name__}"); sys.exit(1)
