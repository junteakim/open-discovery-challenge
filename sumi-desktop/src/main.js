'use strict';

const path = require('node:path');
const {
  app,
  BrowserWindow,
  Menu,
  Notification,
  Tray,
  clipboard,
  dialog,
  ipcMain,
  nativeImage,
  session,
  shell,
} = require('electron');

const config = require('./config');
const { buildAppMenu, buildContextMenu } = require('./menu');
const { registerDownloadHandler, openDownloadFolder } = require('./downloads');

const APP_ID = 'com.smc.sumi';
const ICON_PNG = path.join(__dirname, '..', 'assets', 'smc-icon.png');
const ERROR_PAGE = path.join(__dirname, 'error.html');

let mainWindow = null;
let tray = null;
let quitting = false;

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
    minWidth: 900,
    minHeight: 600,
    show: false,
    backgroundColor: '#0f1115',
    title: 'SUMI · 스미',
    icon: ICON_PNG,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      spellcheck: true,
      backgroundThrottling: false,
    },
  });

  if (config.get('maximized')) window.maximize();

  window.once('ready-to-show', () => window.show());

  window.webContents.on('did-finish-load', () => {
    const level = Number(config.get('zoomLevel')) || 0;
    window.webContents.setZoomLevel(level);
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

  window.webContents.on('will-navigate', (event, target) => {
    if (isAppUrl(target) || target.startsWith('file://')) return;
    event.preventDefault();
    openExternal(target);
  });

  window.webContents.setWindowOpenHandler(({ url }) => {
    if (isAppUrl(url)) {
      loadServerUrl(window, url);
      return { action: 'deny' };
    }
    openExternal(url);
    return { action: 'deny' };
  });

  window.webContents.on('context-menu', (_event, params) => {
    buildContextMenu({ window, params, onReload: () => loadServer(window) }).popup({ window });
  });

  window.on('resize', () => persistBounds(window));
  window.on('move', () => persistBounds(window));
  window.on('maximize', () => persistBounds(window));
  window.on('unmaximize', () => persistBounds(window));

  window.on('close', (event) => {
    if (!quitting && config.get('closeToTray') && tray) {
      event.preventDefault();
      window.hide();
      return;
    }
    persistBounds(window);
    config.saveNow();
  });

  window.on('closed', () => {
    if (mainWindow === window) mainWindow = null;
  });

  return window;
}

function loadServerUrl(window, target) {
  window.loadURL(target).catch(() => {
    /* did-fail-load 핸들러가 처리합니다. */
  });
}

function changeZoom(delta) {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  const next =
    delta === 0 ? 0 : Math.min(5, Math.max(-5, mainWindow.webContents.getZoomLevel() + delta));
  mainWindow.webContents.setZoomLevel(next);
  config.set('zoomLevel', next);
}

async function promptForServerUrl() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  const current = config.get('serverUrl');
  const { response } = await dialog.showMessageBox(mainWindow, {
    type: 'question',
    title: '서버 주소',
    message: '현재 서버 주소',
    detail: current,
    buttons: ['닫기', '주소 복사', '기본 주소로 되돌리기'],
    defaultId: 0,
    cancelId: 0,
    noLink: true,
  });

  if (response === 1) {
    clipboard.writeText(current);
  } else if (response === 2) {
    config.set('serverUrl', config.DEFAULT_URL);
    config.saveNow();
    loadServer();
  }
}

function showAbout() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: 'SUMI 정보',
    message: `SUMI · 스미 ${app.getVersion()}`,
    detail: [
      'SMC 서울기계 사내 업무 에이전트 데스크톱 앱',
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
  if (key === 'closeToTray') setupTray();
}

function applyMenu() {
  Menu.setApplicationMenu(
    buildAppMenu({
      getWindow: () => mainWindow,
      reload: () => loadServer(),
      goHome: () => loadServer(),
      changeZoom,
      openDownloadFolder,
      promptForServerUrl,
      showAbout,
      toggleSetting,
      getSetting: (key) => config.get(key),
      quit: () => {
        quitting = true;
        app.quit();
      },
    })
  );
}

function setupTray() {
  const wanted = config.get('closeToTray');
  if (!wanted) {
    if (tray) {
      tray.destroy();
      tray = null;
    }
    return;
  }
  if (tray) return;

  const image = nativeImage.createFromPath(ICON_PNG).resize({ width: 16, height: 16 });
  tray = new Tray(image);
  tray.setToolTip('SUMI · 스미');
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: 'SUMI 열기', click: () => revealWindow() },
      { type: 'separator' },
      {
        label: '종료',
        click: () => {
          quitting = true;
          app.quit();
        },
      },
    ])
  );
  tray.on('click', () => revealWindow());
}

function revealWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    mainWindow = createWindow();
    loadServer();
    return;
  }
  if (!mainWindow.isVisible()) mainWindow.show();
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

  try {
    defaultSession.setSpellCheckerLanguages(['ko', 'en-US']);
  } catch {
    /* 사전이 없는 플랫폼에서는 맞춤법 검사를 건너뜁니다. */
  }

  defaultSession.setPermissionRequestHandler((contents, permission, callback) => {
    const allowed = ['notifications', 'clipboard-sanitized-write', 'fullscreen'];
    callback(isAppUrl(contents.getURL()) && allowed.includes(permission));
  });
}

function setupCertificateHandling() {
  app.on('certificate-error', (event, _webContents, url, _error, _certificate, callback) => {
    // 사설 인증서를 쓰는 사내 서버를 위한 예외. 기본값은 꺼져 있고,
    // 설정에서 켠 경우에도 지정한 서버 주소에 대해서만 허용합니다.
    if (config.get('allowInsecureCertificate') && isAppUrl(url)) {
      event.preventDefault();
      callback(true);
      return;
    }
    callback(false);
  });
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => revealWindow());

  app.setAppUserModelId(APP_ID);

  app.whenReady().then(() => {
    config.load();
    setupSession();
    applyMenu();
    setupTray();
    mainWindow = createWindow();
    loadServer();

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        mainWindow = createWindow();
        loadServer();
      }
    });
  });

  app.on('before-quit', () => {
    quitting = true;
    config.saveNow();
  });

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin' && !config.get('closeToTray')) app.quit();
  });
}

setupCertificateHandling();

ipcMain.handle('sumi:get-state', () => ({
  serverUrl: config.get('serverUrl'),
  version: app.getVersion(),
}));

ipcMain.handle('sumi:retry', () => {
  loadServer();
  return true;
});

ipcMain.handle('sumi:set-server-url', (_event, value) => {
  const normalized = config.normalizeUrl(value);
  if (!normalized) return { ok: false, error: '주소 형식이 올바르지 않습니다.' };
  config.set('serverUrl', normalized);
  config.saveNow();
  loadServer();
  return { ok: true, serverUrl: normalized };
});
