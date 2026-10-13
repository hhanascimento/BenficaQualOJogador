import type { HintBook } from '../types';

const STATS_KEY = 'qual-o-jogador:stats';
const ERA_KEY = 'qual-o-jogador:era';

function readJSON<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return { ...fallback, ...(JSON.parse(raw) as object) } as T;
  } catch {
    return fallback;
  }
}

function writeJSON(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable (private mode) — the game still works in-memory */
  }
}

/* ------------------------------------------------------------------ *
 * Career stats
 * ------------------------------------------------------------------ */

export interface Stats {
  played: number;
  solved: number;
  streak: number;
  bestStreak: number;
  bestScore: number;
  totalScore: number;
}

export const EMPTY_STATS: Stats = {
  played: 0, solved: 0, streak: 0, bestStreak: 0, bestScore: 0, totalScore: 0,
};

export function loadStats(): Stats {
  return readJSON<Stats>(STATS_KEY, EMPTY_STATS);
}
export function saveStats(s: Stats) {
  writeJSON(STATS_KEY, s);
}

/* ------------------------------------------------------------------ *
 * Scoring — based on the clock and on how many clues were used
 * ------------------------------------------------------------------ */

export interface RoundInput {
  /** Clues on screen when the round ended (the first one is free). */
  hints: number;
  /** Seconds on the clock when the round ended. */
  seconds: number;
  /** The player pressed "Resolver" instead of naming the player. */
  resolved: boolean;
}

export interface RoundResult {
  points: number;
  base: number;
  hintPenalty: number;
  timePenalty: number;
  solved: boolean;
  grade: string;
}

/** A perfect round (no clues, instantly) is worth this. */
const BASE = 1000;
/** Every clue revealed costs a fixed slice of the base score. */
export const HINT_COST = 50;
/** The first clue is on screen from the start and is never charged. */
export const FREE_HINTS = 1;
/** Every second on the clock costs a point. */
export const TIME_COST = 1;

function gradeFor(points: number, solved: boolean): string {
  if (!solved) return 'Sem pontos';
  if (points >= 900) return 'Perfeito';
  if (points >= 700) return 'Excelente';
  if (points >= 450) return 'Bom';
  return 'Fraco';
}

export function scoreRound(input: RoundInput): RoundResult {
  const hintPenalty = Math.max(0, input.hints - FREE_HINTS) * HINT_COST;
  const timePenalty = input.seconds * TIME_COST;
  const solved = !input.resolved;
  const points = solved ? Math.max(0, BASE - hintPenalty - timePenalty) : 0;
  return {
    points: Math.round(points), base: BASE, hintPenalty, timePenalty,
    solved, grade: gradeFor(points, solved),
  };
}

export function applyResult(stats: Stats, result: RoundResult): Stats {
  return {
    played: stats.played + 1,
    solved: stats.solved + (result.solved ? 1 : 0),
    streak: result.solved ? stats.streak + 1 : 0,
    bestStreak: Math.max(stats.bestStreak, result.solved ? stats.streak + 1 : stats.streak),
    bestScore: Math.max(stats.bestScore, result.points),
    totalScore: stats.totalScore + result.points,
  };
}

export function formatTime(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

/* ------------------------------------------------------------------ *
 * Eras — the decades a player was at Benfica
 * ------------------------------------------------------------------ */

export const ERAS = ['1960s', '1970s', '1980s', '1990s', '2000s', '2010s', '2020s'] as const;
export type Era = (typeof ERAS)[number];

export const ERA_LABELS: Record<Era, string> = {
  '1960s': 'Anos 60', '1970s': 'Anos 70', '1980s': 'Anos 80', '1990s': 'Anos 90',
  '2000s': 'Anos 2000', '2010s': 'Anos 2010', '2020s': 'Anos 2020',
};

/** "Todas as épocas" — no decade filter. */
export type EraChoice = Era | 'all';

/** Players whose career at Benfica touches `era` (or all of them for "all"). */
export function playersInEra(book: HintBook, era: EraChoice): string[] {
  const slugs = Object.keys(book);
  if (era === 'all') return slugs;
  return slugs.filter((slug) => (book[slug].eras ?? []).includes(era));
}

/** How many players each decade holds, for the picker counts. */
export function eraCounts(book: HintBook): Record<Era, number> {
  const counts = Object.fromEntries(ERAS.map((e) => [e, 0])) as Record<Era, number>;
  for (const slug of Object.keys(book)) {
    for (const era of new Set(book[slug].eras ?? [])) {
      if (era in counts) counts[era as Era] += 1;
    }
  }
  return counts;
}

export function formatEraLabel(era: EraChoice): string {
  return era === 'all' ? 'Todas as épocas' : ERA_LABELS[era];
}

export function loadEra(): EraChoice | null {
  try {
    const raw = localStorage.getItem(ERA_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as EraChoice;
    if (value === 'all' || (ERAS as readonly string[]).includes(value)) return value;
    return null;
  } catch {
    return null;
  }
}

export function saveEra(era: EraChoice) {
  writeJSON(ERA_KEY, era);
}

/** A Fisher–Yates shuffle, with `avoidFirst` keeping the wrap-around fresh. */
export function shuffled<T>(items: readonly T[], avoidFirst?: T): T[] {
  const deck = [...items];
  for (let i = deck.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }
  if (deck.length > 1 && avoidFirst !== undefined && deck[0] === avoidFirst) {
    [deck[0], deck[1]] = [deck[1], deck[0]];
  }
  return deck;
}
