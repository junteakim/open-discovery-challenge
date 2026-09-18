'use strict';

const path = require('node:path');
const {
  app,
  BrowserWindow,
  Menu,
  Notification,
  dialog,
  ipcMain,
  session,
  shell,
} = require('electron');

const appConfig = require('../app.config');
const config = require('./config');
const { buildAppMenu, buildContextMenu } = require('./menu');
const { registerDownloadHandler, openDownloadFolder } = require('./downloads');

const ICON_PNG = path.join(__dirname, '..', 'assets', 'app-icon.png');
const ERROR_PAGE = path.join(__dirname, 'error.html');
const PRELOAD = path.join(__dirname, 'preload.js');

let mainWindow = null;
let serverUrlWindow = null;

function serverOrigin() {
  try {
    return new URL(config.get('serverUrl')).origin;
  } catch {
    return new URL(config.DEFAULT_URL).origin;
  }
}

function isAppUrl(target) {
  try {
    return new URL(target).origin === serverOrigin();
  } catch {
    return false;
  }
}

function openExternal(target) {
  if (/^https?:\/\//i.test(target) || target.startsWith('mailto:')) {
    shell.openExternal(target).catch((error) => {
      console.error('외부 링크를 열지 못했습니다:', error);
    });
  }
}

// 평문 HTTP 출처를 보안 컨텍스트로 취급해야 WebGPU·비동기 클립보드 같은 API가 열립니다.
// 지정한 서버 출처 하나에만 적용하며, 렌더러 프로세스가 뜨기 전에 설정해야 합니다.
function applyInsecureOriginPolicy() {
  if (!appConfig.treatOriginAsSecure) return;
  const origin = serverOrigin();
  if (origin.startsWith('http://')) {
    app.commandLine.appendSwitch('unsafely-treat-insecure-origin-as-secure', origin);
  }
}

function loadServer(window = mainWindow) {
  if (!window || window.isDestroyed()) return;
  window.loadURL(config.get('serverUrl')).catch(() => {
    /* did-fail-load 핸들러가 오류 화면을 표시합니다. */
  });
}

function showErrorPage(window, info) {
  if (!window || window.isDestroyed()) return;
  const query = new URLSearchParams({
    url: info.url || config.get('serverUrl'),
    code: String(info.code ?? ''),
    message: info.message || '',
  });
  window.loadFile(ERROR_PAGE, { search: `?${query.toString()}` }).catch((error) => {
    console.error('오류 화면을 표시하지 못했습니다:', error);
  });
}

function persistBounds(window) {
  if (!window || window.isDestroyed()) return;
  config.set('maximized', window.isMaximized());
  if (!window.isMaximized() && !window.isFullScreen()) {
    const { width, height, x, y } = window.getBounds();
    config.set('bounds', { width, height, x, y });
  }
}

function createWindow() {
  const saved = config.get('bounds');
  const window = new BrowserWindow({
    width: saved.width,
    height: saved.height,
    x: saved.x,
    y: saved.y,
    minWidth: appConfig.window.minWidth,
    minHeight: appConfig.window.minHeight,
    show: false,
    backgroundColor: appConfig.backgroundColor,
    title: appConfig.displayName,
    icon: ICON_PNG,
    autoHideMenuBar: true,
    webPreferences: {
      preload: PRELOAD,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      spellcheck: false,
      // 도면 계산·렌더링이 백그라운드에서 멈추지 않게 합니다.
      backgroundThrottling: false,
    },
  });

  if (config.get('maximized')) window.maximize();

  window.once('ready-to-show', () => window.show());

  window.webContents.on('did-finish-load', () => {
    window.webContents.setZoomLevel(Number(config.get('zoomLevel')) || 0);
  });

  window.webContents.on('did-fail-load', (_event, code, description, failedUrl, isMainFrame) => {
    // -3(ERR_ABORTED)은 사용자가 이동을 취소했을 때도 발생하므로 무시합니다.
    if (!isMainFrame || code === -3) return;
    showErrorPage(window, { url: failedUrl, code, message: description });
  });

  window.webContents.on('render-process-gone', (_event, details) => {
    showErrorPage(window, {
      url: config.get('serverUrl'),
      code: details.reason,
      message: '화면 프로세스가 예기치 않게 종료되었습니다.',
    });
  });

  // 페이지의 beforeunload(저장하지 않은 도면)가 닫기를 막으면 확인 창을 띄웁니다.
  window.webContents.on('will-prevent-unload', (event) => {
    const choice = dialog.showMessageBoxSync(window, {
      type: 'warning',
      title: '저장하지 않은 변경사항',
      message: '저장하지 않은 도면 변경사항이 있습니다.',
      detail: '지금 나가면 마지막 로컬 저장 이후의 변경 내용이 사라질 수 있습니다.',
      buttons: ['계속 작업', '저장하지 않고 나가기'],
      defaultId: 0,
      cancelId: 0,
      noLink: true,
    });
    if (choice === 1) event.preventDefault();
  });

  window.webContents.on('will-navigate', (event, target) => {
    if (isAppUrl(target) || target.startsWith('file://')) return;
    event.preventDefault();
    openExternal(target);
  });

  window.webContents.setWindowOpenHandler(({ url }) => {
    // 인쇄 미리보기: 페이지가 window.open("")으로 빈 창을 열어 직접 내용을 씁니다.
    if (url === 'about:blank' || url === '') {
      return {
        action: 'allow',
        overrideBrowserWindowOptions: {
          width: appConfig.printWindow.width,
          height: appConfig.printWindow.height,
          parent: window,
          autoHideMenuBar: true,
          title: `${appConfig.displayName} · 인쇄 미리보기`,
          icon: ICON_PNG,
          backgroundColor: '#ffffff',
          webPreferences: { sandbox: true, contextIsolation: true, nodeIntegration: false },
        },
      };
    }
    if (isAppUrl(url)) {
      window.loadURL(url).catch(() => {});
      return { action: 'deny' };
    }
    openExternal(url);
    return { action: 'deny' };
  });

  window.webContents.on('context-menu', (_event, params) => {
    const menu = buildContextMenu({ window, params });
    if (menu) menu.popup({ window });
  });

  window.on('resize', () => persistBounds(window));
  window.on('move', () => persistBounds(window));
  window.on('maximize', () => persistBounds(window));
  window.on('unmaximize', () => persistBounds(window));

  window.on('close', () => {
    persistBounds(window);
    config.saveNow();
  });

  window.on('closed', () => {
    if (mainWindow === window) mainWindow = null;
  });

  return window;
}

