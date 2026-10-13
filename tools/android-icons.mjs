/**
 * Android launcher icons, cut from the app's own icon (`public/app-icon.svg`).
 *
 *   node tools/android-icons.mjs
 *
 * Writes every density of, in android/app/src/main/res/:
 *
 *   mipmap-<d>/ic_launcher.png             the icon as designed, for API < 26
 *   mipmap-<d>/ic_launcher_round.png       …the same in a circle, art scaled to
 *                                          the inscribed square so the gold
 *                                          frame is not cut by the round clip
 *   mipmap-<d>/ic_launcher_foreground.png  adaptive-icon foreground: the gold
 *                                          frame and the wordmark, transparent
 *   mipmap-<d>/ic_launcher_background.png  adaptive-icon background: the plate
 *
 * The adaptive layers follow Android's 108dp canvas: the plate maps to the
 * 72dp viewport that every launcher mask shows, so the icon the launcher
 * draws is the plate the app uses. A square frame cannot fit a circular mask
 * at that size, so the adaptive frame is drawn with a larger corner radius
 * (24dp) — it is the one deliberate difference from the on-screen mark.
 *
 * Runs headless Chromium; on a machine without it see tools/browser-setup.sh.
 */
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW || 'playwright');

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const RES = path.join(ROOT, 'android/app/src/main/res');
const FAVICON = path.join(ROOT, 'public/app-icon.svg');

/* density buckets, and the three sizes the icon is drawn at */
const DENSITIES = [['mdpi', 1], ['hdpi', 1.5], ['xhdpi', 2], ['xxhdpi', 3], ['xxxhdpi', 4]];
const LEGACY_DP = 48;
const ADAPTIVE_DP = 108;
const VIEWPORT_DP = 72;          // what a launcher mask actually shows
const INSCRIBED = 1 / Math.SQRT2; // circle -> inscribed square
const ADAPTIVE_FRAME_RX = 171;    // svg units (≈24dp): survives a round mask

/* the favicon is the source of truth; every piece is addressed by shape */
const src = fs.readFileSync(FAVICON, 'utf8');
const PLATE = /<rect width="512" height="512" rx="96" fill="url\(#bgGrad\)"\/>/;
const FRAME = /<rect x="20" y="20" width="472" height="472" rx="76"[^/]*\/>/;
const TEXT = /<g filter="url\(#dropShadow\)">[\s\S]*?<\/g>/;
const DEFS = /<defs>[\s\S]*?<\/defs>/;
for (const [re, what] of [[PLATE, 'plate'], [FRAME, 'frame'], [TEXT, 'wordmark'], [DEFS, 'gradients']]) {
  if (!re.test(src)) throw new Error(`public/app-icon.svg has no ${what} any more — the icons cannot be cut`);
}
const defs = src.match(DEFS)[0];
const text = src.match(TEXT)[0];
/* two plates: the mark's own rounded one for the legacy icon, and a
   full-bleed one for the layers a launcher mask crops */
const plateRounded = src.match(PLATE)[0];
const plateBleed = '<rect width="512" height="512" fill="url(#bgGrad)"/>';
const frame = (rx) => `<rect x="20" y="20" width="472" height="472" rx="${rx}" fill="none" stroke="url(#goldGrad)" stroke-width="6" opacity="0.8"/>`;
const svg = (px, viewBox, body) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" width="${px}" height="${px}">${defs}${body}</svg>`;

/* the four drawings, each at its own pixel size */
const k = VIEWPORT_DP / 512;   // the plate, mapped onto the 72dp viewport
const centred = `translate(54 54) scale(${k}) translate(-256 -256)`;
const drawings = (legacyPx, adaptivePx) => ({
  'ic_launcher.png': svg(legacyPx, '0 0 512 512', `${plateRounded}${frame(76)}${text}`),
  'ic_launcher_round.png': svg(legacyPx, '0 0 512 512',
    `<clipPath id="round"><circle cx="256" cy="256" r="256"/></clipPath>
     <g clip-path="url(#round)">${plateBleed}</g>
     <g transform="translate(256 256) scale(${INSCRIBED}) translate(-256 -256)">${frame(76)}${text}</g>`),
  'ic_launcher_foreground.png': svg(adaptivePx, '0 0 108 108',
    `<g transform="${centred}">${frame(ADAPTIVE_FRAME_RX)}${text}</g>`),
  'ic_launcher_background.png': svg(adaptivePx, '0 0 512 512', plateBleed),
});

async function main() {
  const written = [];
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 512, height: 512 }, deviceScaleFactor: 1 });

  for (const [bucket, scale] of DENSITIES) {
    const dir = path.join(RES, `mipmap-${bucket}`);
    const legacyPx = Math.round(LEGACY_DP * scale);
    const adaptivePx = Math.round(ADAPTIVE_DP * scale);
    for (const [name, markup] of Object.entries(drawings(legacyPx, adaptivePx))) {
      const px = name.includes('foreground') || name.includes('background') ? adaptivePx : legacyPx;
      const png = await page.evaluate(async ({ markup, px }) => {
        const img = new Image();
        await new Promise((res, rej) => {
          img.onload = res;
          img.onerror = () => rej(new Error('an icon drawing failed to load'));
          img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(markup);
        });
        const canvas = document.createElement('canvas');
        canvas.width = px;
        canvas.height = px;
        canvas.getContext('2d').drawImage(img, 0, 0, px, px);
        return canvas.toDataURL('image/png').split(',')[1];
      }, { markup, px });
      const file = path.join(dir, name);
      fs.writeFileSync(file, Buffer.from(png, 'base64'));
      written.push([file, px]);
    }
  }
  await browser.close();

  /* the deliverable is the file: read every one back and check it is the size
     the density bucket promised, in the format Android needs */
  const problems = [];
  for (const [file, px] of written) {
    const buf = fs.readFileSync(file);
    const w = buf.readUInt32BE(16);
    const h = buf.readUInt32BE(20);
    const colour = buf[25];   /* 6 = 32-bit RGBA, which is what an adaptive
                                 layer needs (the corners must be see-through) */
    const name = path.relative(ROOT, file);
    if (w !== px || h !== px) problems.push(`${name}: ${w}x${h}, expected ${px}x${px}`);
    if (colour !== 6) problems.push(`${name}: PNG is not 32-bit RGBA`);
    console.log(`${name.padEnd(58)} ${w}x${h}`);
  }
  if (problems.length) {
    console.error(`\nFAIL (${problems.length})\n${problems.join('\n')}`);
    process.exit(1);
  }
  console.log(`\nPASS: ${written.length} icon files — every density of all four drawings`);
}

await main();
