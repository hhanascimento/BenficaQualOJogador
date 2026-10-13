/**
 * Google Play store assets: app icon, feature graphic and screenshots.
 *
 *   npm run dev &                          # the app must be served (default :3000)
 *   node tools/store-assets.mjs [url]
 *
 * Everything is composed from the app's own marks so the listing cannot drift
 * from the product: `public/assets/benfica-logo.svg` supplies the crest and the
 * "ONZE INICIAL" wordmark, and the palette (launcher plate #0f1115, pitch green
 * #1f7a34 / #229039, Benfica red #e31c2d) is lifted from the launcher icon and
 * Pitch.css. Nothing here is hand-drawn.
 *
 * The screenshots are the real app, driven the way a player drives it: pick an
 * era, solve half the XI with both hints on, finish the round for the recap.
 *
 * Play's requirements, re-checked against the written files at the end:
 *   app icon        512x512, 32-bit PNG (with alpha), <= 1024 KB
 *   feature graphic 1024x500, JPEG or 24-bit PNG (no alpha)
 *   screenshots     JPEG or 24-bit PNG (no alpha), 9:16 portrait,
 *                   >= 1080px on the short side for large screens,
 *                   <= 3840px on the long side. The Android build is
 *                   portrait-only, so every shot is portrait.
 *
 * Needs headless Chromium; see tools/browser-setup.sh.
 */
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW || 'playwright');

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const URL_ARG = process.argv[2] || 'http://localhost:3000/';
const OUT = path.join(ROOT, 'store');

/* the app's palette, from the source it is drawn from */
const GREEN = '#1f7a34';       // pitch (Pitch.css)
const GREEN_LIGHT = '#229039'; // pitch stripe (Pitch.css)
const RED = '#e31c2d';         // Benfica red (favicon.svg bgGrad)
const GOLD = '#f4c430';        // gold rule (favicon.svg goldGrad)

const MATCHES = JSON.parse(fs.readFileSync(path.join(ROOT, 'src/data/matches.json'), 'utf8'));

/* ------------------------------------------------------------------ *
 * device profiles — 9:16 portrait, the only orientation the app runs
 * ------------------------------------------------------------------ */
const PROFILES = [
  { dir: 'phone',     width: 432, height: 768,  dpr: 2.5, shots: ['home', 'era', 'play', 'hints', 'summary', 'help'] },
  { dir: 'tablet-7',  width: 585, height: 1040, dpr: 2,   shots: ['home', 'era', 'hints', 'summary'] },
  { dir: 'tablet-10', width: 810, height: 1440, dpr: 2,   shots: ['play', 'hints', 'summary', 'help'] },
];

/* Alt text the listing asks for with every graphic (Play: "Include alt text
   with each graphic asset"), written in the store listing's own language. */
const ALT = {
  icon: 'O \u00edcone da aplica\u00e7\u00e3o: BENFICA ONZE INICIAL a branco e dourado sobre uma placa vermelha com filete dourado.',
  graphic: '', // filled in from the graphic's own copy
  home: 'O ecrã inicial: o emblema do clube, o nome ONZE INICIAL e os botões Jogar e Instruções.',
  era: 'O ecrã Novo Jogo: escolher a época, do conjunto todo a cada década, ou um intervalo de anos à medida.',
  play: 'Um jogo a começar: o resultado e a competição da partida, o onze todo por descobrir no relvado e o campo para escrever um nome.',
  hints: 'A mesma partida com as duas dicas ligadas: cada jogador por descobrir mostra as iniciais e o número de camisola.',
  summary: 'Resumo da ronda: pontos, tempo, sequência e a discriminação da pontuação, com o onze todo revelado no relvado.',
  help: 'O ecrã de instruções: como jogar, como os nomes são aceites e como a pontuação é calculada.',
};

/* how much of the XI is on the pitch with both hints on */
const HALF = 6;

/* ---------- fonts for the graphic's own text (Apache-2.0 Roboto) ----
   Same convention as tools/wordmark.py: point ROBOTO at the TTF. */
