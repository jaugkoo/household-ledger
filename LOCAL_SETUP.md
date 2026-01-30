# 로컬 컴퓨터에서 실행하기 (Windows)

이 가이드는 AWS 없이 **개인 노트북에서만** 영수증 자동화를 실행하는 방법입니다.

## 1. 기본 실행 방법

터미널(PowerShell)을 열고:

```powershell
cd "C:\Users\lg59482\OneDrive\바탕 화면\receipt-automation"
python main.py
```

터미널 창을 열어두면 계속 실행됩니다.

---

## 2. 컴퓨터 시작 시 자동 실행 (선택사항)

### 방법 A: 시작 프로그램에 추가 (간단)

1. **배치 파일 생성**
   - `receipt-automation` 폴더에 `start.bat` 파일 생성
   - 내용:
     ```batch
     @echo off
     cd /d "C:\Users\lg59482\OneDrive\바탕 화면\receipt-automation"
     python main.py
     pause
     ```

2. **시작 프로그램에 추가**
   - `Win + R` → `shell:startup` 입력
   - 열린 폴더에 `start.bat` 바로가기 복사

3. **재부팅 후 자동 실행됨**

---

### 방법 B: 작업 스케줄러 (백그라운드 실행)

1. **작업 스케줄러 열기**
   - `Win + R` → `taskschd.msc`

2. **새 작업 만들기**
   - 우측 "작업 만들기" 클릭
   - **일반 탭**:
     - 이름: `Receipt Automation`
     - "사용자가 로그온할 때만 실행" 선택
   
3. **트리거 탭**:
   - "새로 만들기" → "로그온할 때" 선택

4. **동작 탭**:
   - "새로 만들기" → "프로그램 시작"
   - 프로그램/스크립트: `python`
   - 인수 추가: `main.py`
   - 시작 위치: `C:\Users\lg59482\OneDrive\바탕 화면\receipt-automation`

5. **확인** 클릭

---

## 3. 실행 확인

- 핸드폰에서 영수증 사진 촬영
- OneDrive 동기화 대기 (자동)
- 노션 데이터베이스 확인

---

## 문제 해결

### "pip 인식 안 됨" 오류
```powershell
python -m pip install -r requirements.txt
```

### 스크립트가 멈춤
- `Ctrl + C`로 종료 후 다시 실행
- 또는 작업 관리자에서 python.exe 종료

---

**추천:** 방법 A (시작 프로그램)가 가장 간단합니다!
