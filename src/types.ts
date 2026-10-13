/** One clue about a player, in the order it should be revealed. */
export interface Hint {
  /** Short tag shown on the revealed clue (e.g. "Nacionalidade"). */
  label: string;
  /** The clue itself, already written in pt-PT (e.g. "Tem nacionalidade portuguesa."). */
  text: string;
}

/**
 * A player as the guessing game knows them: what to show when they are finally
 * revealed (photo, career summary) plus the ordered hints. Built by
 * tools/build_hints_wd.py + tools/merge_hints.py into src/data/hints.json.
 */
export interface HintPlayer {
  /** Display name used when the player is revealed. */
  name: string;
  /**
   * The player's first + last name (often the full name), for the reveal: the
   * display name is usually just the name he was known by ("Cruz"). Built by
   * tools/build_full_names.py.
   */
  fullName?: string;
  /** Path to the photo, relative to the app base (e.g. "assets/players/eusebio.jpg"). */
  photo?: string | null;
  position?: string;
  nationality?: string | null;
  /** First and last year at Benfica (used for the era picker). */
  first?: number | null;
  last?: number | null;
  /** Decades at Benfica, e.g. ["1990s", "2000s"]. */
  eras?: string[];
  benficaSeasons?: number | null;
  benficaApps?: number | null;
  benficaGoals?: number | null;
  /** Up to 11 clues, easiest first. */
  hints: Hint[];
}

export type HintBook = Record<string, HintPlayer>;