function changeZoom(delta) {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  const next =
    delta === 0 ? 0 : Math.min(3, Math.max(-3, mainWindow.webContents.getZoomLevel() + delta));
  mainWindow.webContents.setZoomLevel(next);
  config.set('zoomLevel', next);
}

function promptForServerUrl() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  if (serverUrlWindow && !serverUrlWindow.isDestroyed()) {
    serverUrlWindow.focus();
    return;
  }

  serverUrlWindow = new BrowserWindow({
    parent: mainWindow,
    modal: true,
    width: 520,
    height: 230,
    resizable: false,
    minimizable: false,
    maximizable: false,
    title: '서버 주소',
    backgroundColor: '#171a21',
    autoHideMenuBar: true,
    webPreferences: {
      preload: PRELOAD,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  serverUrlWindow.setMenu(null);
  serverUrlWindow.on('closed', () => {
    serverUrlWindow = null;
  });
  serverUrlWindow.loadFile(path.join(__dirname, 'server-url.html')).catch((error) => {
    console.error('서버 주소 창을 열지 못했습니다:', error);
  });
}

function showAbout() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: `${appConfig.displayName} 정보`,
    message: `${appConfig.displayName} ${app.getVersion()}`,
    detail: [
      'SMC 서울기계 CAD(cad-lite) 데스크톱 앱',
      '',
      `서버: ${config.get('serverUrl')}`,
      `Electron: ${process.versions.electron}`,
      `Chromium: ${process.versions.chrome}`,
      `설정 파일: ${config.configPath()}`,
    ].join('\n'),
    buttons: ['확인'],
    noLink: true,
  });
}

function toggleSetting(key) {
  config.set(key, !config.get(key));
  config.saveNow();
  applyMenu();
}

function applyMenu() {
  Menu.setApplicationMenu(
    buildAppMenu({
      getWindow: () => mainWindow,
      reload: () => loadServer(),
      changeZoom,
      openDownloadFolder,
      promptForServerUrl,
      showAbout,
      toggleSetting,
      getSetting: (key) => config.get(key),
      quit: () => app.quit(),
    })
  );
}

function revealWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    mainWindow = createWindow();
    loadServer();
    return;
  }
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.focus();
}

function setupSession() {
  const defaultSession = session.defaultSession;

  registerDownloadHandler({
    session: defaultSession,
    getWindow: () => mainWindow,
    shouldAsk: () => Boolean(config.get('askDownloadLocation')),
    notify: (title, body, filePath) => {
      if (!Notification.isSupported()) return;
      const notification = new Notification({ title, body, icon: ICON_PNG });
      if (filePath) notification.on('click', () => shell.showItemInFolder(filePath));
      notification.show();
    },
  });

  defaultSession.setPermissionRequestHandler((contents, permission, callback) => {
    const allowed = [
      'clipboard-read',
      'clipboard-sanitized-write',
      'fullscreen',
      'notifications',
    ];
    callback(isAppUrl(contents.getURL()) && allowed.includes(permission));
  });
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => revealWindow());
  app.setAppUserModelId(appConfig.appId);

  config.load();
  applyInsecureOriginPolicy();

  app.whenReady().then(() => {
    setupSession();
    applyMenu();
    mainWindow = createWindow();
    loadServer();

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        mainWindow = createWindow();
        loadServer();
      }
    });
  });

  app.on('before-quit', () => config.saveNow());

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
  });
}

ipcMain.handle('shell:get-state', () => ({
  serverUrl: config.get('serverUrl'),
  defaultUrl: config.DEFAULT_URL,
  version: app.getVersion(),
  displayName: appConfig.displayName,
}));

ipcMain.handle('shell:retry', () => {
  loadServer();
  return true;
});

ipcMain.handle('shell:close-dialog', (event) => {
  const window = BrowserWindow.fromWebContents(event.sender);
  if (window && window !== mainWindow) window.close();
  return true;
});

ipcMain.handle('shell:set-server-url', (_event, value) => {
  const normalized = config.normalizeUrl(value);
  if (!normalized) return { ok: false, error: '주소 형식이 올바르지 않습니다.' };
  config.set('serverUrl', normalized);
  config.saveNow();
  loadServer();
  return { ok: true, serverUrl: normalized };
});
