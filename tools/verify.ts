/**
 * End-to-end checks for the game data and rules.
 *   node tools/verify.ts
 * Node 24 strips the types, so no build step is needed.
 */
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import type { HintBook } from '../src/types.ts';
import {
  scoreRound, applyResult, EMPTY_STATS, formatTime, shuffled,
  eraCounts, playersInEra, ERAS, ERA_LABELS, HINT_COST, FREE_HINTS,
} from '../src/lib/game.ts';
import {
  matchesPlayer, suggestPlayers, normalize, nameFromSlug, initialsFor, fullerName,
} from '../src/lib/text.ts';
import type { KnownPlayer } from '../src/lib/text.ts';

const root = resolve(import.meta.dirname, '..');
let failures = 0;
let checks = 0;

function check(name: string, ok: boolean, detail = '') {
  checks++;
  if (!ok) {
    failures++;
    console.error(`  ✗ ${name}${detail ? ` — ${detail}` : ''}`);
  }
}
function section(title: string) {
  console.log(`\n${title}`);
}

const book = JSON.parse(readFileSync(resolve(root, 'src/data/hints.json'), 'utf8')) as HintBook;
const slugs = Object.keys(book);
const pool: KnownPlayer[] = slugs.map((slug) => {
  const alias = nameFromSlug(slug);
  const differs = alias.toLowerCase() !== book[slug].name.toLowerCase();
  return { name: book[slug].name, aliases: alias.includes(' ') && differs ? [alias] : [] };
});

/* ---------------- dataset ---------------- */
section(`hints dataset (${slugs.length} players)`);
check('has at least 300 players', slugs.length >= 300, `got ${slugs.length}`);

let badHints = 0;
let photoMissing = 0;
let noEra = 0;
for (const slug of slugs) {
  const p = book[slug];
  if (!p.name || !p.hints || p.hints.length === 0 || p.hints.length > 11) badHints++;
  for (const h of p.hints ?? []) {
    if (!h.label || !h.text || !h.text.trim().endsWith('.')) badHints++;
  }
  if (!p.eras || p.eras.length === 0) noEra++;
  if (p.photo && !existsSync(resolve(root, 'public', p.photo))) photoMissing++;
}
check('every player has 1–11 well-formed hints', badHints === 0, `${badHints} problems`);

/* ---------------- reveal name ---------------- */
let badFull = 0;
let missingFull = 0;
for (const slug of slugs) {
  const p = book[slug];
  const full = p.fullName?.trim();
  if (!full) {
    // a player whose slug spells a longer name than the one shown must carry it
    const spelled = nameFromSlug(slug);
    const spelledWords = new Set(normalize(spelled).split(' ').filter(Boolean));
    const shownWords = normalize(p.name).split(' ').filter(Boolean);
    if (spelledWords.size > shownWords.length && normalize(spelled) !== normalize(p.name)) missingFull++;
    continue;
  }
  const words = full.split(/\s+/).filter(Boolean);
  if (words.length < 2) badFull++;
  if (normalize(full) === normalize(p.name)) badFull++;
}
check('every full name spells at least two words', badFull === 0, `${badFull} problems`);
check('the reveal has a full name where the slug adds one', missingFull === 0, `${missingFull} missing`);
check('every player has at least one era', noEra === 0, `${noEra} without eras`);
check('every referenced photo exists', photoMissing === 0, `${photoMissing} missing`);

const erasValid = slugs.every((s) => (book[s].eras ?? []).every((e) => (ERAS as readonly string[]).includes(e)));
check('eras are all known decades', erasValid);

const withEleven = slugs.filter((s) => book[s].hints.length === 11).length;
check('every player has exactly 11 hints', withEleven === slugs.length, `${withEleven}/${slugs.length}`);

/* ---------------- positions ---------------- */
const POSITIONS = ['Guarda-Redes', 'Defesa', 'Médio', 'Avançado'];
const wrongPosition = slugs.filter((s) => !POSITIONS.includes(book[s].position ?? ''));
check('every position is one of the four the game shows', wrongPosition.length === 0,
  wrongPosition.map((s) => `${s}:${book[s].position}`).join(', '));
const wrongClue = slugs.filter((s) => !book[s].hints.some(
  (h) => h.label === 'Posição' && h.text === `Jogava na posição de ${(book[s].position ?? '').toLowerCase()}.`));
check('the position clue matches the position field', wrongClue.length === 0, wrongClue.join(', '));

