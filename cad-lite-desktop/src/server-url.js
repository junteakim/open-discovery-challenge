'use strict';

const api = window.desktopShell;
const input = document.getElementById('server-url');
const status = document.getElementById('status');

api.getState().then((state) => {
  input.value = state.serverUrl;
  input.focus();
  input.select();
});

async function save() {
  const result = await api.setServerUrl(input.value);
  if (result.ok) {
    api.closeDialog();
  } else {
    status.textContent = result.error;
  }
}

document.getElementById('save').addEventListener('click', save);
document.getElementById('cancel').addEventListener('click', () => api.closeDialog());
document.getElementById('reset').addEventListener('click', async () => {
  const state = await api.getState();
  input.value = state.defaultUrl;
  status.textContent = '';
});

input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') save();
  if (event.key === 'Escape') api.closeDialog();
});
