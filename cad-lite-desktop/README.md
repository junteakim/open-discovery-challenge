# SMC DraftLine 데스크톱 (Windows, 포터블 단일 exe)

`http://smc12.synology.me:8080/cad-lite/` 의 SMC DraftLine(cad-lite) CAD를 브라우저 없이 **윈도우 프로그램(.exe 한 개)** 으로 쓰기 위한 Electron 앱입니다. 설치 파일은 만들지 않으며, 산출물은 `SMC-DraftLine-<버전>-portable.exe` 하나입니다. 그 파일만 복사해서 실행하면 됩니다.

> 웹 서비스 자체는 그대로 사용합니다. 이 폴더는 서버 코드를 바꾸지 않는 **클라이언트 껍데기(wrapper)** 입니다. `sumi-desktop/`(SUMI 래퍼)과 같은 구조이며, 앱마다 다른 값은 `app.config.js` 한 파일에 모아 두었습니다.

## exe 받는 방법

### 1) GitHub Actions에서 내려받기 (권장)

1. GitHub 저장소 → **Actions** → **SMC DraftLine Desktop (Windows portable exe)** 워크플로 선택
2. 최신 실행 결과(또는 **Run workflow** 로 직접 실행) 클릭
3. 하단 **Artifacts → `SMC-DraftLine-windows-portable-exe`** 다운로드 후 압축 해제 → `SMC-DraftLine-1.0.0-portable.exe`

워크플로는 exe가 정확히 1개만 만들어졌는지 검사한 뒤 업로드합니다.

### 2) 윈도우 PC에서 직접 빌드

[Node.js 22 이상](https://nodejs.org/) 설치 후:

```powershell
cd cad-lite-desktop
npm ci
npm run build:win
```

`cad-lite-desktop\release\SMC-DraftLine-1.0.0-portable.exe` 가 생성됩니다.

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
| 로그인 없음, 도면은 브라우저 `localStorage`에 로컬 저장 | 사용자 프로필(`%APPDATA%\SMC DraftLine`)에 영구 보관. 포터블 exe라도 껐다 켜면 도면이 그대로 남음 |
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

## 포터블 exe 동작 방식

electron-builder `portable` 타깃은 실행 시 임시 폴더에 앱을 풀고 실행하므로 첫 화면까지 몇 초가 걸릴 수 있습니다. 서명 인증서가 없어 처음 실행할 때 **Windows SmartScreen** 경고가 나올 수 있으며, `추가 정보 → 실행`으로 진행하면 됩니다.

## 구조

```
cad-lite-desktop/
├── app.config.js       앱 이름·서버 주소·창 크기·단축키 등 앱별 값
├── src/
│   ├── main.js         메인 프로세스(창·메뉴·세션·탐색 제어·인쇄 창·미저장 확인)
│   ├── config.js       설정 저장/불러오기
│   ├── menu.js         한글 앱 메뉴·우클릭 메뉴
│   ├── downloads.js    내보내기 저장 대화상자·진행률·완료 알림
│   ├── preload.js      내장 화면 전용 최소 IPC 브리지
│   ├── error.html/js   연결 실패 화면
│   └── server-url.html/js 서버 주소 입력 창
├── assets/             아이콘(.png/.ico), 로고
└── scripts/            아이콘 생성 스크립트
```
