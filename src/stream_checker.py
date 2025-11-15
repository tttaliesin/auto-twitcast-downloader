"""트위캐스트 스트림 상태 확인 모듈"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime


async def check_stream_status(user_id: str, ytdlp_path: str = None) -> dict:
    """
    yt-dlp를 사용하여 트위캐스트 방송 상태를 확인합니다.

    Args:
        user_id: 트위캐스트 사용자 ID (URL의 마지막 부분)
        ytdlp_path: yt-dlp 실행 파일 경로 (None이면 'yt-dlp' 명령어 사용)

    Returns:
        dict: {"is_live": bool, "title": str | None, "checked_at": datetime}
    """
    url = f"https://twitcasting.tv/{user_id}"
    ytdlp_cmd = ytdlp_path if ytdlp_path else "yt-dlp"

    try:
        # yt-dlp로 방송 정보 가져오기 (JSON 형식)
        # --skip-download: 다운로드하지 않음
        # --dump-single-json: JSON 형식으로 정보만 출력
        # --no-warnings: 경고 메시지 숨김
        cmd = [
            ytdlp_cmd,
            "--skip-download",
            "--dump-single-json",
            "--no-warnings",
            url
        ]

        # 비동기 subprocess 실행
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=15.0  # 15초 타임아웃
        )

        if process.returncode == 0 and stdout:
            # JSON 파싱
            data = json.loads(stdout.decode("utf-8"))

            # is_live 필드 확인 (트위캐스트는 라이브가 아니면 오류 발생)
            is_live = data.get("is_live", True)  # 성공적으로 가져왔다면 라이브 중
            title = data.get("title") or data.get("fulltitle")

            return {
                "is_live": is_live,
                "title": title,
                "checked_at": datetime.now()
            }
        else:
            # 방송이 없거나 오류 발생
            error_msg = stderr.decode("utf-8", errors="ignore").strip() if stderr else ""

            # 일반적인 "방송 없음" 오류는 정상 상태로 처리
            if "no video formats found" in error_msg.lower() or "not currently live" in error_msg.lower():
                return {
                    "is_live": False,
                    "title": None,
                    "checked_at": datetime.now()
                }

            return {
                "is_live": False,
                "title": None,
                "checked_at": datetime.now(),
                "error": error_msg or f"exit code {process.returncode}"
            }

    except asyncio.TimeoutError:
        return {
            "is_live": False,
            "title": None,
            "checked_at": datetime.now(),
            "error": "Timeout (15s)"
        }
    except json.JSONDecodeError as e:
        return {
            "is_live": False,
            "title": None,
            "checked_at": datetime.now(),
            "error": f"JSON parse error: {e}"
        }
    except Exception as e:
        return {
            "is_live": False,
            "title": None,
            "checked_at": datetime.now(),
            "error": str(e)
        }