"""유틸리티 함수 모듈"""

from urllib.parse import urlparse


def extract_user_id(url_or_id: str) -> str:
    """
    URL 또는 사용자 ID에서 트위캐스트 사용자 ID를 추출합니다.

    Args:
        url_or_id: 트위캐스트 URL 또는 사용자 ID

    Returns:
        str: 사용자 ID

    Examples:
        >>> extract_user_id("https://twitcasting.tv/user123")
        'user123'
        >>> extract_user_id("user123")
        'user123'
    """
    url_or_id = url_or_id.strip()

    # URL인 경우 파싱
    if url_or_id.startswith("http://") or url_or_id.startswith("https://"):
        parsed = urlparse(url_or_id)
        path = parsed.path.strip("/")
        # 경로가 비어있지 않으면 첫 번째 세그먼트 반환
        if path:
            return path.split("/")[0]
        return ""

    # 이미 ID만 입력된 경우
    return url_or_id


def validate_paths(*paths: str) -> tuple[bool, str]:
    """
    파일 경로들이 유효한지 검증합니다.

    Args:
        *paths: 검증할 경로들

    Returns:
        tuple[bool, str]: (유효 여부, 오류 메시지)
    """
    from pathlib import Path

    for path in paths:
        if not path or not path.strip():
            return False, "경로가 비어있습니다."

        path_obj = Path(path)
        if not path_obj.exists():
            return False, f"파일을 찾을 수 없습니다: {path}"

        if not path_obj.is_file():
            return False, f"파일이 아닙니다: {path}"

    return True, ""
