import { mkdir, readFile, writeFile, copyFile } from 'node:fs/promises';
import { SOURCES } from '../shared/picks.js';

const read = async path => {
  try { return JSON.parse(await readFile(new URL(`../${path}`, import.meta.url), 'utf8')); }
  catch (error) { if (error.code !== 'ENOENT') throw error; return null; }
};
const sources = {};
for (const [sport, { key }] of Object.entries(SOURCES)) {
  sources[sport] = { picks: await read(`data_cache/${key}.json`), performance: await read(`data_cache/${key}_performance.json`) };
}
await mkdir(new URL('../worker/', import.meta.url), { recursive: true });
await mkdir(new URL('../public/', import.meta.url), { recursive: true });
await copyFile(new URL('../data_files/logo.png', import.meta.url), new URL('../public/logo.png', import.meta.url));
await writeFile(new URL('../worker/snapshots.json', import.meta.url), JSON.stringify({
  manifest: await read('data_cache/status_manifest.json'),
  performance: await read('data_files/model_performance.json'), sources,
}));
console.log(`Prepared snapshots for ${Object.keys(sources).length} sports.`);
