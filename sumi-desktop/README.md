# SUMI 데스크톱 (Windows)

`https://smc12.synology.me:9443/` 의 SUMI(스미) 업무 에이전트를 브라우저 없이 **윈도우 프로그램(.exe)** 으로 쓰기 위한 Electron 앱입니다. 시작 메뉴/바탕화면 아이콘에서 바로 실행되고, 주소창·탭 없이 전용 창으로 열립니다.

> 웹 서비스 자체는 그대로 사용합니다. 이 폴더는 서버 코드를 바꾸지 않는 **클라이언트 껍데기(wrapper)** 입니다.

## 설치 파일 받는 방법

### 1) GitHub Releases에서 내려받기 (권장)

- 최신 설치 파일: **[sumi-desktop-latest 릴리스](https://github.com/junteakim/open-discovery-challenge/releases/tag/sumi-desktop-latest)** 의 `SUMI-<버전>-setup.exe`
- 버전별 릴리스: `sumi-desktop-v1.0.1` 처럼 `sumi-desktop-v*` 태그 릴리스

설치 후에는 앱이 스스로 업데이트하므로 다시 내려받을 필요가 없습니다.

### 2) GitHub Actions 아티팩트

**Actions → SUMI Desktop (Windows exe)** → 실행 결과 → **Artifacts → `SUMI-windows-setup`** (브랜치 푸시마다 빌드만 하고 게시는 하지 않습니다).

### 3) 윈도우 PC에서 직접 빌드

[Node.js 22 이상](https://nodejs.org/) 설치 후:

```powershell
cd sumi-desktop
npm ci
npm run build:win
```

`sumi-desktop\release\` 에 `SUMI-<버전>-setup.exe`, `.blockmap`, `latest.yml` 이 생성됩니다.

### 4) 리눅스/맥에서 실행 폴더만 확인 (Wine 불필요)

```bash
npm run pack:win:dir   # release/SUMI-win32-x64/SUMI.exe 생성 (설치 파일 아님)
```

## 자동 업데이트

설치판(NSIS)은 [electron-updater](https://www.electron.build/auto-update)로 **완전 자동 업데이트**됩니다.

1. 실행 10초 후, 이후 4시간마다 업데이트 채널의 `latest.yml` 을 조회합니다.
2. 새 버전이 있으면 **백그라운드로 내려받으며** 작업 표시줄에 진행률을 표시하고 한글 알림을 띄웁니다.
3. 다운로드가 끝나면 **"지금 다시 시작"** 또는 **"나중에"** 를 묻습니다. 나중에를 고르면 앱을 닫을 때(또는 다음 실행 시) 자동으로 교체 설치됩니다.
4. **도움말 → 업데이트 확인…** 으로 수동 확인도 할 수 있습니다.

### 채널이 앱별로 분리되는 방식

한 저장소에 앱이 두 개(SUMI, SMC DraftLine)라서 electron-updater의 GitHub provider("저장소의 최신 릴리스")는 쓰지 않습니다. 대신 **generic provider + 앱별 고정 태그**를 사용합니다.

| 항목 | 값 |
|------|----|
| 업데이트 피드(URL) | `https://github.com/junteakim/open-discovery-challenge/releases/download/sumi-desktop-latest/` |
| 채널 릴리스(고정 태그) | `sumi-desktop-latest` — CI가 매 릴리스마다 `latest.yml`, `SUMI-<버전>-setup.exe`, `.blockmap` 을 교체 |
| 버전 릴리스(보관용) | `sumi-desktop-v<버전>` — 같은 자산을 버전별로 보관 |

설정은 `package.json → build.publish` 에 있고, 빌드 시 `resources/app-update.yml` 로 앱에 포함됩니다. 다른 앱(`draftline-desktop-latest`)과 태그·URL이 다르므로 서로 섞이지 않습니다. 기존 프리릴리스 `sumi-desktop-v1.0.0`(포터블)은 그대로 두어도 영향이 없습니다.

## 새 버전 배포 절차

1. `sumi-desktop/package.json` 의 `version` 을 올립니다 (예: `1.0.1` → `1.0.2`). 필요하면 `npm version patch --no-git-tag-version` 을 사용합니다.
2. 커밋하고 브랜치에 푸시합니다.
3. **버전과 같은 태그**를 푸시합니다.

   ```bash
   git tag sumi-desktop-v1.0.2
   git push origin sumi-desktop-v1.0.2
   ```

   (또는 Actions에서 **Run workflow** → `publish` 체크. 이 경우 태그는 CI가 만듭니다.)
4. CI(windows-latest)가 설치 파일을 빌드해 `sumi-desktop-v1.0.2` 릴리스를 만들고, `sumi-desktop-latest` 채널의 자산을 교체합니다. 태그와 `package.json` 버전이 다르면 빌드가 실패합니다.
5. 설치된 앱들은 다음 확인 주기(최대 4시간, 또는 재실행 10초 후)에 새 버전을 내려받습니다.

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
| 자동 업데이트 | 새 버전을 백그라운드로 내려받아 재시작 시 교체. 아래 [자동 업데이트](#자동-업데이트) 참고 |
| 단축키 | `Ctrl+R` 새로고침, `Ctrl+Shift+R` 캐시 무시 새로고침, `Ctrl+P` 인쇄, `Ctrl +/-/0` 확대·축소, `Alt+←/→` 뒤로·앞으로, `Alt+Home` 시작 화면, `F11` 전체 화면, `F12` 개발자 도구 |
| 연결 실패 화면 | 서버에 접속하지 못하면 원인·주소를 보여주고 **다시 시도** / **서버 주소 변경** 가능 |
| 트레이 상주 | `설정 → 창을 닫으면 트레이로 최소화` 를 켜면 창을 닫아도 백그라운드에서 알림 수신 |
| 중복 실행 방지 | 이미 실행 중이면 새 창 대신 기존 창을 앞으로 가져옴 |

## 설정

메뉴 **설정 → 서버 주소 확인·변경…** 에서 접속 주소를 직접 입력할 수 있고(`기본값` 버튼으로 초기화), 나머지 항목은 **설정** 메뉴의 체크 항목으로 켜고 끕니다. 값은 아래 파일에 저장됩니다.

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
│   ├── updater.js     electron-updater 연동(백그라운드 다운로드·한글 알림·재시작 확인)
│   ├── config.js      설정 저장/불러오기
│   ├── menu.js        한글 앱 메뉴·우클릭 메뉴
│   ├── downloads.js   다운로드 자동 저장·진행률·완료 알림
│   ├── preload.js     오류 화면 전용 최소 IPC 브리지
│   ├── error.html     연결 실패 화면
│   ├── error.js       연결 실패 화면 스크립트
│   ├── server-url.html 서버 주소 입력 대화 창
│   └── server-url.js  서버 주소 입력 대화 창 스크립트
├── assets/            아이콘(.png/.ico), 로고
└── scripts/           아이콘 생성 및 Wine 없는 패키징 스크립트
```
