'use strict';

const { contextBridge, ipcRenderer } = require('electron');

// 원격 페이지(CAD 웹앱)에는 어떤 API도 노출하지 않습니다.
// 앱에 내장된 오류 화면·서버 주소 창(file://)에서만 사용할 수 있습니다.
if (location.protocol === 'file:') {
  contextBridge.exposeInMainWorld('desktopShell', {
    getState: () => ipcRenderer.invoke('shell:get-state'),
    retry: () => ipcRenderer.invoke('shell:retry'),
    setServerUrl: (value) => ipcRenderer.invoke('shell:set-server-url', value),
    closeDialog: () => ipcRenderer.invoke('shell:close-dialog'),
  });
}
