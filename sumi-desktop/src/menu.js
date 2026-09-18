'use strict';

const { Menu, MenuItem, clipboard, shell } = require('electron');

function buildAppMenu(actions) {
  const {
    getWindow,
    reload,
    goHome,
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
        { label: '새로고침', accelerator: 'CmdOrCtrl+R', click: () => reload() },
        {
          label: '캐시 지우고 새로고침',
          accelerator: 'CmdOrCtrl+Shift+R',
          click: withWindow((window) => window.webContents.reloadIgnoringCache()),
        },
        { type: 'separator' },
        {
          label: '현재 페이지 인쇄',
          accelerator: 'CmdOrCtrl+P',
          click: withWindow((window) => window.webContents.print()),
        },
        { label: '다운로드 폴더 열기', click: () => openDownloadFolder() },
        { type: 'separator' },
        { label: '종료', accelerator: 'CmdOrCtrl+Q', click: () => quit() },
      ],
    },
    {
      label: '편집(&E)',
      submenu: [
        { label: '실행 취소', role: 'undo' },
        { label: '다시 실행', role: 'redo' },
        { type: 'separator' },
        { label: '잘라내기', role: 'cut' },
        { label: '복사', role: 'copy' },
        { label: '붙여넣기', role: 'paste' },
        { label: '서식 없이 붙여넣기', role: 'pasteAndMatchStyle' },
        { label: '모두 선택', role: 'selectAll' },
      ],
    },
    {
      label: '보기(&V)',
      submenu: [
        { label: '확대', accelerator: 'CmdOrCtrl+Plus', click: () => changeZoom(0.5) },
        { label: '축소', accelerator: 'CmdOrCtrl+-', click: () => changeZoom(-0.5) },
        { label: '기본 크기', accelerator: 'CmdOrCtrl+0', click: () => changeZoom(0) },
        { type: 'separator' },
        { label: '전체 화면', role: 'togglefullscreen' },
        {
          label: '개발자 도구',
          accelerator: 'F12',
          click: withWindow((window) => window.webContents.toggleDevTools()),
        },
      ],
    },
    {
      label: '이동(&G)',
      submenu: [
        {
          label: '뒤로',
          accelerator: 'Alt+Left',
          click: withWindow((window) => {
            if (window.webContents.navigationHistory.canGoBack()) {
              window.webContents.navigationHistory.goBack();
            }
          }),
        },
        {
          label: '앞으로',
          accelerator: 'Alt+Right',
          click: withWindow((window) => {
            if (window.webContents.navigationHistory.canGoForward()) {
              window.webContents.navigationHistory.goForward();
            }
          }),
        },
        { type: 'separator' },
        { label: '홈(SUMI 시작 화면)', accelerator: 'Alt+Home', click: () => goHome() },
      ],
    },
    {
      label: '설정(&S)',
      submenu: [
        { label: '서버 주소 확인·변경…', click: () => promptForServerUrl() },
        { type: 'separator' },
        {
          label: '다운로드할 때 저장 위치 묻기',
          type: 'checkbox',
          checked: Boolean(getSetting('askDownloadLocation')),
          click: () => toggleSetting('askDownloadLocation'),
        },
        {
          label: '창을 닫으면 트레이로 최소화',
          type: 'checkbox',
          checked: Boolean(getSetting('closeToTray')),
          click: () => toggleSetting('closeToTray'),
        },
        {
          label: '사설 인증서 허용(사내 서버 전용)',
          type: 'checkbox',
          checked: Boolean(getSetting('allowInsecureCertificate')),
          click: () => toggleSetting('allowInsecureCertificate'),
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
        { label: 'SUMI 정보', click: () => showAbout() },
      ],
    },
  ];

  return Menu.buildFromTemplate(template);
}

function buildContextMenu({ window, params, onReload }) {
  const menu = new Menu();
  const add = (options) => menu.append(new MenuItem(options));

  if (params.misspelledWord && params.dictionarySuggestions.length > 0) {
    for (const suggestion of params.dictionarySuggestions.slice(0, 5)) {
      add({
        label: suggestion,
        click: () => window.webContents.replaceMisspelling(suggestion),
      });
    }
    add({ type: 'separator' });
  }

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
    add({ label: '이미지 주소 복사', click: () => clipboard.writeText(params.srcURL) });
    add({ type: 'separator' });
  }

  if (params.isEditable) {
    add({ label: '실행 취소', role: 'undo' });
    add({ label: '다시 실행', role: 'redo' });
    add({ type: 'separator' });
    add({ label: '잘라내기', role: 'cut', enabled: Boolean(params.selectionText) });
    add({ label: '복사', role: 'copy', enabled: Boolean(params.selectionText) });
    add({ label: '붙여넣기', role: 'paste' });
    add({ label: '모두 선택', role: 'selectAll' });
  } else {
    if (params.selectionText) {
      add({ label: '복사', role: 'copy' });
      add({ type: 'separator' });
    }
    add({ label: '새로고침', click: () => onReload() });
    add({ label: '모두 선택', role: 'selectAll' });
  }

  return menu;
}

module.exports = { buildAppMenu, buildContextMenu };
