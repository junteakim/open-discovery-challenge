'use strict';

const { contextBridge, ipcRenderer } = require('electron');

// 원격 페이지(SUMI 웹앱)에는 어떤 API도 노출하지 않습니다.
// 앱에 내장된 오류 화면(file://)에서만 사용할 수 있습니다.
if (location.protocol === 'file:') {
  contextBridge.exposeInMainWorld('sumiDesktop', {
    getState: () => ipcRenderer.invoke('sumi:get-state'),
    retry: () => ipcRenderer.invoke('sumi:retry'),
    setServerUrl: (value) => ipcRenderer.invoke('sumi:set-server-url', value),
  });
}
