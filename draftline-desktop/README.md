# SMC DraftLine 데스크톱 (Windows, 자동 업데이트 설치판)

`http://smc12.synology.me:8080/cad-lite/` 의 SMC DraftLine(cad-lite) CAD를 브라우저 없이 **윈도우 프로그램** 으로 쓰기 위한 Electron 앱입니다. NSIS 설치판(`SMC-DraftLine-<버전>-setup.exe`)으로 배포하며, 설치된 앱은 새 버전을 스스로 내려받아 교체하는 **완전 자동 업데이트**를 지원합니다.

> 웹 서비스 자체는 그대로 사용합니다. 이 폴더는 서버 코드를 바꾸지 않는 **클라이언트 껍데기(wrapper)** 입니다. `sumi-desktop/`(SUMI 래퍼)과 같은 구조이며, 앱마다 다른 값은 `app.config.js` 한 파일에 모아 두었습니다.

## 설치 파일 받는 방법

### 1) GitHub Releases에서 내려받기 (권장)

- 최신 설치 파일: **[draftline-desktop-latest 릴리스](https://github.com/junteakim/open-discovery-challenge/releases/tag/draftline-desktop-latest)** 의 `SMC-DraftLine-<버전>-setup.exe`
- 버전별 릴리스: `draftline-desktop-v1.0.1` 처럼 `draftline-desktop-v*` 태그 릴리스

설치 후에는 앱이 스스로 업데이트하므로 다시 내려받을 필요가 없습니다.

### 2) GitHub Actions 아티팩트

**Actions → SMC DraftLine Desktop (Windows exe)** → 실행 결과 → **Artifacts → `SMC-DraftLine-windows-setup`** (브랜치 푸시마다 빌드만 하고 게시는 하지 않습니다).

### 3) 윈도우 PC에서 직접 빌드

[Node.js 22 이상](https://nodejs.org/) 설치 후:

```powershell
cd draftline-desktop
npm ci
npm run build:win
```

`draftline-desktop\release\` 에 `SMC-DraftLine-<버전>-setup.exe`, `.blockmap`, `latest.yml` 이 생성됩니다.

## 자동 업데이트

설치판(NSIS)은 [electron-updater](https://www.electron.build/auto-update)로 **완전 자동 업데이트**됩니다.

1. 실행 10초 후, 이후 4시간마다 업데이트 채널의 `latest.yml` 을 조회합니다.
2. 새 버전이 있으면 **백그라운드로 내려받으며** 작업 표시줄에 진행률을 표시하고 한글 알림을 띄웁니다. 도면 작업은 계속할 수 있습니다.
3. 다운로드가 끝나면 **"지금 다시 시작"** 또는 **"나중에"** 를 묻습니다. 나중에를 고르면 앱을 닫을 때(또는 다음 실행 시) 자동으로 교체 설치됩니다. 도면은 로컬 저장소에 있으므로 업데이트 후에도 그대로 남습니다.
4. **도움말 → 업데이트 확인…** 으로 수동 확인도 할 수 있습니다.

### 채널이 앱별로 분리되는 방식

한 저장소에 앱이 두 개(SUMI, SMC DraftLine)라서 electron-updater의 GitHub provider("저장소의 최신 릴리스")는 쓰지 않습니다. 대신 **generic provider + 앱별 고정 태그**를 사용합니다.

| 항목 | 값 |
|------|----|
| 업데이트 피드(URL) | `https://github.com/junteakim/open-discovery-challenge/releases/download/draftline-desktop-latest/` |
| 채널 릴리스(고정 태그) | `draftline-desktop-latest` — CI가 매 릴리스마다 `latest.yml`, `SMC-DraftLine-<버전>-setup.exe`, `.blockmap` 을 교체 |
| 버전 릴리스(보관용) | `draftline-desktop-v<버전>` — 같은 자산을 버전별로 보관 |

설정은 `package.json → build.publish` 에 있고, 빌드 시 `resources/app-update.yml` 로 앱에 포함됩니다. 다른 앱(`sumi-desktop-latest`)과 태그·URL이 다르므로 서로 섞이지 않습니다. 기존 프리릴리스 `draftline-desktop-v1.0.0`(포터블)은 그대로 두어도 영향이 없습니다.

## 새 버전 배포 절차

1. `draftline-desktop/package.json` 의 `version` 을 올립니다 (예: `1.0.1` → `1.0.2`). 필요하면 `npm version patch --no-git-tag-version` 을 사용합니다.
2. 커밋하고 브랜치에 푸시합니다.
3. **버전과 같은 태그**를 푸시합니다.

   ```bash
   git tag draftline-desktop-v1.0.2
   git push origin draftline-desktop-v1.0.2
   ```

   (또는 Actions에서 **Run workflow** → `publish` 체크. 이 경우 태그는 CI가 만듭니다.)
4. CI(windows-latest)가 설치 파일을 빌드해 `draftline-desktop-v1.0.2` 릴리스를 만들고, `draftline-desktop-latest` 채널의 자산을 교체합니다. 태그와 `package.json` 버전이 다르면 빌드가 실패합니다.
5. 설치된 앱들은 다음 확인 주기(최대 4시간, 또는 재실행 10초 후)에 새 버전을 내려받습니다.

## 개발 중 실행

```bash
npm install
npm start                                            # 기본 서버(smc12.synology.me:8080/cad-lite/)
DRAFTLINE_URL=http://다른서버:8080/cad-lite/ npm start  # 이번 실행에만 다른 서버 사용
npm start -- --url=http://다른서버:8080/cad-lite/      # 위와 동일
```

## 웹앱 특성과 대응

| 확인한 웹앱 특성 | 데스크톱 앱 처리 |
|------|------|
| 로그인 없음, 도면은 브라우저 `localStorage`에 로컬 저장 | 사용자 프로필(`%APPDATA%\SMC DraftLine`)에 영구 보관. 앱을 업데이트해도 도면이 그대로 남음 |
| 렌더링: **WebGPU**(`navigator.gpu`) 우선, 없으면 Canvas 2D 폴백. 3D 용기 패널은 Three.js(WebGL) | 서버가 평문 HTTP라 브라우저에서는 WebGPU가 막힘(보안 컨텍스트 전용). 앱은 지정한 서버 출처 하나만 보안 컨텍스트로 취급(`unsafely-treat-insecure-origin-as-secure`)해 GPU 백엔드를 쓸 수 있게 함. GPU 가속은 켠 채로 유지 |
| 도면 열기: `<input type="file">`(Ctrl+O), 드래그 앤 드롭 | Electron 기본 파일 대화상자·드롭 그대로 동작 |
| 내보내기: DXF/JSON/SVG/PNG를 blob 다운로드로 저장 | 기본값은 **파일명이 채워진 "다른 이름으로 저장" 창**(설정에서 자동 저장으로 변경 가능). 작업 표시줄 진행률, 완료 알림(클릭 시 폴더 열기) |
| 인쇄: `window.open("")`으로 빈 창을 열어 미리보기를 그림(Ctrl+P) | 빈 창(`about:blank`)만 자식 창으로 허용, 그 외 새 창·외부 링크는 기본 브라우저로 |
| `beforeunload`로 미저장 변경 보호 | 페이지가 닫기를 막으면 "계속 작업 / 저장하지 않고 나가기" 확인 창 표시 |
| 자체 단축키: Ctrl+S/O/Z/Y/A/C/X/V/P, F3/F7/F8/F9/F12, Space, Delete, Enter, 우클릭(화면 이동·명령 종료) | 앱 메뉴에 이 키들을 가속기로 등록하지 않음(메뉴 가속기는 페이지보다 먼저 키를 가로챔). 개발자 도구는 F12 대신 `Ctrl+Shift+I`. 캔버스 우클릭에는 자체 컨텍스트 메뉴를 띄우지 않음 |
| 서버 API 호출 `/api/ai/…` 등 같은 출처 fetch | 같은 출처라 그대로 동작 |

## 기능

- 주소창·탭 없는 전용 창(기본 최대화), 창 크기·위치·UI 확대 비율 기억, 중복 실행 방지
- 한글 메뉴(파일/보기/설정/도움말, `Alt`로 표시), `Ctrl +/-/0` UI 확대·축소, `F11` 전체 화면
- 연결 실패 시 원인·재시도·서버 주소 변경 화면, 설정 메뉴의 서버 주소 입력 창
- 자동 업데이트(아래 [자동 업데이트](#자동-업데이트) 참고), 도움말 메뉴에서 수동 확인
- 서버 출처 밖의 링크는 기본 브라우저로 전달

## 설정

메뉴 **설정** 에서 바꿀 수 있고, 값은 `%APPDATA%\SMC DraftLine\settings.json` 에 저장됩니다.

| 키 | 기본값 | 설명 |
|----|--------|------|
| `serverUrl` | `http://smc12.synology.me:8080/cad-lite/` | 접속할 서버 주소 |
| `askDownloadLocation` | `true` | 내보낼 때마다 저장 위치를 물어볼지 여부(끄면 `다운로드` 폴더에 자동 저장, 중복 이름 자동 회피) |
| `bounds`, `maximized`, `zoomLevel` | — | 창 상태(자동 저장) |

`DRAFTLINE_URL` 환경 변수나 `--url=` 인자는 **이번 실행에만** 적용되고 설정 파일에는 저장되지 않습니다. HTTP 서버 주소를 바꾼 경우 보안 컨텍스트(WebGPU) 설정은 앱을 다시 시작해야 새 주소에 적용됩니다.

## 보안·HTTP 관련 메모

- 서버가 **평문 HTTP(8080)** 이므로 사내망/VPN 밖에서는 통신 내용이 노출될 수 있습니다. 앱은 이를 바꾸지 않습니다(HTTPS 전환은 서버 측 작업).
- 보안 컨텍스트 예외는 `app.config.js`의 `serverUrl` 출처 **하나**에만 적용되며, 다른 HTTP 사이트에는 영향이 없습니다.
- 렌더러는 `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`로 실행되고, 웹 페이지에는 어떤 Node/IPC API도 노출하지 않습니다(앱 내장 오류 화면·주소 입력 창에서만 사용).
- 서버 출처가 아닌 주소로의 이동·새 창은 앱 안에서 열지 않고 기본 브라우저로 넘깁니다. 클립보드·전체화면·알림 권한은 서버 출처에만 허용합니다.

## 코드 서명 안내

서명 인증서가 없어 처음 설치할 때 **Windows SmartScreen** 경고가 나올 수 있으며, `추가 정보 → 실행`으로 진행하면 됩니다. 자동 업데이트로 받는 새 버전은 SHA-512 해시로 검증됩니다. 사내 코드 서명 인증서가 있다면 CI 시크릿 `CSC_LINK`, `CSC_KEY_PASSWORD` 를 추가하면 설치 파일이 자동으로 서명됩니다.

## 구조

```
draftline-desktop/
├── app.config.js       앱 이름·서버 주소·창 크기·단축키 등 앱별 값
├── src/
│   ├── main.js         메인 프로세스(창·메뉴·세션·탐색 제어·인쇄 창·미저장 확인)
│   ├── updater.js      electron-updater 연동(백그라운드 다운로드·한글 알림·재시작 확인)
│   ├── config.js       설정 저장/불러오기
│   ├── menu.js         한글 앱 메뉴·우클릭 메뉴
│   ├── downloads.js    내보내기 저장 대화상자·진행률·완료 알림
│   ├── preload.js      내장 화면 전용 최소 IPC 브리지
│   ├── error.html/js   연결 실패 화면
│   └── server-url.html/js 서버 주소 입력 창
├── assets/             아이콘(.png/.ico), 로고
└── scripts/            아이콘 생성 스크립트
```
