/** Strip accents, punctuation and casing so guesses match regardless of typing style. */
export function normalize(input: string): string {
  return input
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Common connectors to drop when comparing names ("de", "da", "dos", "van", ...). */
const STOPWORDS = new Set(['de', 'da', 'do', 'dos', 'das', 'e', 'di', 'del', 'la', 'le', 'van', 'von']);

function tokens(name: string): string[] {
  return normalize(name)
    .split(' ')
    .filter((t) => t.length > 0 && !STOPWORDS.has(t));
}

/**
 * A player as the game knows them: the short display name plus any alternate
 * spellings that also identify them. The alternates come from the dataset slug,
 * which is the source page slug and usually carries the first name the display
 * name leaves out ("Grimaldo" ← "alejandro-grimaldo").
 */
export interface KnownPlayer {
  /** Name shown during play (e.g. "Grimaldo"). */
  name: string;
  /** Other names that identify the same player (e.g. "Alejandro Grimaldo"). */
  aliases?: string[];
}

/** Every name that identifies `player`, display name first. */
export function namesFor(player: KnownPlayer): string[] {
  return [player.name, ...(player.aliases ?? [])];
}

/**
 * Readable name held in a dataset slug: "alejandro-grimaldo" →
 * "Alejandro Grimaldo", "joao-manuel-pinto" → "Joao Manuel Pinto". Slugs are
 * stored without accents, which is harmless because matching is
 * accent-insensitive anyway.
 */
export function nameFromSlug(slug: string): string {
  return slug
    .split('-')
    .filter(Boolean)
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(' ');
}

/**
 * The pool of known players for a set of matches: one entry per distinct
 * display name, each carrying the aliases its slug adds. 238 of the 414 names
 * in the current dataset gain an alias this way (e.g. "Grimaldo" also answers
 * to "Alejandro Grimaldo").
 */
/**
 * The alias a dataset slug earns for a player, or '' when it has none to give.
 *
 * An alias exists to carry the name words the display name leaves out
 * ("grimaldo" ← "alejandro-grimaldo"), so a lone slug word such as `leotm` – the
 * source page's shorthand for the player shown as "Léo" – is an internal
 * identifier rather than a name, and must not become one in the game.
 */
export function aliasFromSlug(slug: string): string {
  const name = nameFromSlug(slug);
  return name.includes(' ') ? name : '';
}

export function buildPool(matches: { lineup: { name: string; slug?: string }[] }[]): KnownPlayer[] {
  const byName = new Map<string, KnownPlayer>();
  for (const m of matches) {
    for (const p of m.lineup) {
      const key = normalize(p.name);
      if (!key) continue;
      let known = byName.get(key);
      if (!known) {
        known = { name: p.name, aliases: [] };
        byName.set(key, known);
      }
      const alias = p.slug ? aliasFromSlug(p.slug) : '';
      if (!alias || normalize(alias) === key) continue;
      known.aliases ??= [];
      if (!known.aliases.includes(alias)) known.aliases.push(alias);
    }
  }
  return [...byName.values()].sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * The name rules for one player record, using that record's own slug. Two
 * different players can share a display name in the dataset ("Martins" is
 * three people), so a match must read the alias from the lineup entry it is
 * looking at rather than from the merged pool entry.
 */
export function knownFrom(player: { name: string; slug?: string }): KnownPlayer {
  const alias = player.slug ? aliasFromSlug(player.slug) : '';
  return {
    name: player.name,
    aliases: alias && normalize(alias) !== normalize(player.name) ? [alias] : [],
  };
}

/**
 * Returns true when `guess` identifies `target`.
 *
 * Accepted: an exact name, the full name, any two of its words in any order
 * ("rui costa", "costa rui", "mehdi gonzalez"), a contiguous multi-part name
 * ("di maria"), or a lone surname when no other player in `pool` shares it. Names are the
 * display name plus the player's aliases, so a first + last name that only the
 * source slug carries ("alejandro grimaldo" for the slot shown as "Grimaldo")
 * works too. Matches whole words only, so "silva" never matches "silvares".
 */
export function matchesPlayer(guess: string, target: KnownPlayer, pool: KnownPlayer[]): boolean {
  const gNorm = normalize(guess);
  if (!gNorm) return false;
  const names = namesFor(target).map(normalize).filter(Boolean);
  if (names.length === 0) return false;

  // An exact name always identifies its player – display name or alias. Without
  // this, a player whose name is a single common word would be unreachable: the
  // slot shows "Nélson", but another player's slug ("nelson-semedo") puts that
  // word in the pool too, and the ambiguity rule below would refuse the guess
  // for the very player the slot names.
  if (names.includes(gNorm)) return true;

  // word for word: the whole name, or a contiguous phrase inside it
  const literal = names.some(
    (n) => n === gNorm || n.startsWith(`${gNorm} `) || n.endsWith(` ${gNorm}`) || n.includes(` ${gNorm} `),
  );

  // …or the guess is a selection of the player's name words in any order, which
  // is what lets a first + last name find a name with middle words in between
  const guessWords = tokens(guess);
  if (guessWords.length === 0) return false;
  const nameWords = new Set(names.flatMap(tokens));
  const everyWord = guessWords.every((w) => nameWords.has(w));

  if (!literal && !everyWord) return false;

  // A full or multi-part name is specific enough on its own.
  if (gNorm.split(' ').length > 1 || guessWords.length > 1) return true;

  // A lone word (usually a surname) counts only when no *other* player shares
  // it. Names that add nothing but words this same player already has (a short
  // and a long form of one player) are not competition.
  const [word] = guessWords;
  const ambiguous = pool.some((other) => {
    if (other === target) return false;
    if (normalize(other.name) === normalize(target.name)) return false;
    const otherWords = tokens(namesFor(other).join(' '));
    if (!otherWords.includes(word)) return false;
    return !otherWords.every((t) => nameWords.has(t));
  });
  return !ambiguous;
}

/** Does a partly typed query filter down to this one name? */
function queryHitsName(name: string, query: string): boolean {
  const qNorm = normalize(query);
  if (!qNorm) return false;
  // every word typed matches the start of one of the name's words, in any order
  const qWords = tokens(query);
  const words = tokens(name);
  if (qWords.length > 0 && qWords.every((q) => words.some((w) => w.startsWith(q)))) return true;
  // otherwise fall back to a plain substring, so mid-word typing still suggests
  return normalize(name).includes(qNorm);
}

/** Should this player show up in the suggestion list for what has been typed? */
export function matchesQuery(player: KnownPlayer, query: string): boolean {
  return namesFor(player).some((n) => queryHitsName(n, query));
}

/**
 * The alias that made a suggestion match, or null when the display name alone
 * explains it. Lets the list say *why* it is offering a name the player does
 * not literally contain.
 */
export function aliasHit(player: KnownPlayer, query: string): string | null {
  if (queryHitsName(player.name, query)) return null;
  return (player.aliases ?? []).find((a) => queryHitsName(a, query)) ?? null;
}

/**
 * The fuller name shown to the right of a suggestion.
 *
 * The list always shows the complete name we know for the player — a slot
 * displayed as "de Tomás" is offered as "de Tomás   Raul De Tomas" — so a
 * one-word entry never hides the first name the source slug carries. The alias
 * that actually matched the query wins when there is one (e.g. typing "tomás"
 * against the shared name "Tavares" keeps showing *Tomás Tavares*, not the
 * unrelated first alias). Returns null only when the player is known by a
 * single name and there is nothing more to show.
 */
export function fullerName(player: KnownPlayer, query = ''): string | null {
  const aliases = (player.aliases ?? []).filter(Boolean);
  if (aliases.length === 0) return null;
  return aliasHit(player, query) ?? aliases[0];
}

/**
 * The initials of a player, used both as the hint inside an unknown slot and as
 * the photo fallback: first letter and last letter of the name, e.g.
 * "Costa Pereira" → "CP".
 *
 * The displayed name is usually just the surname ("Cristóvão"), which would
 * give a single letter, so a one-word name is expanded to the fullest name we
 * know — `fullName` when the dataset has it, otherwise the source slug
 * ("helder-cristovao" → "Helder Cristovao" → "HC"). A name already written in
 * two words keeps its own initials ("Bastos Lopes" → "BL"), since that is the
 * name the player has to type.
 */
export function initialsFor(player: { name: string; fullName?: string; slug?: string }): string {
  // only words that actually start with a letter count, so a qualifier such as
  // "Julio Cesar (Defesa)" gives "JC" and never "J("
  const named = (value: string) =>
    value.split(/\s+/).filter((w) => /^\p{L}/u.test(w));
  const display = named(player.name);
  let words = display;
  if (display.length < 2) {
    const full = player.fullName?.trim() || (player.slug ? nameFromSlug(player.slug) : '');
    const fuller = named(full);
    if (fuller.length > 1) words = fuller;
  }
  if (words.length === 0) return '';
  const first = words[0][0] ?? '';
  const last = words.length > 1 ? (words[words.length - 1][0] ?? '') : '';
  return (first + last).toUpperCase();
}

/* ------------------------------------------------------------------ *
 * Suggestion ranking
 * ------------------------------------------------------------------ */

/** How strongly a player matches what has been typed (0 = no match). */
export function queryScore(player: KnownPlayer, query: string): number {
  const qNorm = normalize(query);
  if (!qNorm) return 0;
  const qWords = tokens(query);
  let best = 0;
  for (const name of namesFor(player)) {
    const n = normalize(name);
    const words = tokens(name);
    // the whole name typed out, letters and all
    if (n === qNorm) best = Math.max(best, 100);
    // start of one of the name's words ("grimal" → "Grimaldo", but also
    // "silva" → the alias "Antonio Silva")
    if (words.some((w) => w.startsWith(qNorm))) best = Math.max(best, 70);
    // several words, each starting a name word, any order
    if (qWords.length > 1 && qWords.every((q) => words.some((w) => w.startsWith(q)))) {
      best = Math.max(best, 60);
    }
    // a plain substring, so mid-word typing still suggests ("osta" → "Costa
    // Pereira"). Weakest on purpose: it is also what makes "toni" hit
    // "An*toni*o", so it must never outrank a real prefix.
    if (n.includes(qNorm)) best = Math.max(best, 30);
  }
  return best;
}

const PREFIX_SCORE = 60;

/**
 * The suggestion list for a partly typed name, best match first.
 *
 * A weak mid-word hit must not bury the player who actually starts with what
 * was typed: "toni" matches "Toni" as a word prefix but every "António …" as a
 * substring, and the substring names sort first alphabetically, which is how
 * "Toni" used to never show up. So when any word-prefix match exists, only
 * those are offered; the substring fallback is used when nothing else does.
 */
export function suggestPlayers(pool: KnownPlayer[], query: string, limit = 6): KnownPlayer[] {
  const scored: { player: KnownPlayer; score: number }[] = [];
  for (const player of pool) {
    const score = queryScore(player, query);
    if (score > 0) scored.push({ player, score });
  }
  if (scored.length === 0) return [];
  const strong = scored.filter((x) => x.score >= PREFIX_SCORE);
  const ranked = (strong.length > 0 ? strong : scored).sort(
    (a, b) => b.score - a.score || a.player.name.localeCompare(b.player.name),
  );
  return ranked.slice(0, limit).map((x) => x.player);
}
