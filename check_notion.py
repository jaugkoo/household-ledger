"""
노션 연동 문제 진단: DB 스키마 조회 + 테스트 페이지 생성 시도
실행: python check_notion.py
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
BASE = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def main():
    print("=" * 60)
    print("노션 연동 진단")
    print("=" * 60)
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        print("[오류] .env에 NOTION_TOKEN, NOTION_DATABASE_ID가 없습니다.")
        return
    print(f"NOTION_DATABASE_ID: {NOTION_DATABASE_ID[:8]}...")
    print()

    # 1. DB 스키마 조회
    print("[1] 데이터베이스 스키마 조회 (GET /databases/{id})")
    r = requests.get(f"{BASE}/databases/{NOTION_DATABASE_ID}", headers=HEADERS)
    print(f"    상태 코드: {r.status_code}")
    if r.status_code != 200:
        print(f"    응답: {r.text[:500]}")
        print()
        if r.status_code == 401:
            print("    → 401: 토큰이 잘못되었거나 만료됨. Notion 연동에서 새 토큰 발급 후 .env 갱신.")
        elif r.status_code == 404:
            print("    → 404: DB를 찾을 수 없음. 데이터베이스에 연동(Integration)을 연결했는지, ID가 맞는지 확인.")
        return
    db = r.json()
    props = db.get("properties", {})
    print("    DB 속성 (코드에서 기대하는 이름/타입):")
    expected = {
        "항목": "title",
        "날짜": "date",
        "합계": "number",
        "단가": "number",
        "수량": "number",
        "분류": "select",
        "사용처": "rich_text",
        "원본파일": "rich_text",
    }
    for name, etype in expected.items():
        if name in props:
            p = props[name]
            actual_type = p.get("type", "?")
            ok = "OK" if actual_type == etype else f"X (실제: {actual_type})"
            opts = ""
            if actual_type == "select" and "select" in p and "options" in p["select"]:
                opts = " 옵션: " + ", ".join(o.get("name", "") for o in p["select"].get("options", []))
            print(f"      {name}: {actual_type} {ok}{opts}")
        else:
            print(f"      {name}: 없음 (필요: {etype})")
    extra = set(props) - set(expected)
    if extra:
        print(f"    기타 속성: {', '.join(extra)}")
    print()

    # 2. 테스트 페이지 생성 (main.py와 동일한 payload)
    print("[2] 테스트 페이지 생성 (POST /pages) - main.py와 동일한 구조")
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "항목": {"title": [{"text": {"content": "[진단] 테스트 항목"}}]},
            "날짜": {"date": {"start": "2025-01-31"}},
            "합계": {"number": 1000},
            "단가": {"number": 1000},
            "수량": {"number": 1},
            "분류": {"select": {"name": "기타"}},
            "사용처": {"rich_text": [{"text": {"content": "테스트 매장"}}]},
        },
    }
    r2 = requests.post(f"{BASE}/pages", headers=HEADERS, json=payload)
    print(f"    상태 코드: {r2.status_code}")
    if r2.status_code != 200:
        print(f"    응답 본문: {r2.text}")
        try:
            err = r2.json()
            if "message" in err:
                print(f"    메시지: {err['message']}")
            if "code" in err:
                print(f"    코드: {err['code']}")
        except Exception:
            pass
        print()
        if r2.status_code == 400:
            print("    → 400: 속성 이름/타입이 DB와 다르거나, select 옵션에 '기타'가 없을 수 있음.")
        return
    print("    성공: 테스트 페이지가 생성되었습니다. (노션에서 '[진단] 테스트 항목' 페이지 삭제 가능)")
    print()
    print("=" * 60)
    print("진단 완료. 위에서 속성 이름/타입이 OK가 아니거나 페이지 생성이 실패한 항목을 수정하세요.")
    print("=" * 60)

if __name__ == "__main__":
    main()
