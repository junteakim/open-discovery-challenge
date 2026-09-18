// Windows 실행 파일 폴더(SUMI.exe + 런타임)를 만드는 스크립트.
// Wine 없이 동작하므로 Linux/macOS에서도 패키징 결과를 확인할 수 있습니다.
// 설치 파일(.exe installer)이 필요하면 Windows에서 `npm run build:win`을 사용하세요.
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { packager } from '@electron/packager';

const here = path.dirname(fileURLToPath(import.meta.url));
const projectDir = path.join(here, '..');

const paths = await packager({
  dir: projectDir,
  out: path.join(projectDir, 'release'),
  platform: 'win32',
  arch: 'x64',
  name: 'SUMI',
  appVersion: process.env.npm_package_version,
  icon: path.join(projectDir, 'assets', 'icon.ico'),
  overwrite: true,
  prune: true,
  ignore: [/^\/release/, /^\/\.git/],
});

console.log(`패키징 완료: ${paths.join(', ')}`);
