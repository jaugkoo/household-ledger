# 빠른 시작 가이드 (Quick Start Guide)

## 새로운 기능 활성화하기

영수증 자동화 프로그램이 업데이트되었습니다! 이제 다음 기능들이 추가되었습니다:

✅ **데이터 검증** - 잘못된 데이터 자동 감지  
✅ **중복 제거** - 중복된 항목 자동 삭제  
✅ **오류 자동 수정** - 문제 발견 시 이미지 재분석  
✅ **날짜별 정리** - 날짜 유효성 검사 및 정렬  

---

## 1단계: Notion 데이터베이스 업데이트

새로운 기능을 사용하려면 Notion 데이터베이스에 필드를 하나 추가해야 합니다.

### Notion에서 설정하기:

1. 가계부 데이터베이스 열기
2. 오른쪽 상단 "..." 메뉴 → "속성" 클릭
3. "+ 새 속성" 클릭
4. 다음과 같이 설정:
   - **속성 이름**: `원본파일`
   - **속성 유형**: 텍스트

이 필드는 어떤 이미지에서 데이터가 추출되었는지 추적하여 오류 수정 시 정확한 항목만 삭제할 수 있게 합니다.

---

## 2단계: 프로그램 실행

기존과 동일하게 실행하면 됩니다:

```powershell
cd "C:\Users\lg59482\OneDrive\바탕 화면\receipt-automation"
python main.py
```

---

## 3단계: 작동 확인

프로그램이 실행되면 다음과 같은 로그를 볼 수 있습니다:

```
2026-01-30 20:15:23 - Processing new file: receipt_001.jpg
2026-01-30 20:15:30 - Extracted 5 items from receipt.
2026-01-30 20:15:35 - Successfully added 5 / 5 items to Notion.
2026-01-30 20:15:35 - Checking for duplicate entries...
2026-01-30 20:15:37 - Validating data quality...
```

---

## 설정 변경하기 (선택사항)

`.env` 파일을 열어서 기능을 켜거나 끌 수 있습니다:

```env
# 모든 기능 활성화 (권장)
ENABLE_VALIDATION=true
ENABLE_DUPLICATE_DETECTION=true
ENABLE_AUTO_CORRECTION=true

# 자동 수정 비활성화 (수동 확인 원할 때)
ENABLE_AUTO_CORRECTION=false
```

---

## 주요 기능 설명

### 🔍 중복 검사
- 같은 항목명 + 날짜 + 사용처 + 가격이 동일하면 중복으로 판단
- 가장 최근 항목만 남기고 나머지는 자동 삭제
- 로그에서 "Removed X duplicate entries" 확인 가능

### ✅ 데이터 검증
다음 항목을 자동으로 검사합니다:
- 필수 필드 누락 (항목명, 날짜, 가격)
- 잘못된 날짜 형식
- 음수 또는 0원 가격
- 잘못된 카테고리

### 🔧 자동 오류 수정
1. 검증 오류 발견
2. 원본 이미지 재분석 (더 엄격한 프롬프트 사용)
3. 기존 잘못된 데이터 삭제
4. 수정된 데이터 업로드

---

## 문제 해결

### "원본파일" 필드가 없다는 오류
→ 1단계의 Notion 데이터베이스 설정을 확인하세요.

### 중복이 제거되지 않음
→ `.env` 파일에서 `ENABLE_DUPLICATE_DETECTION=true` 확인

### 자동 수정이 작동하지 않음
→ `.env` 파일에서 `ENABLE_AUTO_CORRECTION=true` 확인

---

## 더 자세한 정보

- 전체 기능 설명: [README.md](file:///C:/Users/lg59482/OneDrive/바탕%20화면/receipt-automation/README.md)
- 구현 세부사항: [walkthrough.md](file:///C:/Users/lg59482/.gemini/antigravity/brain/7777f575-fa00-45c6-a7b2-49792eb710e8/walkthrough.md)

---

**이제 영수증을 찍으면 자동으로 검증, 중복 제거, 오류 수정이 진행됩니다! 🎉**
