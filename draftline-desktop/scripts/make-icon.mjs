import { writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import pngToIco from 'png-to-ico';

const here = path.dirname(fileURLToPath(import.meta.url));
const source = path.join(here, '..', 'assets', 'app-icon.png');
const target = path.join(here, '..', 'assets', 'icon.ico');

const buffer = await pngToIco(source);
await writeFile(target, buffer);
console.log(`icon.ico 생성 완료: ${target} (${buffer.length} bytes)`);
