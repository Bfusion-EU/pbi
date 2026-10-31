// One-off: renders the command-center rail icons (Tabler outline) to 96 px PNGs.
// Usage (from a scratch folder):  npm i @resvg/resvg-js @tabler/icons  &&  node <path>/make_icons.mjs <outDir>
import { Resvg } from '@resvg/resvg-js';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';

const require = createRequire(path.join(process.cwd(), 'x.js'));
const iconDir = path.dirname(require.resolve('@tabler/icons/outline/layout-dashboard.svg'));
const ICONS = { cc: 'layout-dashboard', exec: 'crown', portfolio: 'briefcase', finance: 'coin-euro',
  resources: 'users', schedule: 'calendar-time', risk: 'alert-triangle', benefits: 'trending-up',
  governance: 'shield-check' };
const COLOURS = { grey: '#8C98B3', white: '#FFFFFF' };
const out = process.argv[2];
mkdirSync(out, { recursive: true });
for (const [key, file] of Object.entries(ICONS)) {
  const svg = readFileSync(path.join(iconDir, `${file}.svg`), 'utf8');
  for (const [cname, hex] of Object.entries(COLOURS)) {
    const png = new Resvg(svg.replaceAll('currentColor', hex), { fitTo: { mode: 'width', value: 96 } }).render().asPng();
    writeFileSync(path.join(out, `rail-${key}-${cname}.png`), png);
  }
}
console.log('done');
