import { useEffect, useMemo, useRef, useState } from 'react';
import {
  IonContent, IonHeader, IonToolbar, IonTitle, IonButton,
  IonInput, IonChip, IonIcon, IonProgressBar, IonFooter,
} from '@ionic/react';
import {
  refresh, eye, checkmarkCircle, closeCircle, timerOutline,
  flame, trophy, bulb, shuffle, home, personCircle,
} from 'ionicons/icons';
import { addIcons } from 'ionicons';
import { HINTS, POOL, knownOf } from '../lib/hints';
import type { PlayerCard } from '../lib/hints';
import { matchesPlayer, normalize, suggestPlayers, fullerName } from '../lib/text';
import {
  loadStats, saveStats, scoreRound, applyResult, formatTime, shuffled,
  playersInEra, formatEraLabel, FREE_HINTS,
} from '../lib/game';
import type { Stats, RoundResult, EraChoice } from '../lib/game';
import Summary from './Summary';
import '../App.css';

addIcons({
  refresh, eye, checkmarkCircle, closeCircle, timerOutline, flame, trophy,
  bulb, shuffle, home, personCircle,
});

interface Props {
  /** The period this game's players are drawn from (chosen before the round). */
  era: EraChoice;
  /** Leave the game and go back to the intro screen. */
  onHome: () => void;
  /** Leave the round and choose a different period for the next game. */
  onNewGame: () => void;
}

type Msg = { text: string; kind: 'ok' | 'bad' | 'info' };