// Two players matched to the same source page end up with byte-identical
// careers; every player must be distinguishable from every other.
const careers = new Map<string, string>();
let collisions = 0;
for (const slug of slugs) {
  const key = JSON.stringify(book[slug].hints);
  const twin = careers.get(key);
  if (twin) collisions++;
  else careers.set(key, slug);
}
check('no two players share an identical career', collisions === 0, `${collisions} duplicate(s)`);

/* ---------------- eras ---------------- */
section('era picker');
const counts = eraCounts(book);
check('every decade has players', ERAS.every((e) => counts[e] > 0),
  JSON.stringify(counts));
check('"all" returns every player', playersInEra(book, 'all').length === slugs.length);
const someEra: (typeof ERAS)[number] = '1990s';
check('an era returns only its players',
  playersInEra(book, someEra).every((s) => (book[s].eras ?? []).includes(someEra)));
check('two-era players appear in both', slugs.some((s) => (book[s].eras ?? []).length >= 2));
check('era labels cover every decade', ERAS.every((e) => Boolean(ERA_LABELS[e])));

/* ---------------- scoring ---------------- */
section('scoring');
const perfect = scoreRound({ hints: 0, seconds: 0, resolved: false });
check('a perfect round is 1000', perfect.points === 1000 && perfect.solved, JSON.stringify(perfect));
const withHints = scoreRound({ hints: 4, seconds: 100, resolved: false });
check('only hints past the free one are charged',
  withHints.points === 1000 - 3 * HINT_COST - 100, `${withHints.points}`);
check('hint penalty is 50 each', withHints.hintPenalty === 3 * HINT_COST);
check('time penalty is 1 per second', withHints.timePenalty === 100);
const onlyFree = scoreRound({ hints: FREE_HINTS, seconds: 0, resolved: false });
check('the first hint is free', onlyFree.points === 1000 && onlyFree.hintPenalty === 0, JSON.stringify(onlyFree));
const noHints = scoreRound({ hints: 0, seconds: 0, resolved: false });
check('the free hint never becomes a bonus', noHints.points === 1000 && noHints.hintPenalty === 0);
const resolved = scoreRound({ hints: 3, seconds: 40, resolved: true });
check('resolve scores zero and is not solved', resolved.points === 0 && !resolved.solved);
const floored = scoreRound({ hints: 11, seconds: 1200, resolved: false });
check('score never goes below zero', floored.points === 0, `${floored.points}`);
check('grades go from perfect to weak',
  scoreRound({ hints: 0, seconds: 10, resolved: false }).grade === 'Perfeito' &&
  scoreRound({ hints: 11, seconds: 200, resolved: false }).grade === 'Fraco');

const s1 = applyResult(EMPTY_STATS, perfect);
check('a win starts a streak', s1.streak === 1 && s1.solved === 1 && s1.totalScore === 1000);
const s2 = applyResult(s1, resolved);
check('a loss resets the streak but keeps the best', s2.streak === 0 && s2.bestStreak === 1);
check('total score accumulates', s2.totalScore === 1000);

check('formatTime pads correctly', formatTime(0) === '00:00' && formatTime(65) === '01:05');

/* ---------------- shuffling ---------------- */
section('deck');
const deck = shuffled([...slugs], slugs[0]);
check('shuffle keeps every player', deck.length === slugs.length && new Set(deck).size === slugs.length);
check('shuffle avoids repeating the first card', deck[0] !== slugs[0] || slugs.length === 1);

/* ---------------- name matching ---------------- */
section('name matching');
const eusebio: KnownPlayer = pool.find((p) => normalize(p.name) === 'eusebio') ?? { name: 'Eusébio' };
check('exact name matches', matchesPlayer('Eusébio', eusebio, pool));
check('accents are ignored', matchesPlayer('Eusebio', eusebio, pool));
check('a wrong name does not match', !matchesPlayer('Ronaldo', eusebio, pool));
const costa = pool.find((p) => normalize(p.name) === 'costa');
if (costa) {
  check('a surname used by several players is only valid with the first name',
    matchesPlayer('Costa', costa, pool) === false || pool.filter((p) => normalize(p.name) === 'costa').length === 1);
}
const sug = suggestPlayers(pool, 'eus');
check('suggestions find a typed prefix', sug.some((p) => normalize(p.name) === 'eusebio'));
check('initials expand a one-word name', initialsFor({ name: 'Eusébio', slug: 'eusebio' }).length >= 1);
check('fullerName reveals the first name the slug carries',
  fullerName({ name: 'Costa', aliases: ['Rui Costa'] }, 'costa') === 'Rui Costa');

/* ---------------- result ---------------- */
console.log(`\n${checks - failures}/${checks} checks passed`);
if (failures > 0) {
  console.error(`${failures} FAILED`);
  process.exit(1);
}
console.log('all good');
