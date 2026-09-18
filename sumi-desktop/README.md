# SUMI 데스크톱 (Windows)

`https://smc12.synology.me:9443/` 의 SUMI(스미) 업무 에이전트를 브라우저 없이 **윈도우 프로그램(.exe)** 으로 쓰기 위한 Electron 앱입니다. 시작 메뉴/바탕화면 아이콘에서 바로 실행되고, 주소창·탭 없이 전용 창으로 열립니다.

> 웹 서비스 자체는 그대로 사용합니다. 이 폴더는 서버 코드를 바꾸지 않는 **클라이언트 껍데기(wrapper)** 입니다.

## exe 받는 방법

### 1) GitHub Actions에서 내려받기 (권장, 윈도우 PC 없이도 가능)

1. GitHub 저장소 → **Actions** → **SUMI Desktop (Windows exe)** 워크플로 선택
2. 최신 실행 결과(또는 **Run workflow** 로 직접 실행) 클릭
3. 하단 **Artifacts → `SUMI-windows-exe`** 다운로드 후 압축 해제
   - `SUMI-1.0.0-setup.exe` — 설치 파일 (시작 메뉴·바탕화면 바로가기 생성)
   - `SUMI-1.0.0-portable.exe` — 설치 없이 바로 실행되는 단일 실행 파일 (USB 사용 가능)

### 2) 윈도우 PC에서 직접 빌드

[Node.js 22 이상](https://nodejs.org/) 설치 후:

```powershell
cd sumi-desktop
npm ci
npm run build:win
```

`sumi-desktop\release\` 폴더에 설치 파일과 포터블 exe가 생성됩니다.

### 3) 리눅스/맥에서 실행 폴더만 확인 (Wine 불필요)

```bash
npm run pack:win:dir   # release/SUMI-win32-x64/SUMI.exe 생성 (설치 파일 아님)
```

## 개발 중 실행

```bash
npm install
npm start                                   # 기본 서버(smc12.synology.me:9443)로 실행
SUMI_URL=https://다른서버:9443/ npm start     # 이번 실행에만 다른 서버 사용
npm start -- --url=https://다른서버:9443/     # 위와 동일
```

## 기능

| 기능 | 설명 |
|------|------|
| 전용 창 | 주소창·탭 없는 앱 창, 창 크기·위치·최대화 상태 기억 |
| 로그인 유지 | 세션 쿠키를 사용자 프로필에 저장하므로 껐다 켜도 로그인 유지 |
| 파일 업로드·다운로드 | 다운로드는 기본적으로 `다운로드` 폴더에 자동 저장(중복 이름 자동 회피), 작업 표시줄 진행률과 완료 알림 제공. 알림을 클릭하면 저장 위치가 열림 |
| 외부 링크 | SUMI 서버 밖의 링크와 새 창은 기본 브라우저로 열림 |
| 한글 메뉴 | 파일/편집/보기/이동/설정/도움말 메뉴와 한글 우클릭 메뉴 (메뉴 막대는 `Alt` 로 표시) |
| 단축키 | `Ctrl+R` 새로고침, `Ctrl+Shift+R` 캐시 무시 새로고침, `Ctrl+P` 인쇄, `Ctrl +/-/0` 확대·축소, `Alt+←/→` 뒤로·앞으로, `Alt+Home` 시작 화면, `F11` 전체 화면, `F12` 개발자 도구 |
| 연결 실패 화면 | 서버에 접속하지 못하면 원인·주소를 보여주고 **다시 시도** / **서버 주소 변경** 가능 |
| 트레이 상주 | `설정 → 창을 닫으면 트레이로 최소화` 를 켜면 창을 닫아도 백그라운드에서 알림 수신 |
| 중복 실행 방지 | 이미 실행 중이면 새 창 대신 기존 창을 앞으로 가져옴 |

## 설정

메뉴 **설정** 에서 바꿀 수 있고, 값은 아래 파일에 저장됩니다.

- 윈도우: `%APPDATA%\SUMI\settings.json`
- 리눅스(개발 실행): `~/.config/sumi-desktop/settings.json`

| 키 | 기본값 | 설명 |
|----|--------|------|
| `serverUrl` | `https://smc12.synology.me:9443/` | 접속할 SUMI 서버 주소 |
| `askDownloadLocation` | `false` | 다운로드할 때마다 저장 위치를 물어볼지 여부 |
| `closeToTray` | `false` | 창을 닫을 때 종료하지 않고 트레이로 내릴지 여부 |
| `allowInsecureCertificate` | `false` | 사설·만료 인증서 허용 여부. 켜더라도 `serverUrl` 과 같은 출처에만 적용 |
| `bounds`, `maximized`, `zoomLevel` | — | 창 상태(자동 저장) |

`SUMI_URL` 환경 변수나 `--url=` 인자는 **이번 실행에만** 적용되고 설정 파일에는 저장되지 않습니다.

## 보안 관련 메모

- 렌더러는 `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true` 로 실행되며, 웹 페이지에는 어떤 Node/IPC API도 노출하지 않습니다(앱 내장 오류 화면에서만 사용).
- 서버 출처가 아닌 주소로의 이동·새 창은 앱 안에서 열지 않고 기본 브라우저로 넘깁니다.
- 알림·전체화면 등 권한 요청은 SUMI 서버 출처일 때만 허용합니다.
- TLS 인증서는 기본적으로 정상 검증합니다(현재 서버는 Let's Encrypt 인증서 사용).

## 코드 서명 안내

서명 인증서가 없으므로 설치 시 **Windows SmartScreen** 경고가 나올 수 있습니다. `추가 정보 → 실행`으로 진행하면 됩니다. 사내 배포용 코드 서명 인증서가 있다면 `package.json` 의 `build.win` 에 `certificateFile`/`certificatePassword`(또는 CI 시크릿 `CSC_LINK`, `CSC_KEY_PASSWORD`)를 추가하면 자동으로 서명됩니다.

## 구조

```
sumi-desktop/
├── src/
│   ├── main.js        메인 프로세스(창·메뉴·트레이·세션·탐색 제어)
│   ├── config.js      설정 저장/불러오기
│   ├── menu.js        한글 앱 메뉴·우클릭 메뉴
│   ├── downloads.js   다운로드 자동 저장·진행률·완료 알림
│   ├── preload.js     오류 화면 전용 최소 IPC 브리지
│   ├── error.html     연결 실패 화면
│   └── error.js       연결 실패 화면 스크립트
├── assets/            아이콘(.png/.ico), 로고
└── scripts/           아이콘 생성 및 Wine 없는 패키징 스크립트
```
