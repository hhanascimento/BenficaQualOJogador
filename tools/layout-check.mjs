/**
 * Layout acceptance check for the "everything fits the screen" layout.
 *
 * It drives the real app in headless Chromium at a range of viewport sizes and
 * fails if any scroller overflows, the pitch/slots escape their box, two player
 * photos collide, or a hint badge / name label is clipped by the pitch edge.
 *
 *   npm run dev &                                  # app on :3000
 *   PW=/path/to/playwright node tools/layout-check.mjs [url]
 *
 * PW may be omitted when playwright is resolvable from the project.
 */
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW || 'playwright');

const URL = process.argv[2] || 'http://localhost:3000/';

const SIZES = [
  [1440, 900], [1280, 800], [1280, 700], [1024, 768], [900, 900],
  [800, 600], [700, 900], [430, 932], [390, 844], [360, 640], [1280, 560],
];

const probe = async (page) => page.evaluate(() => {
  const c = document.querySelector('ion-content.game');
  const inner = c && c.shadowRoot && c.shadowRoot.querySelector('.inner-scroll');
  const pitch = document.querySelector('.pitch');
  const wrap = document.querySelector('.pitchWrap');
  const r = (el) => { const b = el.getBoundingClientRect(); return { w: +b.width.toFixed(1), h: +b.height.toFixed(1), top: +b.top.toFixed(1), bottom: +b.bottom.toFixed(1) }; };
  const boxes = (sel) => [...document.querySelectorAll(sel)].map((s) => s.getBoundingClientRect());
  const slots = boxes('.slot__photo, .slot__placeholder');
  // the bits that hang off a circle: the hint badge and the name label
  const marks = boxes('.slot__hint, .slot__name');
  const p = pitch ? pitch.getBoundingClientRect() : null;
  const clipped = (list) => (p ? list.filter((s) => s.left < p.left - 1 || s.right > p.right + 1 || s.top < p.top - 1 || s.bottom > p.bottom + 1).length : 0);

  // closest two circles: the slots are sized in cqw, so they must never collide
  let minGap = Infinity;
  for (let i = 0; i < slots.length; i++) {
    for (let j = i + 1; j < slots.length; j++) {
      const a = slots[i], b = slots[j];
      const d = Math.hypot(
        (a.left + a.width / 2) - (b.left + b.width / 2),
        (a.top + a.height / 2) - (b.top + b.height / 2),
      );
      minGap = Math.min(minGap, d - a.width / 2 - b.width / 2);
    }
  }

  return {
    doc: { sh: document.documentElement.scrollHeight, ch: document.documentElement.clientHeight },
    body: { sh: document.body.scrollHeight, ch: document.body.clientHeight },
    content: inner ? { sh: inner.scrollHeight, ch: inner.clientHeight, sw: inner.scrollWidth, cw: inner.clientWidth } : null,
    wrap: wrap ? r(wrap) : null,
    pitch: pitch ? r(pitch) : null,
    outside: clipped(slots),
    outsideMarks: clipped(marks),
    minGap: Number.isFinite(minGap) ? +minGap.toFixed(1) : null,
    slotSize: slots.length ? +slots[0].width.toFixed(1) : null,
    suggest: !!document.querySelector('.suggest'),
  };
});

const fails = [];
const browser = await chromium.launch();

