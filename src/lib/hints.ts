import book from '../data/hints.json';
import type { HintBook, HintPlayer } from '../types';
import { nameFromSlug } from './text';
import type { KnownPlayer } from './text';

/** The whole clue book, keyed by the dataset slug. */
export const HINTS = book as unknown as HintBook;

export interface PlayerCard extends HintPlayer {
  slug: string;
}

/** The clue book as a list, each entry carrying its slug. */
export const PLAYERS: PlayerCard[] = Object.entries(HINTS)
  .map(([slug, p]) => ({ slug, ...p }))
  .sort((a, b) => a.name.localeCompare(b.name));

/**
 * Every player the game can ask about, in the name pool the text rules use
 * (see lib/text.ts). The slug usually carries the first name the display name
 * leaves out ("rui-costa" → "Rui Costa" for the slot shown as "Costa"), so it
 * becomes an alias and a first + last name guess still lands.
 */
export const POOL: KnownPlayer[] = PLAYERS.map((p) => {
  const alias = nameFromSlug(p.slug);
  const differs = alias.toLowerCase() !== p.name.toLowerCase();
  return { name: p.name, aliases: alias.includes(' ') && differs ? [alias] : [] };
});

export const TOTAL_PLAYERS = PLAYERS.length;

/** The player's own name rules (display name + the alias its slug gives). */
export function knownOf(card: PlayerCard): KnownPlayer {
  const alias = nameFromSlug(card.slug);
  const differs = alias.toLowerCase() !== card.name.toLowerCase();
  return { name: card.name, aliases: alias.includes(' ') && differs ? [alias] : [] };
}