function fontFile(name) {
  const dirs = [
    process.env.ROBOTO ? path.dirname(process.env.ROBOTO) : null,
    '/tmp/roboto/root/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF',
  ].filter(Boolean);
  for (const dir of dirs) {
    const file = path.join(dir, `${name}.ttf`);
    if (fs.existsSync(file)) return fs.readFileSync(file).toString('base64');
  }
  throw new Error(
    `Roboto (${name}.ttf) not found — the feature graphic needs it for its text.\n` +
    'Set ROBOTO=/path/to/Roboto-Bold.ttf (same convention as tools/wordmark.py).',
  );
}

/** Pull the two marks out of the app's own logo lockup, geometrically. */
async function readMarks(page) {
  const svg = fs.readFileSync(path.join(ROOT, 'public/assets/benfica-logo.svg'), 'utf8');
  await page.setContent(`<body style="margin:0">${svg}</body>`);
  return page.evaluate(() => {
    const root = document.querySelector('svg');
    const paths = [...root.querySelectorAll('path')];
    /* the wordmark is the only path that carries an explicit fill instead of
       one of the crest's .st0..st7 classes */
    const wordmark = paths.filter((p) => !p.getAttribute('class'));
    if (wordmark.length !== 1) {
      throw new Error(`expected one classless path (the wordmark), got ${wordmark.length}`);
    }
    if (wordmark[0].getAttribute('transform')) {
      throw new Error('the wordmark carries a transform — placing it by bbox would be wrong');
    }
    const crest = paths.filter((p) => p !== wordmark[0]);
    const box = (list) => list.reduce((a, p) => {
      const b = p.getBBox();
      return {
        x0: Math.min(a.x0, b.x), y0: Math.min(a.y0, b.y),
        x1: Math.max(a.x1, b.x + b.width), y1: Math.max(a.y1, b.y + b.height),
      };
    }, { x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity });
    const c = box(crest);
    const w = wordmark[0].getBBox();
    return {
      style: (root.querySelector('style') || {}).textContent || '',
      crest: { inner: crest.map((p) => p.outerHTML).join('\n      '), x: c.x0, y: c.y0, w: c.x1 - c.x0, h: c.y1 - c.y0 },
      wordmark: { outer: wordmark[0].outerHTML, x: w.x, y: w.y, w: w.width, h: w.height },
    };
  });
}

/* ---------------------------------------------------------------- *
 * app icon — the app's own icon, `public/app-icon.svg`, squared up
 * for the store. Play's own icon specification asks for a full
 * square with no rounding and no outer shadow because *it* applies
 * the mask (radius 30% of the icon size), so the rounded plate of
 * the on-screen mark is dropped and the gold frame is pulled in far
 * enough that a 153px corner radius cannot bite into it.
 * ---------------------------------------------------------------- */
function buildIcon() {
  const file = path.join(ROOT, 'public/app-icon.svg');
  const svg = fs.readFileSync(file, 'utf8');
  const plate = /<rect width="512" height="512" rx="96" fill="url\(#bgGrad\)"\/>/;
  const frame = /<rect x="20" y="20" width="472" height="472" rx="76"[^/]*\/>/;
  if (!plate.test(svg) || !frame.test(svg)) {
    throw new Error('public/app-icon.svg changed shape — the store icon cannot reshape it');
  }
  return svg
    .replace('width="100%" height="100%"', 'width="512" height="512"')
    .replace(plate, '<rect width="512" height="512" fill="url(#bgGrad)"/>')
    .replace(frame, '<rect x="54" y="54" width="404" height="404" rx="72" fill="none" stroke="url(#goldGrad)" stroke-width="7" opacity="0.85"/>');
}

/* ---------------------------------------------------------------- *
 * feature graphic — 1024x500: the pitch the game is played on, the
 * crest, the wordmark and the promise. Everything sits inside the
 * 50px side crop zones and clear of the centred video play button.
 * ---------------------------------------------------------------- */
