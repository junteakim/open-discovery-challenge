'use strict';

const { app, dialog, Notification } = require('electron');
const { autoUpdater } = require('electron-updater');

const CHECK_INTERVAL_MS = 4 * 60 * 60 * 1000;
const FIRST_CHECK_DELAY_MS = 10 * 1000;

// 업데이트 흐름:
//  1) 실행 10초 후, 이후 4시간마다 latest.yml 조회
//  2) 새 버전이 있으면 백그라운드로 내려받으며 작업 표시줄에 진행률 표시
//  3) 다운로드가 끝나면 "지금 다시 시작" 또는 "나중에"를 물음
//     - 나중에: 앱을 종료할 때(또는 다음 실행 시) 자동으로 교체 설치
function setupAutoUpdater({ appName, iconPath, getWindow }) {
  let manualCheck = false;
  let downloadedVersion = null;
  let timer = null;

  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;
  autoUpdater.allowPrerelease = false;
  autoUpdater.allowDowngrade = false;
  // 웹 설치 프로그램은 쓰지 않으므로 전체 설치 파일만 내려받습니다.
  autoUpdater.disableWebInstaller = true;
  autoUpdater.logger = {
    info: (message) => console.log('[updater]', message),
    warn: (message) => console.warn('[updater]', message),
    error: (message) => console.error('[updater]', message),
    debug: () => {},
  };

  const window = () => {
    const current = getWindow();
    return current && !current.isDestroyed() ? current : null;
  };

  const notify = (title, body) => {
    if (!Notification.isSupported()) return;
    new Notification({ title, body, icon: iconPath, silent: true }).show();
  };

  const setProgress = (value) => {
    const current = window();
    if (current) current.setProgressBar(value);
  };

  const versionLabel = (info) => (info && info.version ? `v${info.version}` : '새 버전');

  autoUpdater.on('update-available', (info) => {
    notify(`${appName} 업데이트`, `${versionLabel(info)} 을(를) 백그라운드로 내려받고 있습니다.`);
    if (manualCheck) {
      manualCheck = false;
      const current = window();
      if (current) {
        dialog.showMessageBox(current, {
          type: 'info',
          title: '업데이트 확인',
          message: `${versionLabel(info)} 을(를) 내려받고 있습니다.`,
          detail: '다운로드가 끝나면 다시 알려 드립니다. 계속 사용하셔도 됩니다.',
          buttons: ['확인'],
          noLink: true,
        });
      }
    }
  });

  autoUpdater.on('update-not-available', () => {
    if (!manualCheck) return;
    manualCheck = false;
    const current = window();
    if (current) {
      dialog.showMessageBox(current, {
        type: 'info',
        title: '업데이트 확인',
        message: `현재 최신 버전(v${app.getVersion()})을 사용하고 있습니다.`,
        buttons: ['확인'],
        noLink: true,
      });
    }
  });

  autoUpdater.on('download-progress', (progress) => {
    setProgress(Math.max(0.01, progress.percent / 100));
  });

  autoUpdater.on('update-downloaded', async (info) => {
    setProgress(-1);
    downloadedVersion = info.version;
    const current = window();
    if (!current) return;
    const { response } = await dialog.showMessageBox(current, {
      type: 'question',
      title: '업데이트 준비 완료',
      message: `${appName} ${versionLabel(info)} 이(가) 준비되었습니다.`,
      detail: '지금 다시 시작하면 바로 설치됩니다. "나중에"를 선택하면 앱을 닫을 때 자동으로 설치됩니다.',
      buttons: ['나중에', '지금 다시 시작'],
      defaultId: 1,
      cancelId: 0,
      noLink: true,
    });
    if (response === 1) {
      setImmediate(() => autoUpdater.quitAndInstall(true, true));
    } else {
      notify(`${appName} 업데이트`, `${versionLabel(info)} 은(는) 앱을 닫을 때 자동으로 설치됩니다.`);
    }
  });

  autoUpdater.on('error', (error) => {
    setProgress(-1);
    console.error('[updater] 실패:', error);
    if (!manualCheck) return;
    manualCheck = false;
    const current = window();
    if (current) {
      dialog.showMessageBox(current, {
        type: 'warning',
        title: '업데이트 확인 실패',
        message: '업데이트 서버에 연결하지 못했습니다.',
        detail: String((error && error.message) || error),
        buttons: ['확인'],
        noLink: true,
      });
    }
  });

  function check(manual = false) {
    if (!app.isPackaged) {
      if (manual) {
        const current = window();
        if (current) {
          dialog.showMessageBox(current, {
            type: 'info',
            title: '업데이트 확인',
            message: '개발 모드에서는 업데이트를 확인하지 않습니다.',
            buttons: ['확인'],
            noLink: true,
          });
        }
      }
      return;
    }
    if (downloadedVersion) {
      if (manual) {
        const current = window();
        if (current) {
          dialog
            .showMessageBox(current, {
              type: 'question',
              title: '업데이트 준비 완료',
              message: `v${downloadedVersion} 이(가) 이미 내려받아져 있습니다.`,
              detail: '지금 다시 시작하여 설치할까요?',
              buttons: ['나중에', '지금 다시 시작'],
              defaultId: 1,
              cancelId: 0,
              noLink: true,
            })
            .then(({ response }) => {
              if (response === 1) setImmediate(() => autoUpdater.quitAndInstall(true, true));
            });
        }
      }
      return;
    }
    manualCheck = manual;
    autoUpdater.checkForUpdates().catch((error) => {
      console.error('[updater] 확인 실패:', error);
    });
  }

  function start() {
    if (!app.isPackaged) return;
    setTimeout(() => check(false), FIRST_CHECK_DELAY_MS);
    timer = setInterval(() => check(false), CHECK_INTERVAL_MS);
    app.on('before-quit', () => {
      if (timer) clearInterval(timer);
    });
  }

  return {
    start,
    checkManually: () => check(true),
    feedUrl: () => {
      try {
        return require('../package.json').build.publish.url;
      } catch {
        return '';
      }
    },
  };
}

module.exports = { setupAutoUpdater };