export default function Game({ era, onHome, onNewGame }: Props) {
  const pool = useMemo(() => playersInEra(HINTS, era), [era]);

  const [deck, setDeck] = useState(() => shuffled(pool));
  const [index, setIndex] = useState(0);
  const slug = deck[index] ?? pool[0];
  const card: PlayerCard = { slug, ...HINTS[slug] };
  const totalHints = card.hints.length;

  const [revealed, setRevealed] = useState(1);
  const [guess, setGuess] = useState('');
  const [wrong, setWrong] = useState<string[]>([]);
  const [message, setMessage] = useState<Msg | null>(null);
  const [activeIdx, setActiveIdx] = useState(-1);
  const [shake, setShake] = useState(false);

  const [seconds, setSeconds] = useState(0);
  const [finished, setFinished] = useState(false);
  const [resolved, setResolved] = useState(false);
  const [result, setResult] = useState<RoundResult | null>(null);

  const [stats, setStats] = useState<Stats>(() => loadStats());

  const secondsRef = useRef(0);
  const recordedRef = useRef(false);

  /* ---- timer: runs until the round ends, restarts on every new player ---- */
  useEffect(() => {
    if (finished) return;
    const id = window.setInterval(() => {
      secondsRef.current += 1;
      setSeconds(secondsRef.current);
    }, 1000);
    return () => window.clearInterval(id);
  }, [finished, index]);

  /* ---- score the round exactly once, when it ends ---- */
  useEffect(() => {
    if (!finished || recordedRef.current) return;
    recordedRef.current = true;
    const res = scoreRound({ hints: revealed, seconds: secondsRef.current, resolved });
    setResult(res);
    setStats((prev) => {
      const next = applyResult(prev, res);
      saveStats(next);
      return next;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [finished]);

  const suggestions = useMemo(() => {
    if (finished || normalize(guess).length < 2) return [];
    return suggestPlayers(POOL, guess);
  }, [guess, finished]);

  useEffect(() => { setActiveIdx(-1); }, [guess]);

  function resetRound() {
    secondsRef.current = 0;
    recordedRef.current = false;
    setRevealed(1);
    setGuess('');
    setWrong([]);
    setMessage(null);
    setActiveIdx(-1);
    setSeconds(0);
    setFinished(false);
    setResolved(false);
    setResult(null);
    setShake(false);
  }

  function nextPlayer() {
    if (index + 1 < deck.length) {
      setIndex(index + 1);
    } else {
      setDeck(shuffled(pool, deck[deck.length - 1]));
      setIndex(0);
    }
    resetRound();
  }

  function flashShake() {
    setShake(true);
    window.setTimeout(() => setShake(false), 460);
  }

  function submitGuess(value: string) {
    value = value.trim();
    if (!value) return;
    if (matchesPlayer(value, knownOf(card), POOL)) {
      setGuess('');
      setMessage(null);
      setResolved(false);
      setFinished(true);
      return;
    }
    const known = POOL.some((p) => matchesPlayer(value, p, POOL));
    setWrong((w) => [value, ...w].slice(0, 12));
    setMessage(
      known
        ? { text: `${value} não é este jogador.`, kind: 'info' }
        : { text: `Não conheço nenhum jogador chamado “${value}”.`, kind: 'bad' },
    );
    setGuess('');
    flashShake();
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'ArrowDown' && suggestions.length) {
      e.preventDefault();
      setActiveIdx((i) => (i + 1) % suggestions.length);
    } else if (e.key === 'ArrowUp' && suggestions.length) {
      e.preventDefault();
      setActiveIdx((i) => (i - 1 + suggestions.length) % suggestions.length);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIdx >= 0 && suggestions[activeIdx]) submitGuess(suggestions[activeIdx].name);
      else submitGuess(guess);
    } else if (e.key === 'Escape') {
      setActiveIdx(-1);
    }
  }

  function revealHint() {
    setRevealed((r) => Math.min(r + 1, totalHints));
    setMessage(null);
  }

  function resolve() {
    setResolved(true);
    setFinished(true);
    setMessage(null);
  }

  const allHintsShown = revealed >= totalHints;
  const shownHints = card.hints.slice(0, revealed);

  return (
    <>
      <IonHeader>
        <IonToolbar>
          <button
            type="button"
            slot="start"
            className="newGame homeBtn"
            data-testid="home"
            title="Voltar ao ecrã inicial"
            aria-label="Ecrã inicial"
            onClick={onHome}
          >
            <IonIcon icon={home} />
          </button>
          <IonTitle>
            Qual o Jogador
            <span className="titleCount"> {index + 1}/{pool.length}</span>
          </IonTitle>
          <div className="hud" slot="end">
            <button
              type="button"
              className="newGame"
              data-testid="new-game"
              title="Escolhe a época de um jogo novo"
              aria-label="Novo Jogo"
              onClick={onNewGame}
            >
              <IonIcon icon={shuffle} />
              <span className="newGame__label">Novo Jogo</span>
            </button>
            <span className="hud__item" title="Sequência de acertos"><IonIcon icon={flame} />{stats.streak}</span>
            <span className="hud__item" title="Pontuação total"><IonIcon icon={trophy} />{stats.totalScore}</span>
          </div>
        </IonToolbar>
      </IonHeader>

      <IonContent className="game">
        <div className="gameWrap">
          <section className="card mystery" data-testid="mystery">
            <div className="mystery__mark">
              <IonIcon icon={finished ? checkmarkCircle : personCircle} />
            </div>
            <div className="mystery__text">
              <h2>{finished ? card.name : 'Quem é este jogador?'}</h2>
              <p className="mystery__era">
                {formatEraLabel(era)} · {totalHints} {totalHints === 1 ? 'dica' : 'dicas'}
              </p>
            </div>
          </section>

          <section className="card hintsCard" data-testid="hints">
            <h3 className="hints__head">
              <IonIcon icon={bulb} /> Pistas
              <span className="hints__count">{revealed}/{totalHints}</span>
            </h3>
            <ul className="hints__list">
              {shownHints.map((h, i) => (
                <li key={h.label} className={i === shownHints.length - 1 ? 'is-new' : ''}>
                  <span className="hints__label">{h.label}</span>
                  <span className="hints__text">{h.text}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="card controls">
            <div className="statbar">
              <IonProgressBar value={revealed / totalHints} color="primary" />
              <div className="statbar__row">
                <span className={`timer ${finished ? 'timer--done' : ''}`} data-testid="timer">
                  <IonIcon icon={timerOutline} /> {formatTime(seconds)}
                </span>
                <span className="statbar__count">
                  {finished
                    ? <strong className={resolved ? '' : 'solved'}>
                        <IonIcon icon={resolved ? eye : checkmarkCircle} /> {resolved ? 'Revelado' : 'Acertaste!'}
                      </strong>
                    : <>Pistas reveladas: {revealed}/{totalHints}</>}
                </span>
              </div>
            </div>

            {finished && result ? (
              <Summary
                card={card}
                result={result}
                seconds={seconds}
                streak={stats.streak}
                resolved={resolved}
                hintsUsed={Math.max(0, revealed - FREE_HINTS)}
                onNext={nextPlayer}
                onReplay={resetRound}
              />
            ) : (
              <>
                <div className="guessRow">
                  <div className={`guessField ${shake ? 'guessField--shake' : ''}`}>
                    <IonInput
                      className="guessInput"
                      data-testid="guess-input"
                      placeholder="Escreve o nome do jogador…"
                      value={guess}
                      autocapitalize="words"
                      enterkeyhint="done"
                      onIonInput={(e) => setGuess((e.detail.value ?? '') as string)}
                      onKeyDown={onKeyDown}
                    />
                    {guess && (
                      <button
                        type="button"
                        className="guessClear"
                        aria-label="Limpar campo"
                        data-testid="clear-guess"
                        onClick={() => { setGuess(''); setActiveIdx(-1); }}
                      >
                        <IonIcon icon={closeCircle} />
                      </button>
                    )}
                    {suggestions.length > 0 && (
                      <ul className="suggest" data-testid="suggestions">
                        {suggestions.map((p, i) => {
                          const alias = fullerName(p, guess);
                          return (
                            <li key={p.name}>
                              <button
                                type="button"
                                data-name={p.name}
                                className={i === activeIdx ? 'is-active' : ''}
                                onMouseEnter={() => setActiveIdx(i)}
                                onClick={() => submitGuess(p.name)}
                              >
                                <span className="suggest__name">{p.name}</span>
                                {alias && <span className="suggest__alias">{alias}</span>}
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </div>
                  <IonButton data-testid="guess-button" onClick={() => submitGuess(guess)}>
                    Adivinha
                  </IonButton>
                </div>

                <div className="feedback">
                  {message ? (
                    <p className={`msg msg--${message.kind}`} data-testid="message">{message.text}</p>
                  ) : (
                    <p className="msg msg--hint" data-testid="hint">
                      Escreve um nome e carrega em Adivinha
                    </p>
                  )}
                  {wrong.length > 0 && (
                    <div className="found" aria-label="Tentativas erradas">
                      {wrong.map((n) => <IonChip key={n} color="medium" outline>{n}</IonChip>)}
                    </div>
                  )}
                </div>

                <div className="actions">
                  <IonButton fill="outline" size="small" onClick={resetRound}>
                    <IonIcon slot="start" icon={refresh} /> Reiniciar
                  </IonButton>
                  {allHintsShown ? (
                    <IonButton size="small" color="warning" data-testid="resolve" onClick={resolve}>
                      <IonIcon slot="start" icon={eye} /> Resolve
                    </IonButton>
                  ) : (
                    <IonButton size="small" data-testid="hint-button" onClick={revealHint}>
                      <IonIcon slot="start" icon={bulb} /> Mostrar Dica ({revealed}/{totalHints})
                    </IonButton>
                  )}
                </div>
              </>
            )}
          </section>
        </div>
      </IonContent>

      <IonFooter>
        <IonToolbar>
          <p className="footer">
            {formatEraLabel(era)} · {pool.length} jogadores · acertados{' '}
            {stats.solved}/{stats.played} · melhor sequência {stats.bestStreak}
          </p>
        </IonToolbar>
      </IonFooter>
    </>
  );
}