function buildFeatureGraphic(marks) {
  const W = 1024;
  const H = 500;
  const crestH = 300;
  const crestW = (crestH * marks.crest.w) / marks.crest.h;
  const crestX = 96;
  const crestY = (H - crestH) / 2;

  const markW = 470;
  const markScale = markW / marks.wordmark.w;
  const markX = 452;
  const markY = 186;
  const markH = marks.wordmark.h * markScale;

  const from = MATCHES.reduce((a, m) => Math.min(a, +m.date.slice(0, 4)), Infinity);
  const lines = [
    'Adivinha o onze inicial em jogos hist\u00f3ricos',
    `${MATCHES.length} jogos \u00b7 de ${from} aos dias de hoje`,
  ];

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
    <style>${marks.style}</style>
    <defs>
      <linearGradient id="grass" x1="0" y1="0" x2="0.35" y2="1">
        <stop offset="0%" stop-color="${GREEN_LIGHT}"/>
        <stop offset="55%" stop-color="${GREEN}"/>
        <stop offset="100%" stop-color="#14512a"/>
      </linearGradient>
      <radialGradient id="glow" cx="24%" cy="50%" r="42%">
        <stop offset="0%" stop-color="#ffffff" stop-opacity="0.16"/>
        <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="pool" cx="50%" cy="50%" r="50%">
        <stop offset="35%" stop-color="#06280f" stop-opacity="0.5"/>
        <stop offset="100%" stop-color="#06280f" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="vignette" cx="50%" cy="50%" r="76%">
        <stop offset="60%" stop-color="#000000" stop-opacity="0"/>
        <stop offset="100%" stop-color="#000000" stop-opacity="0.26"/>
      </radialGradient>
      <linearGradient id="gold" x1="0" y1="0" x2="1" y2="0.6">
        <stop offset="0%" stop-color="#fff4b8"/>
        <stop offset="55%" stop-color="${GOLD}"/>
        <stop offset="100%" stop-color="#ddab1f"/>
      </linearGradient>
      <linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="${RED}"/>
        <stop offset="100%" stop-color="${GOLD}"/>
      </linearGradient>
    </defs>

    <rect width="${W}" height="${H}" fill="url(#grass)"/>
    ${[0, 1, 2, 3, 4, 5, 6, 7].map((i) => `<rect x="${i * 128}" y="0" width="64" height="${H}" fill="${GREEN_LIGHT}" opacity="0.45"/>`).join('\n    ')}

    <!-- the pitch itself, faintly: frame, halfway line, centre circle -->
    <g fill="none" stroke="#ffffff" stroke-opacity="0.24" stroke-width="3">
      <rect x="26" y="26" width="${W - 52}" height="${H - 52}" rx="6"/>
      <line x1="${W / 2}" y1="26" x2="${W / 2}" y2="${H - 26}"/>
      <circle cx="${W / 2}" cy="${H / 2}" r="96"/>
    </g>
    <circle cx="${W / 2}" cy="${H / 2}" r="4" fill="#ffffff" fill-opacity="0.3"/>
    <rect width="${W}" height="${H}" fill="url(#glow)"/>
    <!-- a pool of shade under the crest, so it reads against the green -->
    <ellipse cx="${crestX + crestW / 2}" cy="${H / 2}" rx="${crestW * 0.78}" ry="${crestH * 0.74}" fill="url(#pool)"/>
    <rect width="${W}" height="${H}" fill="url(#vignette)"/>

    <g transform="translate(${crestX} ${crestY}) scale(${(crestH / marks.crest.h).toFixed(5)}) translate(${-marks.crest.x} ${-marks.crest.y})">
      ${marks.crest.inner}
    </g>

    <text x="${markX}" y="168" font-family="RobotoBold" font-size="31" letter-spacing="7"
          fill="#ffffff" fill-opacity="0.92">BENFICA</text>
    <g transform="translate(${markX} ${markY}) scale(${markScale.toFixed(5)}) translate(${-marks.wordmark.x} ${-marks.wordmark.y})">
      <g fill="url(#gold)">${marks.wordmark.outer}</g>
    </g>
    <rect x="${markX}" y="${(markY + markH + 18).toFixed(1)}" width="${markW}" height="7" rx="3.5" fill="url(#rule)"/>
    <text x="${markX}" y="${(markY + markH + 68).toFixed(1)}" font-family="RobotoRegular" font-size="27"
          fill="#ffffff" fill-opacity="0.95">${lines[0]}</text>
    <text x="${markX}" y="${(markY + markH + 104).toFixed(1)}" font-family="RobotoRegular" font-size="22"
          fill="#ffffff" fill-opacity="0.86">${lines[1]}</text>
  </svg>`;

  ALT.graphic = `Emblema do Benfica ao lado do logótipo ONZE INICIAL num relvado verde: ${lines[0]} — ${lines[1]}.`;
  return { svg, lines };
}

/* ---------------------------------------------------------------- *
 * screenshots — drive the real app and shoot the states a player sees
 * ---------------------------------------------------------------- */
/* the native input lives inside ion-input's shadow root, and Playwright's CSS
   engine pierces it; the host itself is not fillable */
const INPUT = '[data-testid="guess-input"] input';

/**
 * The XI on the pitch. Every slot carries its player's name, so the dataset
 * lookup is only needed when a name has to be typed — and two matches that
 * share a line-up are interchangeable here, which is why this cannot tie.
 */
async function readLineup(page) {
  const names = await page.evaluate(() =>
    [...document.querySelectorAll('[data-testid^="slot-"]')]
      .map((s) => s.getAttribute('data-testid').slice('slot-'.length)));
  if (names.length !== 11) throw new Error(`expected 11 slots, got ${names.length}`);
  return names;
}

/**
 * Type one name and wait for it to land on the pitch.
 *
 * The pause before Enter is not decoration: ion-input reports the typed value
 * through its own event, so pressing Enter too early submits the previous
 * guess — the round would then refuse a name that is on the pitch.
 */
async function guess(page, name, expected) {
  await page.click(INPUT);
  await page.fill(INPUT, '');
  await page.keyboard.type(name, { delay: 20 });
  await page.waitForTimeout(400);
  await page.keyboard.press('Enter');
  /* count the pitch, not the chips: the chip list is replaced by the recap on
     the eleventh player, so it never reaches 11 */
  await page.waitForFunction(
    (n) => document.querySelectorAll('.slot--revealed').length >= n,
    expected,
    { timeout: 15000 },
  );
}

async function captureStory(page, shots) {
  const taken = {};
  const shot = async (state) => { taken[state] = await page.screenshot(); };

  await page.goto(URL_ARG, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="play"]', { timeout: 20000 });
  if (shots.includes('home')) await shot('home');

  await page.click('[data-testid="play"]');
  await page.waitForSelector('[data-testid="era-select"]', { timeout: 20000 });
  if (shots.includes('era')) await shot('era');

  await page.click('[data-testid="era-all"]');
  await page.waitForSelector('.pitch', { timeout: 20000 });
  /* let the clock tick past 00:00 so the timer is not a zero */
  await page.waitForTimeout(2100);
  if (shots.includes('play')) await shot('play');

  /* solve the first half of the XI, in the order the slots are dealt */
  const lineup = await readLineup(page);
  for (let i = 0; i < HALF; i++) await guess(page, lineup[i], i + 1);

  /* both hints on: the badges only show on the slots that are still empty */
  await page.click('[data-testid="toggle-initials"]');
  await page.click('[data-testid="toggle-number"]');
  try {
    await page.waitForFunction(
      () => document.querySelectorAll('.slot__hint--initials').length > 0
        && document.querySelectorAll('.slot__hint--number').length > 0,
      undefined,
      { timeout: 10000 },
    );
  } catch {
    const state = await page.evaluate(() => ({
      toggles: [...document.querySelectorAll('.toggle')].map((t) => t.className),
      hiddenSlots: document.querySelectorAll('.slot--hidden').length,
      badges: document.querySelectorAll('.slot__hint').length,
      settings: !!document.querySelector('[data-testid="settings"]'),
    }));
    throw new Error(`the hint badges did not appear: ${JSON.stringify(state)}`);
  }
  await page.waitForTimeout(300);
  if (shots.includes('hints')) await shot('hints');

  /* finish the round: the recap is the real scored one */
  for (let i = HALF; i < lineup.length; i++) await guess(page, lineup[i], i + 1);
  await page.waitForSelector('[data-testid="summary"]', { timeout: 15000 });
  await page.waitForTimeout(400);
  if (shots.includes('summary')) await shot('summary');

  /* and the rules screen */
  await page.click('[data-testid="home"]');
  await page.waitForSelector('[data-testid="play"]', { timeout: 15000 });
  await page.click('[data-testid="help"]');
  await page.waitForSelector('[data-testid="help-content"]', { timeout: 15000 });
  await page.waitForTimeout(300);
  if (shots.includes('help')) await shot('help');

  return taken;
}

/* ------------------------------------------------------------------ *
 * the deliverable is the file, not the run: read every asset back and
 * hold it against Play's requirements
 * ------------------------------------------------------------------ */
function pngHead(file) {
  const buf = fs.readFileSync(file);
  const sig = [137, 80, 78, 71, 13, 10, 26, 10];
  if (!sig.every((b, i) => buf[i] === b)) throw new Error(`${file}: not a PNG`);
  return {
    bytes: buf.length,
    width: buf.readUInt32BE(16),
    height: buf.readUInt32BE(20),
    depth: buf[24],
    colour: buf[25],   // 2 = truecolour (24-bit), 6 = truecolour + alpha (32-bit)
  };
}

const files = [];

function check() {
  const problems = [];
  const rows = [];
  const note = (name, file, ok, detail) => {
    rows.push([name, detail, ok ? 'ok' : 'FAIL']);
    if (!ok) problems.push(`${name}: ${detail}`);
  };

  for (const file of files) {
    const name = path.relative(OUT, file).replace(/\\/g, '/');
    const h = pngHead(file);
    const kb = (h.bytes / 1024).toFixed(0);
    const ratio = h.width / h.height;
    const detail = `${h.width}x${h.height}  ${h.depth * (h.colour === 6 ? 4 : 3)}-bit PNG  ${kb} KB`;
    const spec = [];

    if (name.startsWith('app-icon')) {
      if (h.width !== 512 || h.height !== 512) spec.push('icon must be 512x512');
      if (h.colour !== 6) spec.push('icon must be 32-bit PNG with alpha');
      if (h.bytes > 1024 * 1024) spec.push('icon must be <= 1024 KB');
    } else {
      if (h.colour !== 2) spec.push('must be 24-bit PNG without alpha');
      if (name.startsWith('feature-graphic')) {
        if (h.width !== 1024 || h.height !== 500) spec.push('feature graphic must be 1024x500');
      } else {
        /* the general rule is at most 2:1; 9:16 is what the large-screen
           buckets and the game-recommendation formats ask for, so hold every
           shot to it */
        if (Math.abs(ratio - 9 / 16) > 0.0005) {
          spec.push(`must be 9:16 portrait (is ${h.width}:${h.height})`);
        }
        if (Math.min(h.width, h.height) < 320 || Math.max(h.width, h.height) > 3840) {
          spec.push('dimensions must be within 320..3840 px');
        }
        if (name.startsWith('tablet') && Math.min(h.width, h.height) < 1080) {
          spec.push('large-screen screenshots must be >= 1080 px on the short side');
        }
      }
    }
    note(name, file, spec.length === 0, spec.length ? `${detail} — ${spec.join('; ')}` : detail);
  }

  console.log('');
  for (const [name, detail, verdict] of rows) {
    console.log(`${verdict.padEnd(5)} ${name.padEnd(28)} ${detail}`);
  }
  const total = files.reduce((a, f) => a + fs.statSync(f).size, 0);
  console.log(`\n${files.length} assets, ${(total / 1024 / 1024).toFixed(1)} MB total`);
  if (problems.length) {
    console.error(`\nFAIL (${problems.length})\n${problems.join('\n')}`);
    process.exit(1);
  }
  console.log('\nPASS: every asset meets the Google Play requirement it is written for');
}

async function main() {
  fs.rmSync(OUT, { recursive: true, force: true });
  fs.mkdirSync(OUT, { recursive: true });

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1024, height: 500 } });

  const marks = await readMarks(page);
  const fontCss = Object.entries({ RobotoBold: fontFile('Roboto-Bold'), RobotoRegular: fontFile('Roboto-Regular') })
    .map(([family, b64]) => `@font-face{font-family:${family};src:url(data:font/ttf;base64,${b64}) format('truetype')}`)
    .join('\n');

  /* ---- app icon: 512x512, 32-bit PNG with alpha ---- */
  const iconB64 = await page.evaluate(async ({ svg, size }) => {
    const img = new Image();
    await new Promise((res, rej) => {
      img.onload = res;
      img.onerror = () => rej(new Error('the icon SVG failed to load'));
      img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
    });
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    canvas.getContext('2d').drawImage(img, 0, 0, size, size);
    return canvas.toDataURL('image/png').split(',')[1];
  }, { svg: buildIcon(), size: 512 });
  files.push(path.join(OUT, 'app-icon-512.png'));
  fs.writeFileSync(files[files.length - 1], Buffer.from(iconB64, 'base64'));

  /* ---- feature graphic: 1024x500, no alpha ---- */
  const graphic = buildFeatureGraphic(marks);
  await page.setContent(`<style>html,body{margin:0;padding:0;overflow:hidden}${fontCss}</style>${graphic.svg}`);
  await page.evaluate(() => document.fonts.ready);
  files.push(path.join(OUT, 'feature-graphic-1024x500.png'));
  await page.screenshot({ path: files[files.length - 1] });

  /* ---- screenshots ---- */
  for (const profile of PROFILES) {
    const context = await browser.newContext({
      viewport: { width: profile.width, height: profile.height },
      deviceScaleFactor: profile.dpr,
    });
    const shotPage = await context.newPage();
    const shots = await captureStory(shotPage, profile.shots);
    const dir = path.join(OUT, profile.dir);
    fs.mkdirSync(dir, { recursive: true });
    profile.shots.forEach((state, i) => {
      const file = path.join(dir, `${String(i + 1).padStart(2, '0')}-${state}.png`);
      fs.writeFileSync(file, shots[state]);
      files.push(file);
    });
    await context.close();
  }

  await browser.close();
  fs.writeFileSync(path.join(OUT, 'README.txt'), readme());
  check();
}

function readme() {
  const rows = files.map((file) => {
    const name = path.relative(OUT, file).replace(/\\/g, '/');
    const base = path.basename(file, '.png');
    const state = name.startsWith('app-icon') ? 'icon'
      : name.startsWith('feature-graphic') ? 'graphic'
        : base.slice(base.indexOf('-') + 1);
    const h = pngHead(file);
    return `  ${name.padEnd(30)} ${`${h.width}x${h.height}`.padEnd(11)} ${`${Math.round(h.bytes / 1024)} KB`.padEnd(7)} ${ALT[state] || ''}`;
  });

  return `Google Play store assets \u2014 Benfica Onze Inicial

Ícone da aplicação ................ app-icon-512.png
Gráfico de funcionalidades ........ feature-graphic-1024x500.png
Imagens do telemóvel .............. phone/
Capturas de ecrã do tablet de 7 ... tablet-7/
Imagem em tablet de 10 polegadas .. tablet-10/

One line per file, with the alt text to paste beside it in the Play Console:

  file                           size        weight  alt text
${rows.join('\n')}

Every screenshot is the real app and every one is portrait 9:16: the Android
build is portrait-only (MainActivity locks it, and appCategory=game keeps that
lock on large screens), so that is how the game looks on a phone and on a
tablet. A landscape shot would be a picture of something the app never does.

Generated by tools/store-assets.mjs \u2014 see README.md to re-run it.
`;
}

await main();