for (const [w, h] of SIZES) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  await page.goto(URL, { waitUntil: 'networkidle' });
  // the app opens on its intro screen; "Jogar" now goes through the era picker,
  // so choose a decade (the widest option list) before the pitch game.
  const play = page.locator('[data-testid="play"]');
  if (await play.count()) await play.first().click();
  await page.waitForSelector('[data-testid="era-select"]', { timeout: 15000 });

  const steps = [];

  // 0. era picker: a scrollable list screen, so it is checked for horizontal
  //    overflow and a full set of options, not for fitting one screen
  const era = await page.evaluate(() => {
    const c = document.querySelector('ion-content.eraScreen');
    const inner = c && c.shadowRoot && c.shadowRoot.querySelector('.inner-scroll');
    const grid = document.querySelector('.era__grid');
    return {
      hScroll: inner ? inner.scrollWidth > inner.clientWidth + 1 : false,
      options: document.querySelectorAll('.era__option').length,
      gridRight: grid ? +grid.getBoundingClientRect().right.toFixed(1) : null,
      vw: window.innerWidth,
    };
  });
  if (era.hScroll) fails.push(`${w}x${h} [era picker]: horizontally scrolls`);
  if (era.options !== 8) fails.push(`${w}x${h} [era picker]: ${era.options} options (expected 8)`);
  if (era.gridRight !== null && era.gridRight > era.vw + 1) {
    fails.push(`${w}x${h} [era picker]: grid overflows viewport (${era.gridRight} > ${era.vw})`);
  }
  console.log(`${w}x${h} [era picker]`.padEnd(30), `${era.options} options`.padEnd(26),
    era.hScroll ? 'FAIL: h-scroll' : era.gridRight !== null && era.gridRight > era.vw + 1 ? 'FAIL: overflow' : 'ok');

  await page.click('[data-testid="era-all"]');
  await page.waitForSelector('.pitch', { timeout: 15000 });

  // 1. initial state
  steps.push(['initial', await probe(page)]);

  // 2. autocomplete open (suggestions must not push the layout around)
  await page.click('[data-testid="guess-input"] input, [data-testid="guess-input"]');
  await page.keyboard.type('dia');
  await page.waitForTimeout(150);
  steps.push(['suggestions open', await probe(page)]);

  // 3. wrong guess -> message, 4. right guess -> chips
  await page.keyboard.press('Enter');
  await page.waitForTimeout(120);
  steps.push(['wrong guess', await probe(page)]);

  // walk the suggestion list until one of them is actually in the XI, so the
  // "found" chips state is really on screen
  const suggested = await page.evaluate(() =>
    [...document.querySelectorAll('.suggest li button')].map((b) => b.dataset.name).filter(Boolean));
  for (const name of suggested) {
    await page.fill('[data-testid="guess-input"] input', '').catch(() => {});
    await page.click('[data-testid="guess-input"] input, [data-testid="guess-input"]');
    await page.keyboard.type(name);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(250);
    const found = await page.evaluate(() => document.querySelectorAll('.found ion-chip').length);
    if (found > 0) break;
  }
  await page.keyboard.press('Escape');
  await page.waitForTimeout(150);
  steps.push(['correct guess', await probe(page)]);

  // 5. round over -> the summary card is the tallest state of the screen
  const reveal = page.locator('[data-testid="give-up"]');
  if (await reveal.count()) {
    await reveal.first().click();
    await page.waitForTimeout(450);
    steps.push(['round finished', await probe(page)]);
  }

  // 6. "Novo Jogo" in the header -> the era picker opens; choose again and the
  //    fresh match must still fit without scrolling
  const newGame = page.locator('[data-testid="new-game"]');
  if (await newGame.count()) {
    await newGame.first().click();
    await page.waitForSelector('[data-testid="era-select"]', { timeout: 15000 });
    await page.click('[data-testid="era-1990"]');
    await page.waitForSelector('.pitch', { timeout: 15000 });
    await page.waitForTimeout(450);
    steps.push(['new game', await probe(page)]);
  }

  // 7. both hints on -> the two badges are the outermost thing on screen
  const hints = page.locator('[data-testid="toggle-initials"]');
  if (await hints.count()) {
    await hints.first().click();
    const numbers = page.locator('[data-testid="toggle-number"]');
    if (await numbers.count()) await numbers.first().click();
    await page.waitForTimeout(300);
    steps.push(['hints on', await probe(page)]);
  }

  for (const [label, m] of steps) {
    const problems = [];
    if (m.doc.sh > m.doc.ch + 1) problems.push(`document scrolls ${m.doc.sh}>${m.doc.ch}`);
    if (m.body.sh > m.body.ch + 1) problems.push(`body scrolls ${m.body.sh}>${m.body.ch}`);
    if (m.content && m.content.sh > m.content.ch + 1) problems.push(`ion-content scrolls ${m.content.sh}>${m.content.ch}`);
    if (m.content && m.content.sw > m.content.cw + 1) problems.push(`ion-content h-scrolls ${m.content.sw}>${m.content.cw}`);
    if (m.wrap && m.wrap.bottom > m.doc.ch + 1) problems.push(`pitchWrap overflows viewport (bottom ${m.wrap.bottom} > ${m.doc.ch})`);
    // the pitch must always be usable; in the post-round recap the summary
    // card takes priority, so a slightly smaller pitch is accepted there
    const floor = label === 'round finished' ? 110 : 140;
    if (m.pitch && m.pitch.w < floor) problems.push(`pitch too small to play (${m.pitch.w}px wide)`);
    if (label === 'suggestions open' && !m.suggest) problems.push('no suggestion list rendered');
    if (label !== 'suggestions open' && label !== 'correct guess' && m.suggest) problems.push('suggestion list stuck open');
    if (m.outside > 0) problems.push(`${m.outside} player photo(s) clipped by the pitch edge`);
    if (m.outsideMarks > 0) problems.push(`${m.outsideMarks} hint badge / name label(s) clipped by the pitch edge`);
    if (m.minGap !== null && m.minGap < -0.5) problems.push(`player photos overlap by ${(-m.minGap).toFixed(1)}px`);
    if (problems.length) fails.push(`${w}x${h} [${label}]: ${problems.join('; ')}`);
    console.log(
      `${w}x${h} [${label}]`.padEnd(30),
      `content ${m.content ? `${m.content.ch}px (sh ${m.content.sh})` : 'n/a'}`.padEnd(26),
      `pitch ${m.pitch ? `${m.pitch.w}x${m.pitch.h}` : 'n/a'}`.padEnd(18),
      `slot ${m.slotSize ?? 'n/a'}px`.padEnd(11),
      `gap ${m.minGap ?? 'n/a'}px`.padEnd(11),
      problems.length ? `FAIL: ${problems.join('; ')}` : 'ok',
    );
  }
  await page.close();
}

await browser.close();
console.log(fails.length ? `\nFAIL (${fails.length})\n${fails.join('\n')}` : '\nPASS: no scrolling at any tested viewport');
process.exit(fails.length ? 1 : 0);
