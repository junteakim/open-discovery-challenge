'use strict';

const api = window.desktopShell;
const params = new URLSearchParams(location.search);
const detail = document.getElementById('detail');
const input = document.getElementById('server-url');
const status = document.getElementById('status');

const failedUrl = params.get('url') || '';
const code = params.get('code') || '';
const message = params.get('message') || '';

detail.textContent = [failedUrl, message && `${message}${code ? ` (${code})` : ''}`]
  .filter(Boolean)
  .join('\n');

async function init() {
  if (!api) return;
  const state = await api.getState();
  input.value = state.serverUrl;
}

document.getElementById('retry').addEventListener('click', async () => {
  status.textContent = '다시 연결하는 중…';
  await api.retry();
});

document.getElementById('save').addEventListener('click', async () => {
  const result = await api.setServerUrl(input.value);
  status.textContent = result.ok ? '주소를 저장했습니다. 다시 연결합니다…' : result.error;
});

input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') document.getElementById('save').click();
});

init();
