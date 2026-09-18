'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { app } = require('electron');
const appConfig = require('../app.config');

const DEFAULT_URL = appConfig.serverUrl;

const DEFAULTS = {
  serverUrl: DEFAULT_URL,
  bounds: { width: appConfig.window.width, height: appConfig.window.height },
  maximized: true,
  zoomLevel: 0,
  askDownloadLocation: true,
  ...appConfig.defaults,
};

let cache = null;
let saveTimer = null;
// --url= / APP_URL 로 지정한 주소는 이번 실행에만 적용하고 파일에 남기지 않습니다.
let sessionUrlOverride = null;

function configPath() {
  return path.join(app.getPath('userData'), 'settings.json');
}

function normalizeUrl(value) {
  if (typeof value !== 'string' || value.trim() === '') return null;
  const raw = value.trim();
  const withScheme = /^https?:\/\//i.test(raw) ? raw : `http://${raw}`;
  try {
    return new URL(withScheme).toString();
  } catch {
    return null;
  }
}

function urlFromCommandLine(argv) {
  const flag = argv.find((arg) => arg.startsWith('--url='));
  return flag ? normalizeUrl(flag.slice('--url='.length)) : null;
}

function load() {
  if (cache) return cache;
  let stored = {};
  try {
    stored = JSON.parse(fs.readFileSync(configPath(), 'utf8'));
  } catch {
    stored = {};
  }
  cache = {
    ...DEFAULTS,
    ...stored,
    bounds: { ...DEFAULTS.bounds, ...(stored && stored.bounds) },
  };
  if (!normalizeUrl(cache.serverUrl)) cache.serverUrl = DEFAULT_URL;
  sessionUrlOverride =
    urlFromCommandLine(process.argv) || normalizeUrl(process.env.DRAFTLINE_URL);
  return cache;
}

function get(key) {
  const values = load();
  if (key === 'serverUrl' && sessionUrlOverride) return sessionUrlOverride;
  return values[key];
}

function set(key, value) {
  if (key === 'serverUrl') sessionUrlOverride = null;
  load()[key] = value;
  scheduleSave();
}

// 창 이동/크기 변경 이벤트는 연속으로 발생하므로 저장을 모아서 처리합니다.
function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    saveTimer = null;
    saveNow();
  }, 400);
}

function saveNow() {
  if (!cache) return;
  if (saveTimer) {
    clearTimeout(saveTimer);
    saveTimer = null;
  }
  try {
    fs.mkdirSync(path.dirname(configPath()), { recursive: true });
    fs.writeFileSync(configPath(), `${JSON.stringify(cache, null, 2)}\n`, 'utf8');
  } catch (error) {
    console.error('설정을 저장하지 못했습니다:', error);
  }
}

module.exports = {
  DEFAULT_URL,
  configPath,
  normalizeUrl,
  get,
  set,
  load,
  saveNow,
};
