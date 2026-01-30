"""
Receipt Automation - Setup Wizard
초기 설정을 위한 GUI 도구
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from pathlib import Path

class SetupWizard:
    def __init__(self, root):
        self.root = root
        self.root.title("영수증 자동화 - 초기 설정")
        self.root.geometry("600x700")
        self.root.resizable(False, False)
        
        # 현재 디렉토리
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.env_file = os.path.join(self.script_dir, ".env")
        
        # 기존 설정 로드
        self.existing_config = self.load_existing_config()
        
        self.create_widgets()
    
    def load_existing_config(self):
        """기존 .env 파일에서 설정 로드"""
        config = {}
        if os.path.exists(self.env_file):
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        return config
    
    def create_widgets(self):
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 제목
        title = ttk.Label(main_frame, text="영수증 자동화 초기 설정", 
                         font=('Arial', 16, 'bold'))
        title.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 설명
        desc = ttk.Label(main_frame, 
                        text="필요한 API 키와 설정을 입력해주세요.\n기존 설정이 있으면 자동으로 표시됩니다.",
                        justify=tk.LEFT)
        desc.grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
        current_row = 2
        
        # OpenAI API Key
        ttk.Label(main_frame, text="OpenAI API Key:", font=('Arial', 10, 'bold')).grid(
            row=current_row, column=0, sticky=tk.W, pady=(10, 5))
        current_row += 1
        
        self.openai_key = tk.StringVar(value=self.existing_config.get('OPEN_AI_API_KEY', ''))
        openai_entry = ttk.Entry(main_frame, textvariable=self.openai_key, width=60, show='*')
        openai_entry.grid(row=current_row, column=0, columnspan=2, pady=(0, 5))
        current_row += 1
        
        ttk.Label(main_frame, text="OpenAI 웹사이트에서 발급받은 API 키를 입력하세요.",
                 foreground='gray', font=('Arial', 8)).grid(
            row=current_row, column=0, columnspan=2, sticky=tk.W)
        current_row += 1
        
        # Notion Token
        ttk.Label(main_frame, text="Notion Integration Token:", font=('Arial', 10, 'bold')).grid(
            row=current_row, column=0, sticky=tk.W, pady=(10, 5))
        current_row += 1
        
        self.notion_token = tk.StringVar(value=self.existing_config.get('NOTION_TOKEN', ''))
        notion_token_entry = ttk.Entry(main_frame, textvariable=self.notion_token, width=60, show='*')
        notion_token_entry.grid(row=current_row, column=0, columnspan=2, pady=(0, 5))
        current_row += 1
        
        ttk.Label(main_frame, text="Notion Integration에서 발급받은 토큰을 입력하세요.",
                 foreground='gray', font=('Arial', 8)).grid(
            row=current_row, column=0, columnspan=2, sticky=tk.W)
        current_row += 1
        
        # Notion Database ID
        ttk.Label(main_frame, text="Notion Database ID:", font=('Arial', 10, 'bold')).grid(
            row=current_row, column=0, sticky=tk.W, pady=(10, 5))
        current_row += 1
        
        self.notion_db_id = tk.StringVar(value=self.existing_config.get('NOTION_DATABASE_ID', ''))
        notion_db_entry = ttk.Entry(main_frame, textvariable=self.notion_db_id, width=60)
        notion_db_entry.grid(row=current_row, column=0, columnspan=2, pady=(0, 5))
        current_row += 1
        
        ttk.Label(main_frame, text="Notion 데이터베이스 URL에서 ID를 복사하세요.",
                 foreground='gray', font=('Arial', 8)).grid(
            row=current_row, column=0, columnspan=2, sticky=tk.W)
        current_row += 1
        
        # Watch Directory
        ttk.Label(main_frame, text="모니터링할 폴더:", font=('Arial', 10, 'bold')).grid(
            row=current_row, column=0, sticky=tk.W, pady=(10, 5))
        current_row += 1
        
        dir_frame = ttk.Frame(main_frame)
        dir_frame.grid(row=current_row, column=0, columnspan=2, pady=(0, 5))
        
        default_dir = self.existing_config.get('WATCH_DIR', 
                     f"C:\\Users\\{os.getlogin()}\\OneDrive\\사진\\카메라 앨범")
        self.watch_dir = tk.StringVar(value=default_dir)
        dir_entry = ttk.Entry(dir_frame, textvariable=self.watch_dir, width=50)
        dir_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        browse_btn = ttk.Button(dir_frame, text="찾아보기", command=self.browse_directory)
        browse_btn.pack(side=tk.LEFT)
        current_row += 1
        
        ttk.Label(main_frame, text="영수증 사진이 저장되는 OneDrive 폴더를 선택하세요.",
                 foreground='gray', font=('Arial', 8)).grid(
            row=current_row, column=0, columnspan=2, sticky=tk.W)
        current_row += 1
        
        # 구분선
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=current_row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=20)
        current_row += 1
        
        # 검증 설정
        ttk.Label(main_frame, text="검증 설정:", font=('Arial', 10, 'bold')).grid(
            row=current_row, column=0, sticky=tk.W, pady=(0, 10))
        current_row += 1
        
        self.enable_validation = tk.BooleanVar(
            value=self.existing_config.get('ENABLE_VALIDATION', 'true').lower() == 'true')
        ttk.Checkbutton(main_frame, text="데이터 검증 활성화", 
                       variable=self.enable_validation).grid(
            row=current_row, column=0, sticky=tk.W)
        current_row += 1
        
        self.enable_duplicate = tk.BooleanVar(
            value=self.existing_config.get('ENABLE_DUPLICATE_DETECTION', 'true').lower() == 'true')
        ttk.Checkbutton(main_frame, text="중복 검사 활성화", 
                       variable=self.enable_duplicate).grid(
            row=current_row, column=0, sticky=tk.W)
        current_row += 1
        
        self.enable_correction = tk.BooleanVar(
            value=self.existing_config.get('ENABLE_AUTO_CORRECTION', 'true').lower() == 'true')
        ttk.Checkbutton(main_frame, text="자동 오류 수정 활성화", 
                       variable=self.enable_correction).grid(
            row=current_row, column=0, sticky=tk.W)
        current_row += 1
        
        # 버튼
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=current_row, column=0, columnspan=2, pady=(30, 0))
        
        save_btn = ttk.Button(button_frame, text="저장 및 완료", command=self.save_config)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        test_btn = ttk.Button(button_frame, text="연결 테스트", command=self.test_connection)
        test_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(button_frame, text="취소", command=self.root.quit)
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def browse_directory(self):
        """폴더 선택 다이얼로그"""
        directory = filedialog.askdirectory(
            title="영수증 사진 폴더 선택",
            initialdir=self.watch_dir.get() if os.path.exists(self.watch_dir.get()) else os.path.expanduser("~")
        )
        if directory:
            self.watch_dir.set(directory)
    
    def validate_inputs(self):
        """입력값 검증"""
        if not self.openai_key.get().strip():
            messagebox.showerror("오류", "OpenAI API Key를 입력해주세요.")
            return False
        
        if not self.notion_token.get().strip():
            messagebox.showerror("오류", "Notion Token을 입력해주세요.")
            return False
        
        if not self.notion_db_id.get().strip():
            messagebox.showerror("오류", "Notion Database ID를 입력해주세요.")
            return False
        
        if not self.watch_dir.get().strip():
            messagebox.showerror("오류", "모니터링할 폴더를 선택해주세요.")
            return False
        
        if not os.path.exists(self.watch_dir.get()):
            result = messagebox.askyesno("경고", 
                f"선택한 폴더가 존재하지 않습니다:\n{self.watch_dir.get()}\n\n계속하시겠습니까?")
            if not result:
                return False
        
        return True
    
    def save_config(self):
        """설정을 .env 파일에 저장"""
        if not self.validate_inputs():
            return
        
        env_content = f"""# OpenAI API Key
