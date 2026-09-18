'use strict';

const { Menu, MenuItem, clipboard, shell } = require('electron');
const appConfig = require('../app.config');

// 주의: 이 앱 메뉴에는 페이지가 직접 처리하는 단축키(Ctrl+S/O/Z/Y/A/C/X/V/P, F3/F7/F8/F9/F12)를
// 가속기로 등록하지 않습니다. 메뉴 가속기는 페이지보다 먼저 키를 가로채기 때문입니다.
function buildAppMenu(actions) {
  const {
    getWindow,
    reload,
    changeZoom,
    openDownloadFolder,
    promptForServerUrl,
    showAbout,
    toggleSetting,
    getSetting,
    quit,
  } = actions;

  const withWindow = (fn) => () => {
    const window = getWindow();
    if (window && !window.isDestroyed()) fn(window);
  };

  const template = [
    {
      label: '파일(&F)',
      submenu: [
        { label: '다운로드 폴더 열기', click: () => openDownloadFolder() },
        { type: 'separator' },
        { label: '앱 다시 불러오기', click: () => reload() },
        {
          label: '캐시 지우고 다시 불러오기',
          accelerator: appConfig.shortcuts.hardReload,
          click: withWindow((window) => window.webContents.reloadIgnoringCache()),
        },
        { type: 'separator' },
        { label: '종료', accelerator: 'CmdOrCtrl+Q', click: () => quit() },
      ],
    },
    {
      label: '보기(&V)',
      submenu: [
        { label: 'UI 확대', accelerator: 'CmdOrCtrl+Plus', click: () => changeZoom(0.5) },
        { label: 'UI 축소', accelerator: 'CmdOrCtrl+-', click: () => changeZoom(-0.5) },
        { label: 'UI 기본 크기', accelerator: 'CmdOrCtrl+0', click: () => changeZoom(0) },
        { type: 'separator' },
        { label: '전체 화면', role: 'togglefullscreen' },
        {
          label: '개발자 도구',
          accelerator: appConfig.shortcuts.devTools,
          click: withWindow((window) => window.webContents.toggleDevTools()),
        },
      ],
    },
    {
      label: '설정(&S)',
      submenu: [
        { label: '서버 주소 확인·변경…', click: () => promptForServerUrl() },
        { type: 'separator' },
        {
          label: '내보낼 때 저장 위치 묻기',
          type: 'checkbox',
          checked: Boolean(getSetting('askDownloadLocation')),
          click: () => toggleSetting('askDownloadLocation'),
        },
      ],
    },
    {
      label: '도움말(&H)',
      submenu: [
        {
          label: '브라우저로 열기',
          click: () => shell.openExternal(getSetting('serverUrl')),
        },
        { label: `${appConfig.displayName} 정보`, click: () => showAbout() },
      ],
    },
  ];

  return Menu.buildFromTemplate(template);
}

// 도면 캔버스는 우클릭을 화면 이동·명령 종료에 쓰므로, 링크/이미지/텍스트 입력처럼
// 명확한 대상이 있을 때만 메뉴를 띄우고 그 외에는 null을 돌려줍니다.
function buildContextMenu({ window, params }) {
  const relevant =
    params.isEditable ||
    Boolean(params.linkURL) ||
    Boolean(params.selectionText) ||
    (params.mediaType === 'image' && params.srcURL);
  if (!relevant) return null;

  const menu = new Menu();
  const add = (options) => menu.append(new MenuItem(options));

  if (params.linkURL) {
    add({
      label: '링크를 브라우저에서 열기',
      click: () => shell.openExternal(params.linkURL),
    });
    add({ label: '링크 주소 복사', click: () => clipboard.writeText(params.linkURL) });
    add({ type: 'separator' });
  }

  if (params.mediaType === 'image' && params.srcURL) {
    add({ label: '이미지 복사', click: () => window.webContents.copyImageAt(params.x, params.y) });
    add({ type: 'separator' });
  }

  if (params.isEditable) {
    add({ label: '잘라내기', role: 'cut', enabled: Boolean(params.selectionText) });
    add({ label: '복사', role: 'copy', enabled: Boolean(params.selectionText) });
    add({ label: '붙여넣기', role: 'paste' });
    add({ label: '모두 선택', role: 'selectAll' });
    return menu;
  }

  if (params.selectionText) add({ label: '복사', role: 'copy' });
  return menu;
}

module.exports = { buildAppMenu, buildContextMenu };
