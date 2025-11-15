# 트위캐스트 자동 녹화 프로그램

트위캐스트 스트림 모니터링 및 자동 녹화 애플리케이션

## 기능

- 4채널 동시 모니터링
- 방송 시작 시 자동 녹화
- yt-dlp 기반 실시간 스트림 상태 감지
- 시스템 트레이 지원
- 설정 자동 저장
- 채널별 독립 제어

## 필수 요구사항

- Python 3.13 이상
- uv 패키지 매니저
- yt-dlp 실행 파일
- ffmpeg 실행 파일

## 설치

```bash
uv sync
```

## 실행 방법

### 소스코드 실행

```bash
uv run python main.py
```

### 실행 파일 빌드

```bash
build.bat
```

빌드 결과: `dist\TwitCastingMonitor.exe`

실행 파일은 단독 실행 가능하며 외부 의존성이 필요하지 않음.

## 설정

### 공통 설정
- **확인 주기**: 스트림 상태 확인 주기(초 단위, 최소 10초)
- **자동 녹화**: 방송 시작 시 자동 녹화 활성화
- **yt-dlp 경로**: yt-dlp 실행 파일 경로
- **ffmpeg 경로**: ffmpeg 실행 파일 경로
- **저장 경로**: 녹화 파일 저장 디렉토리

### 채널 설정
4개 채널 각각 지원:
- 트위캐스트 URL 또는 사용자 ID 입력
- 개별 시작/중지 제어
- 독립적인 상태 모니터링

### 녹화 파일 저장 형식
```
{저장경로}/{사용자ID}/[{날짜}]_{제목}({ID})/[{날짜}]_{제목}({ID}).mp4
```

## 아키텍처

```
src/
├── gui.py              # GUI 구현 (customtkinter)
├── stream_checker.py   # 스트림 상태 감지 (yt-dlp)
├── recorder.py         # 녹화 관리 (subprocess)
├── config.py           # 설정 저장
└── utils.py            # 유틸리티 함수
```

## 컨트롤

- **모두 시작**: URL이 설정된 모든 채널 모니터링 시작
- **모두 중지**: 활성화된 모든 모니터링 세션 중지
- **로그 지우기**: 로그 출력 삭제
- **로그 숨기기/보기**: 로그 패널 토글

## 기술 상세

- **GUI 프레임워크**: customtkinter
- **스트림 감지**: yt-dlp JSON 메타데이터 추출
- **녹화**: yt-dlp (ffmpeg 백엔드)
- **비동기 처리**: asyncio (논블로킹 스트림 체크)
- **프로세스 관리**: subprocess (시그널 핸들링)
- **빌드 도구**: PyInstaller (단일 실행 파일)

## 설정 파일

애플리케이션 디렉토리의 `config.json`에 자동 저장:
```json
{
  "check_interval": "60",
  "auto_record": false,
  "ytdlp_path": "C:\\path\\to\\yt-dlp.exe",
  "ffmpeg_path": "C:\\path\\to\\ffmpeg.exe",
  "save_path": "C:\\Downloads",
  "channel_urls": ["user1", "user2", "", ""]
}
```

## yt-dlp 명령어

녹화 시 실행되는 명령어:
```bash
yt-dlp -v -c --no-part \
  --ffmpeg-location {ffmpeg_path} \
  -o {output_template} \
  --embed-thumbnail \
  --merge-output-format mp4 \
  https://twitcasting.tv/{user_id}
```

## 참고사항

- 최소 확인 주기: 10초
- 각 채널은 독립적으로 동작
- 창 닫기 시 시스템 트레이로 최소화
- 완전 종료는 트레이 메뉴의 "완전 종료" 사용

## 메모리 관리

장시간 실행 시 메모리 누수 방지를 위한 구현:

### 로그 제한
- 로그 출력은 최대 1000줄까지 자동 유지
- 초과 시 오래된 로그부터 자동 삭제

### 스레드 관리
- 모니터링 중지 시 스레드 참조 자동 정리
- 반복 시작/중지 시에도 메모리 누적 방지

### 프로세스 관리
- 녹화 중지 시 subprocess 완전 종료 보장
- zombie 프로세스 방지 (Windows: taskkill 후 wait 호출)
- 프로세스 및 출력 스레드 참조 정리

### asyncio 이벤트 루프
- 모니터링 스레드 종료 시 이벤트 루프 참조 정리
- 멀티스레드 환경에서 루프 누수 방지

## 라이센스

MIT License