OPEN_AI_API_KEY={self.openai_key.get().strip()}

# Notion credentials
NOTION_TOKEN={self.notion_token.get().strip()}
NOTION_DATABASE_ID={self.notion_db_id.get().strip()}

# Path to monitor
WATCH_DIR={self.watch_dir.get().strip()}

# Validation Settings
ENABLE_VALIDATION={str(self.enable_validation.get()).lower()}
ENABLE_DUPLICATE_DETECTION={str(self.enable_duplicate.get()).lower()}
ENABLE_AUTO_CORRECTION={str(self.enable_correction.get()).lower()}
"""
        
        try:
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            messagebox.showinfo("완료", 
                "설정이 저장되었습니다!\n\n이제 프로그램을 실행할 수 있습니다.")
            self.root.quit()
        except Exception as e:
            messagebox.showerror("오류", f"설정 저장 중 오류가 발생했습니다:\n{e}")
    
    def test_connection(self):
        """Notion 연결 테스트"""
        if not self.validate_inputs():
            return
        
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {self.notion_token.get().strip()}",
                "Notion-Version": "2022-06-28"
            }
            
            # 데이터베이스 조회 테스트
            url = f"https://api.notion.com/v1/databases/{self.notion_db_id.get().strip()}"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                messagebox.showinfo("성공", "Notion 연결에 성공했습니다!")
            else:
                messagebox.showerror("오류", 
                    f"Notion 연결 실패:\n{response.status_code} - {response.text}")
        except Exception as e:
            messagebox.showerror("오류", f"연결 테스트 중 오류 발생:\n{e}")

def main():
    root = tk.Tk()
    app = SetupWizard(root)
    root.mainloop()

if __name__ == "__main__":
    main()
