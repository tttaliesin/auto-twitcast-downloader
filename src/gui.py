"""트위캐스트 감시 프로그램 GUI 모듈 - 채널별 독립 제어"""

import asyncio
import threading
from pathlib import Path
from tkinter import filedialog
import pystray
from PIL import Image, ImageDraw

import customtkinter as ctk

from .recorder import StreamRecorder
from .stream_checker import check_stream_status
from .utils import extract_user_id
from .config import ConfigManager


class ChannelMonitor(ctk.CTkFrame):
    """개별 채널 감시 UI 컴포넌트"""

    def __init__(self, parent, channel_num: int, gui_instance):
        super().__init__(parent)
        self.channel_num = channel_num
        self.gui = gui_instance

        # 상태 변수
        self.is_monitoring = False
        self.was_live = False
        self.monitoring_thread = None
        self.user_id = None
        
        self.configure(fg_color=self.gui.colors["navy"])

        self.init_ui()

    def init_ui(self):
        """채널 UI 초기화"""
        # 채널 번호 표시
        header = ctk.CTkFrame(
            self, 
            fg_color="transparent",
        )
        header.pack(fill="x", padx=10, pady=(10, 5))

        channel_label = ctk.CTkLabel(
            header,
            text=f"채널 {self.channel_num}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.gui.colors["pale_lavender"]
        )
        channel_label.pack(side="left")

        self.status_label = ctk.CTkLabel(
            header,
            text="⚫ 대기",
            font=ctk.CTkFont(size=11),
            text_color="#95a5a6"
        )
        self.status_label.pack(side="right")

        # URL 입력
        url_row = ctk.CTkFrame(self, fg_color="transparent")
        url_row.pack(fill="x", padx=10, pady=(0, 5))

        self.url_input = ctk.CTkEntry(
            url_row,
            placeholder_text="URL 또는 ID 입력",
            height=28,
            font=ctk.CTkFont(size=10)
        )
        self.url_input.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # 시작/중지 버튼
        self.toggle_button = ctk.CTkButton(
            url_row,
            text="시작",
            command=self.toggle_monitoring,
            width=60,
            height=28,
            font=ctk.CTkFont(size=10),
            text_color=self.gui.colors["charcoal"],
            
            fg_color=self.gui.colors["lavender"],
            hover_color=self.gui.colors["pale_lavender"],
        )
        self.toggle_button.pack(side="right")

        # 구분선
        separator = ctk.CTkFrame(self, height=1, fg_color=self.gui.colors["pale_lavender"])
        separator.pack(fill="x", padx=5, pady=(5, 0))

    def toggle_monitoring(self):
        """감시 시작/중지"""
        if not self.is_monitoring:
            self.start_monitoring()
        else:
            self.stop_monitoring()

    def start_monitoring(self):
        """감시 시작"""
        url_or_id = self.url_input.get().strip()
        if not url_or_id:
            self.gui.log_message(f"[채널{self.channel_num}] ❌ URL을 입력해주세요.")
            return

        user_id = extract_user_id(url_or_id)
        if not user_id:
            self.gui.log_message(f"[채널{self.channel_num}] ❌ 올바른 URL이 아닙니다.")
            return

        self.user_id = user_id
        self.is_monitoring = True
        self.was_live = False

        # UI 업데이트
        self.url_input.configure(state="disabled")
        self.toggle_button.configure(text="중지", fg_color=self.gui.colors["soft_pink"], hover_color="#FF8FB8")
        self.status_label.configure(text="⏳ 확인 중...", text_color=self.gui.colors["lavender"])

        self.gui.log_message(f"[채널{self.channel_num}] ✅ {user_id} 감시 시작")

        # 감시 스레드 시작
        self.monitoring_thread = threading.Thread(
            target=self.run_monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()

    def stop_monitoring(self):
        """감시 중지"""
        self.is_monitoring = False

        # 녹화 중이면 중지
        if self.user_id and self.gui.recorder.is_recording(self.user_id):
            self.gui.recorder.stop_recording(self.user_id)
            self.gui.log_message(f"[채널{self.channel_num}] ⏹️  {self.user_id} 녹화 중지")

        # UI 업데이트
        self.url_input.configure(state="normal")
        self.toggle_button.configure(text="시작", fg_color=self.gui.colors["deep_purple"], hover_color=self.gui.colors["lavender"])
        self.status_label.configure(text="⚫ 대기", text_color="#95a5a6")

        self.gui.log_message(f"[채널{self.channel_num}] ⏹️  {self.user_id} 감시 중지")
        self.user_id = None

    def run_monitoring_loop(self):
        """백그라운드 감시 루프"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self.monitor_stream())
        except Exception as e:
            self.gui.after(0, lambda: self.gui.log_message(
                f"[채널{self.channel_num}] ❌ 오류: {e}"
            ))
        finally:
            loop.close()

    async def monitor_stream(self):
        """스트림 감시"""
        ytdlp_path = self.gui.ytdlp_path_input.get().strip()

        if not ytdlp_path:
            self.gui.after(0, lambda: self.gui.log_message(
                f"[채널{self.channel_num}] ❌ yt-dlp 경로를 설정해주세요."
            ))
            self.gui.after(0, self.stop_monitoring)
            return

        check_interval = self.gui.get_check_interval()

        while self.is_monitoring:
            status = await check_stream_status(self.user_id, ytdlp_path)
            timestamp = status["checked_at"].strftime("%H:%M:%S")

            if "error" in status:
                self.gui.after(0, lambda t=timestamp, err=status['error']:
                    self.gui.log_message(f"[{t}] [채널{self.channel_num}] ⚠️  {err}"))
            elif status["is_live"]:
                if not self.was_live:
                    # 방송 시작
                    self.gui.after(0, lambda t=timestamp:
                        self.gui.log_message(f"\n🔴 [{t}] [채널{self.channel_num}] {self.user_id} 방송 시작!"))

                    if status["title"]:
                        self.gui.after(0, lambda title=status['title']:
                            self.gui.log_message(f"   📺 제목: {title}"))

                    self.gui.after(0, lambda:
                        self.status_label.configure(text="🔴 방송 중", text_color="#e74c3c"))

                    self.was_live = True

                    # 자동 녹화
                    if self.gui.auto_record_var.get():
                        self.gui.start_recording(self.user_id, self.channel_num)
                else:
                    # 방송 중
                    self.gui.after(0, lambda t=timestamp:
                        self.gui.log_message(f"[{t}] [채널{self.channel_num}] 🔴 방송 중"))
            else:
                if self.was_live:
                    # 방송 종료
                    self.gui.after(0, lambda t=timestamp:
                        self.gui.log_message(f"\n⚫ [{t}] [채널{self.channel_num}] {self.user_id} 방송 종료"))

                    self.gui.after(0, lambda:
                        self.status_label.configure(text="⚫ 종료", text_color="#95a5a6"))

                    self.was_live = False

                    # 녹화 중지
                    if self.gui.recorder.is_recording(self.user_id):
                        self.gui.recorder.stop_recording(self.user_id)
                        self.gui.log_message(f"[채널{self.channel_num}] ⏹️  {self.user_id} 녹화 중지")
                else:
                    # 대기 중
                    self.gui.after(0, lambda t=timestamp:
                        self.gui.log_message(f"[{t}] [채널{self.channel_num}] ⏳ 대기 중"))
                    self.gui.after(0, lambda:
                        self.status_label.configure(text="⏳ 대기 중", text_color="#3498db"))

            await asyncio.sleep(check_interval)


class TwitCastingMonitorGUI(ctk.CTk):
    """트위캐스트 방송 감시 GUI - 채널별 독립 제어"""

    def __init__(self):
        super().__init__()

        # 윈도우 설정
        self.title("트위캐스트 자동녹화")
        self.geometry("1100x750")
        self.resizable(False, False)  # 크기 조절 불가

        # 설정 관리자
        self.config = ConfigManager()

        # 녹화 관리
        self.recorder = StreamRecorder()
        self.recorder.set_output_callback(self.on_recording_output)

        # 로그 토글 상태
        self.log_visible = True

        # 트레이 아이콘
        self.tray_icon = None

        # UI 초기화
        self.init_ui()

        # 설정 불러오기
        self.load_settings()

        # 자동 저장 바인딩
        self.bind_auto_save()

        # 윈도우 닫기 (트레이로 숨김)
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

    def create_tray_icon(self):
        """트레이 아이콘 생성"""
        # 간단한 아이콘 이미지 생성
        image = Image.new('RGB', (64, 64), color='#1f538d')
        draw = ImageDraw.Draw(image)
        draw.ellipse([16, 16, 48, 48], fill='#3498db')

        # 메뉴 생성
        menu = pystray.Menu(
            pystray.MenuItem("열기", self.show_from_tray),
            pystray.MenuItem("완전 종료", self.quit_app)
        )

        # 트레이 아이콘 생성
        self.tray_icon = pystray.Icon(
            "TwitCasting Monitor",
            image,
            "트위캐스트 자동녹화",
            menu
        )

    def hide_to_tray(self):
        """트레이로 숨기기"""
        self.withdraw()  # 윈도우 숨김

        if self.tray_icon is None:
            self.create_tray_icon()
            # 트레이 아이콘을 별도 스레드에서 실행
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_from_tray(self):
        """트레이에서 복원"""
        self.after(0, self.deiconify)  # 윈도우 표시

    def quit_app(self):
        """완전 종료"""
        self.save_settings()

        # 모든 채널 중지
        for monitor in self.channel_monitors:
            if monitor.is_monitoring:
                monitor.is_monitoring = False

        # 모든 녹화 중지
        self.recorder.stop_all_recordings()

        # 트레이 아이콘 종료
        if self.tray_icon:
            self.tray_icon.stop()

        self.quit()

    def init_ui(self):
        """UI 초기화"""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # 커스텀 컬러 팔레트 - UI 가이드 적용
        self.colors = {
            # 주요 색상
            "lavender": "#B8A9E6",      # 메인 브랜드 컬러
            "soft_pink": "#FFB3D9",      # 액센트 핑크
            "navy": "#2B3A67",           # 텍스트 본문
            # 보조 색상
            "white": "#FFFFFF",          # 배경, 카드
            "light_gray": "#E8E9F3",     # UI 배경
            "charcoal": "#3C3C3C",       # 텍스트 제목
            # 액센트 색상
            "pale_lavender": "#E6DFFF",  # 호버 효과
            "deep_purple": "#7B68EE",    # CTA 버튼
            "baby_pink": "#FFE5F1",      # 알림, 배지
        }

        # 메인 윈도우 배경 - 라이트 그레이
        self.configure(fg_color=self.colors["deep_purple"])

        # 메인 컨테이너
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # 좌우 분할 레이아웃
        # 왼쪽: 설정 및 채널 (고정 너비)
        left_frame = ctk.CTkFrame(main_container, fg_color=self.colors["lavender"], corner_radius=15, border_width=0)
        left_frame.pack(side="left", fill="both", padx=(0, 5))

        # 오른쪽: 로그 (확장)
        self.right_frame = ctk.CTkFrame(main_container, fg_color=self.colors["lavender"], corner_radius=15, border_width=0)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # === 왼쪽 영역 ===
        # 제목
        title_label = ctk.CTkLabel(
            left_frame,
            text="🎥 트위캐스트 자동녹화",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors["charcoal"]
        )
        title_label.pack(pady=(10, 10))

        # 공통 설정
        settings_frame = ctk.CTkFrame(
            left_frame, 
            fg_color=self.colors["deep_purple"], 
            border_color=self.colors["pale_lavender"], 
            border_width=0, 
            corner_radius=10
        )
        settings_frame.pack(fill="x", padx=10, pady=(0, 8))

        settings_title = ctk.CTkLabel(
            settings_frame,
            text="공통 설정",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.colors["pale_lavender"]
        )
        settings_title.pack(anchor="w", padx=8, pady=(8, 5))

        # 확인 주기 + 자동 녹화 (같은 줄)
        interval_auto_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
        interval_auto_row.pack(fill="x", padx=8, pady=(0, 4))

        # 확인 주기
        ctk.CTkLabel(
            interval_auto_row,
            text="주기:",
            font=ctk.CTkFont(size=10),
            width=40
        ).pack(side="left", padx=(0, 3))

        self.interval_input = ctk.CTkEntry(
            interval_auto_row,
            placeholder_text="60",
            height=26,
            width=45,
            font=ctk.CTkFont(size=10)
        )
        self.interval_input.insert(0, "60")
        self.interval_input.pack(side="left")

        ctk.CTkLabel(
            interval_auto_row,
            text="초",
            font=ctk.CTkFont(size=10)
        ).pack(side="left", padx=(2, 10))

        # 자동 녹화
        self.auto_record_var = ctk.BooleanVar(value=False)
        self.auto_record_checkbox = ctk.CTkCheckBox(
            interval_auto_row,
            text="자동녹화",
            variable=self.auto_record_var,
            font=ctk.CTkFont(size=10)
        )
        self.auto_record_checkbox.pack(side="left")

        # yt-dlp 경로
        ytdlp_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
        ytdlp_row.pack(fill="x", padx=8, pady=(0, 4))

        ctk.CTkLabel(
            ytdlp_row,
            text="yt-dlp",
            font=ctk.CTkFont(size=9),
            width=50,
            anchor="w"
        ).pack(side="left", padx=(0, 3))

        self.ytdlp_path_input = ctk.CTkEntry(
            ytdlp_row,
            placeholder_text="C:\\ffmpeg\\bin\\yt-dlp.exe",
            height=24,
            font=ctk.CTkFont(size=8)
        )
        self.ytdlp_path_input.pack(side="left", fill="x", expand=True, padx=(0, 3))

        ctk.CTkButton(
            ytdlp_row,
            text="찾기",
            command=self.browse_ytdlp,
            width=45,
            height=24,
            font=ctk.CTkFont(size=9),
            fg_color=self.colors["navy"]
        ).pack(side="right")

        # ffmpeg 경로
        ffmpeg_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
        ffmpeg_row.pack(fill="x", padx=8, pady=(0, 4))

        ctk.CTkLabel(
            ffmpeg_row,
            text="ffmpeg",
            font=ctk.CTkFont(size=9),
            width=50,
            anchor="w"
        ).pack(side="left", padx=(0, 3))

        self.ffmpeg_path_input = ctk.CTkEntry(
            ffmpeg_row,
            placeholder_text="C:\\ffmpeg\\bin\\ffmpeg.exe",
            height=24,
            font=ctk.CTkFont(size=8)
        )
        self.ffmpeg_path_input.pack(side="left", fill="x", expand=True, padx=(0, 3))

        ctk.CTkButton(
            ffmpeg_row,
            text="찾기",
            command=self.browse_ffmpeg,
            width=45,
            height=24,
            font=ctk.CTkFont(size=9),
            fg_color=self.colors["navy"]
        ).pack(side="right")

        # 저장 경로
        save_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
        save_row.pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkLabel(
            save_row,
            text="저장",
            font=ctk.CTkFont(size=9),
            width=50,
            anchor="w"
        ).pack(side="left", padx=(0, 3))

        self.save_path_input = ctk.CTkEntry(
            save_row,
            placeholder_text="C:\\Downloads",
            height=24,
            font=ctk.CTkFont(size=8)
        )
        self.save_path_input.pack(side="left", fill="x", expand=True, padx=(0, 3))

        ctk.CTkButton(
            save_row,
            text="찾기",
            command=self.browse_save_path,
            width=45,
            height=24,
            font=ctk.CTkFont(size=9),
            fg_color=self.colors["navy"]
        ).pack(side="right")

        # 채널 모니터링 영역
        channels_frame = ctk.CTkFrame(
            left_frame, 
            fg_color=self.colors["deep_purple"], 
            border_color=self.colors["pale_lavender"], 
            border_width=1, 
            corner_radius=10
        )
        channels_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        channels_title = ctk.CTkLabel(
            channels_frame,
            text="채널 감시",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.colors["pale_lavender"]
        )
        channels_title.pack(anchor="w", padx=8, pady=(8, 5))

        # 4개의 채널 모니터 생성
        self.channel_monitors = []
        for i in range(1, 5):
            monitor = ChannelMonitor(channels_frame, i, self)
            monitor.pack(fill="x", padx=5, pady=(0, 3))
            self.channel_monitors.append(monitor)

        # 버튼 영역
        button_frame = ctk.CTkFrame(
            left_frame,
            fg_color=self.colors["deep_purple"], 
            border_color=self.colors["pale_lavender"], 
        )
        button_frame.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkButton(
            button_frame,
            text="모두 시작",
            command=self.start_all,
            height=32,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.colors["pale_lavender"],
            fg_color=self.colors["navy"],
            hover_color="#3d4f7a",
            border_color=self.colors["pale_lavender"],
            border_width=1,
        ).pack(side="left", fill="x", expand=True, padx=(5, 3), pady=5)

        ctk.CTkButton(
            button_frame,
            text="모두 중지",
            command=self.stop_all,
            height=32,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.colors["pale_lavender"],
            fg_color=self.colors["navy"],
            hover_color="#3d4f7a",
            border_color=self.colors["pale_lavender"],
            border_width=1,
        ).pack(side="left", fill="x", expand=True, padx=(3, 3), pady=5)

        ctk.CTkButton(
            button_frame,
            text="로그 지우기",
            command=self.clear_log,
            height=32,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.colors["pale_lavender"],
            fg_color=self.colors["navy"],
            hover_color="#3d4f7a",
            border_color=self.colors["pale_lavender"],
            border_width=1
        ).pack(side="right", fill="x", expand=True, padx=(3, 5), pady=5)

        # 로그 토글 버튼 (왼쪽 하단)
        self.toggle_log_button = ctk.CTkButton(
            left_frame,
            text="◀ 로그 숨기기",
            command=self.toggle_log,
            height=32,
            font=ctk.CTkFont(size=11),
            text_color=self.colors["pale_lavender"],
            fg_color=self.colors["navy"], 
            hover_color=self.colors["deep_purple"],
        )
        self.toggle_log_button.pack(fill="x", padx=10, pady=(0, 10))

        # === 오른쪽 영역 (로그) ===
        log_header = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=5, pady=(5, 5))

        log_title = ctk.CTkLabel(
            log_header,
            text="로그",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors["charcoal"]
        )
        log_title.pack(side="left")

        # 로그 출력 영역
        self.log_output = ctk.CTkTextbox(
            self.right_frame,
            font=ctk.CTkFont(family="Consolas", size=9),
            wrap="word"
        )
        self.log_output.pack(fill="both", expand=True, padx=5, pady=(0, 5))

    def toggle_log(self):
        """로그 영역 토글"""
        if self.log_visible:
            # 로그 숨기기
            self.right_frame.pack_forget()
            self.toggle_log_button.configure(text="▶ 로그 보기")
            self.log_visible = False
            self.geometry("500x750")
        else:
            # 로그 보이기
            self.right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
            self.toggle_log_button.configure(text="◀ 로그 숨기기")
            self.log_visible = True
            self.geometry("1100x750")

    def get_check_interval(self) -> int:
        """확인 주기 가져오기"""
        try:
            interval = int(self.interval_input.get())
            return max(10, interval)  # 최소 10초
        except:
            return 60  # 기본값

    def start_all(self):
        """모든 채널 시작"""
        for monitor in self.channel_monitors:
            if not monitor.is_monitoring and monitor.url_input.get().strip():
                monitor.start_monitoring()

    def stop_all(self):
        """모든 채널 중지"""
        for monitor in self.channel_monitors:
            if monitor.is_monitoring:
                monitor.stop_monitoring()

    def log_message(self, message: str):
        """로그 메시지 추가"""
        self.log_output.insert("end", message + "\n")
        self.log_output.see("end")

    def clear_log(self):
        """로그 지우기"""
        self.log_output.delete("1.0", "end")

    def browse_ytdlp(self):
        """yt-dlp 파일 선택"""
        filename = filedialog.askopenfilename(
            title="yt-dlp 실행 파일 선택",
            filetypes=[("실행 파일", "*.exe"), ("모든 파일", "*.*")]
        )
        if filename:
            self.ytdlp_path_input.delete(0, "end")
            self.ytdlp_path_input.insert(0, filename)

    def browse_ffmpeg(self):
        """ffmpeg 파일 선택"""
        filename = filedialog.askopenfilename(
            title="ffmpeg 실행 파일 선택",
            filetypes=[("실행 파일", "*.exe"), ("모든 파일", "*.*")]
        )
        if filename:
            self.ffmpeg_path_input.delete(0, "end")
            self.ffmpeg_path_input.insert(0, filename)

    def browse_save_path(self):
        """저장 경로 선택"""
        dirname = filedialog.askdirectory(title="저장 경로 선택")
        if dirname:
            self.save_path_input.delete(0, "end")
            self.save_path_input.insert(0, dirname)

    def start_recording(self, user_id: str, channel_num: int):
        """녹화 시작"""
        ytdlp_path = self.ytdlp_path_input.get().strip()
        ffmpeg_path = self.ffmpeg_path_input.get().strip()
        save_path = self.save_path_input.get().strip()

        if not ytdlp_path or not Path(ytdlp_path).exists():
            self.log_message(f"[채널{channel_num}] ⚠️  yt-dlp 경로가 올바르지 않습니다.")
            return

        if not ffmpeg_path or not Path(ffmpeg_path).exists():
            self.log_message(f"[채널{channel_num}] ⚠️  ffmpeg 경로가 올바르지 않습니다.")
            return

        success, message = self.recorder.start_recording(
            user_id=user_id,
            ytdlp_path=ytdlp_path,
            ffmpeg_path=ffmpeg_path,
            save_path=save_path or None
        )

        if success:
            self.log_message(f"[채널{channel_num}] 🎬 {message}")
        else:
            self.log_message(f"[채널{channel_num}] ❌ {message}")

    def on_recording_output(self, user_id: str, line: str):
        """녹화 출력 콜백"""
        self.after(0, lambda: self.log_message(f"[yt-dlp][{user_id}] {line}"))

    def load_settings(self):
        """설정 불러오기"""
        # 공통 설정
        interval = self.config.get("check_interval", "60")
        self.interval_input.delete(0, "end")
        self.interval_input.insert(0, str(interval))

        auto_record = self.config.get("auto_record", False)
        self.auto_record_var.set(auto_record)

        ytdlp_path = self.config.get("ytdlp_path", "")
        if ytdlp_path:
            self.ytdlp_path_input.delete(0, "end")
            self.ytdlp_path_input.insert(0, ytdlp_path)

        ffmpeg_path = self.config.get("ffmpeg_path", "")
        if ffmpeg_path:
            self.ffmpeg_path_input.delete(0, "end")
            self.ffmpeg_path_input.insert(0, ffmpeg_path)

        save_path = self.config.get("save_path", "")
        if save_path:
            self.save_path_input.delete(0, "end")
            self.save_path_input.insert(0, save_path)

        # 채널별 URL
        urls = self.config.get("channel_urls", ["", "", "", ""])
        for i, url in enumerate(urls[:4]):
            if url and i < len(self.channel_monitors):
                self.channel_monitors[i].url_input.delete(0, "end")
                self.channel_monitors[i].url_input.insert(0, url)

    def bind_auto_save(self):
        """자동 저장 바인딩"""
        self.interval_input.bind("<FocusOut>", lambda e: self.save_settings())
        self.ytdlp_path_input.bind("<FocusOut>", lambda e: self.save_settings())
        self.ffmpeg_path_input.bind("<FocusOut>", lambda e: self.save_settings())
        self.save_path_input.bind("<FocusOut>", lambda e: self.save_settings())

        for monitor in self.channel_monitors:
            monitor.url_input.bind("<FocusOut>", lambda e: self.save_settings())

        self.auto_record_var.trace_add("write", lambda *args: self.save_settings())

    def save_settings(self):
        """설정 저장"""
        channel_urls = [monitor.url_input.get().strip() for monitor in self.channel_monitors]

        self.config.update({
            "check_interval": self.interval_input.get().strip(),
            "auto_record": self.auto_record_var.get(),
            "ytdlp_path": self.ytdlp_path_input.get().strip(),
            "ffmpeg_path": self.ffmpeg_path_input.get().strip(),
            "save_path": self.save_path_input.get().strip(),
            "channel_urls": channel_urls
        })
        self.config.save_config()
