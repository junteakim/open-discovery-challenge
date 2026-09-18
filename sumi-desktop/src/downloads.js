'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { app, shell } = require('electron');

function downloadRoot() {
  try {
    return app.getPath('downloads');
  } catch {
    return app.getPath('userData');
  }
}

// 같은 이름의 파일이 있으면 "문서 (2).pdf" 형태로 자동 회피합니다.
function uniquePath(directory, fileName) {
  const extension = path.extname(fileName);
  const base = path.basename(fileName, extension);
  let candidate = path.join(directory, fileName);
  let index = 2;
  while (fs.existsSync(candidate)) {
    candidate = path.join(directory, `${base} (${index})${extension}`);
    index += 1;
  }
  return candidate;
}

function registerDownloadHandler({ session, getWindow, shouldAsk, notify }) {
  session.on('will-download', (_event, item) => {
    const fileName = item.getFilename();

    if (!shouldAsk()) {
      item.setSavePath(uniquePath(downloadRoot(), fileName));
    }

    const window = getWindow();

    item.on('updated', (_updateEvent, state) => {
      if (!window || window.isDestroyed()) return;
      if (state === 'progressing' && item.getTotalBytes() > 0) {
        window.setProgressBar(item.getReceivedBytes() / item.getTotalBytes());
      }
    });

    item.once('done', (_doneEvent, state) => {
      if (window && !window.isDestroyed()) window.setProgressBar(-1);
      if (state === 'completed') {
        notify('다운로드 완료', `${fileName}\n클릭하면 저장 위치를 엽니다.`, item.getSavePath());
      } else if (state !== 'cancelled') {
        notify('다운로드 실패', fileName, null);
      }
    });
  });
}

function openDownloadFolder() {
  shell.openPath(downloadRoot()).catch((error) => {
    console.error('다운로드 폴더를 열지 못했습니다:', error);
  });
}

module.exports = { registerDownloadHandler, openDownloadFolder, downloadRoot };
