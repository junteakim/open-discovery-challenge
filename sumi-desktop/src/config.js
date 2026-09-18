'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { app } = require('electron');

const DEFAULT_URL = 'https://smc12.synology.me:9443/';

const DEFAULTS = {
  serverUrl: DEFAULT_URL,
  bounds: { width: 1280, height: 860 },
  maximized: false,
  zoomLevel: 0,
  askDownloadLocation: false,
  closeToTray: false,
  allowInsecureCertificate: false,
};

let cache = null;
let saveTimer = null;
// --url= / SUMI_URL 로 지정한 주소는 이번 실행에만 적용하고 파일에 남기지 않습니다.
let sessionUrlOverride = null;

function configPath() {
  return path.join(app.getPath('userData'), 'settings.json');
}

function normalizeUrl(value) {
  if (typeof value !== 'string' || value.trim() === '') return null;
  const raw = value.trim();
  const withScheme = /^https?:\/\//i.test(raw) ? raw : `https://${raw}`;
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
  sessionUrlOverride = urlFromCommandLine(process.argv) || normalizeUrl(process.env.SUMI_URL);
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

// Window move/resize fires continuously, so writes are coalesced.
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
