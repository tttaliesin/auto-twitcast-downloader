"""트위캐스트 스트림 녹화 관리 모듈"""

import subprocess
import sys
import threading
from pathlib import Path


class StreamRecorder:
    """스트림 녹화 관리 클래스 - 다중 채널 지원"""

    def __init__(self):
        self.processes = {}  # {user_id: process}
        self.output_callback = None

    def set_output_callback(self, callback):
        """출력 콜백 함수를 설정합니다."""
        self.output_callback = callback

    def _read_output(self, user_id: str):
        """프로세스 출력을 읽어서 콜백으로 전달합니다."""
        process = self.processes.get(user_id)
        if process and process.stdout:
            for line in iter(process.stdout.readline, b''):
                if line and user_id in self.processes:  # 프로세스가 아직 관리 중인지 확인
                    decoded_line = line.decode('utf-8', errors='ignore').strip()
                    if decoded_line and self.output_callback:
                        self.output_callback(user_id, decoded_line)

    def start_recording(
        self,
        user_id: str,
        ytdlp_path: str,
        ffmpeg_path: str,
        save_path: str = None
    ) -> tuple[bool, str]:
        """
        녹화를 시작합니다.

        Args:
            user_id: 트위캐스트 사용자 ID
            ytdlp_path: yt-dlp 실행 파일 경로
            ffmpeg_path: ffmpeg 실행 파일 경로
            save_path: 저장 경로 (None이면 현재 디렉토리)

        Returns:
            tuple[bool, str]: (성공 여부, 메시지)
        """
        if user_id in self.processes:
            return False, f"{user_id}: 이미 녹화가 진행 중입니다."

        # 저장 경로 설정
        if not save_path:
            save_path = str(Path.cwd())

        save_dir = Path(save_path)
        save_dir.mkdir(parents=True, exist_ok=True)

        # yt-dlp 출력 템플릿 설정
        # 형식: 채널명/[날짜]_제목(ID)/[날짜]_제목(ID).확장자
        output_template = str(save_dir / user_id / "[%(upload_date)s]_%(title)s(%(id)s)/[%(upload_date)s]_%(title)s(%(id)s).mp4")

        # yt-dlp 명령어 구성
        url = f"https://twitcasting.tv/{user_id}"
        cmd = [
            ytdlp_path,
            "-v",  # verbose
            "-c",  # continue (resume)
            "--no-part",  # .part 확장자 사용 안 함
            "--ffmpeg-location", ffmpeg_path,
            "--restrict-filenames",
            "-o", output_template,
            "--embed-thumbnail",
            "--merge-output-format", "mp4",
            url
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                bufsize=1,  # 줄 단위 버퍼링
                universal_newlines=False
            )

            self.processes[user_id] = process

            # 출력 읽기 스레드 시작
            output_thread = threading.Thread(target=self._read_output, args=(user_id,), daemon=True)
            output_thread.start()

            return True, f"녹화 시작: {user_id}"

        except Exception as e:
            if user_id in self.processes:
                del self.processes[user_id]
            return False, f"녹화 시작 오류: {e}"

    def stop_recording(self, user_id: str) -> tuple[bool, str]:
        """
        특정 채널의 녹화를 중지합니다.

        Args:
            user_id: 트위캐스트 사용자 ID

        Returns:
            tuple[bool, str]: (성공 여부, 메시지)
        """
        if user_id not in self.processes:
            return False, f"{user_id}: 진행 중인 녹화가 없습니다."

        process = self.processes[user_id]

        try:
            if sys.platform == "win32":
                import signal
                # 먼저 CTRL+C 시그널 전송 (정상 종료 시도)
                try:
                    process.send_signal(signal.CTRL_C_EVENT)
                except:
                    pass

                # 2초 대기
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # 여전히 살아있으면 강제 종료
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
            else:
                # Unix-like 시스템
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

            return True, f"{user_id}: 녹화 중지"

        except Exception as e:
            return False, f"{user_id}: 녹화 중지 오류: {e}"
        finally:
            if user_id in self.processes:
                del self.processes[user_id]

    def stop_all_recordings(self):
        """모든 녹화를 중지합니다."""
        user_ids = list(self.processes.keys())
        for user_id in user_ids:
            self.stop_recording(user_id)

    def is_recording(self, user_id: str) -> bool:
        """특정 채널이 녹화 중인지 확인합니다."""
        return user_id in self.processes

    def get_recording_channels(self) -> list[str]:
        """현재 녹화 중인 채널 목록을 반환합니다."""
        return list(self.processes.keys())