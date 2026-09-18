'use strict';

// 이 파일만 바꾸면 다른 사내 웹앱도 같은 셸로 감쌀 수 있습니다.
module.exports = {
  appId: 'com.smc.draftline',
  displayName: 'SMC DraftLine',
  serverUrl: 'http://smc12.synology.me:8080/cad-lite/',

  // 서버가 평문 HTTP라서 브라우저는 WebGPU·클립보드 등 "보안 컨텍스트 전용" API를 막습니다.
  // 앱에서는 이 출처 하나만 보안 컨텍스트로 취급해 GPU 렌더링 백엔드를 쓸 수 있게 합니다.
  treatOriginAsSecure: true,

  window: { width: 1500, height: 940, minWidth: 1024, minHeight: 680 },
  backgroundColor: '#f8f9fa',

  // CAD 내보내기(DXF/SVG/JSON)는 결과물이므로 저장 위치를 매번 묻는 것이 기본값입니다.
  defaults: {
    askDownloadLocation: true,
    zoomLevel: 0,
  },

  // 페이지가 직접 처리하는 단축키. 앱 메뉴 가속기로 가로채면 안 됩니다.
  // Ctrl+S/O/Z/Y/A/C/X/V/P, F3/F7/F8/F9/F12, Space, Delete, Enter
  shortcuts: {
    devTools: 'CmdOrCtrl+Shift+I',
    hardReload: 'CmdOrCtrl+Shift+R',
  },

  // 페이지가 window.open("")으로 여는 인쇄 미리보기 창 크기
  printWindow: { width: 1100, height: 800 },
};
