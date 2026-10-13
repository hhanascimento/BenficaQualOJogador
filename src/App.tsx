import { useState } from 'react';
import { IonApp } from '@ionic/react';
import Home from './components/Home';
import Help from './components/Help';
import EraSelect from './components/EraSelect';
import Game from './components/Game';
import type { EraChoice } from './lib/game';

/**
 * The app shell. Four screens, one at a time:
 *
 *   home  – the intro screen: the app icon plus "Jogar" / "Instruções"
 *   era   – pick the period a new game is drawn from (a decade, or all of them)
 *   game  – the guessing game (one mystery player per round)
 *   help  – how the game works
 *
 * Only one screen is mounted at a time, so leaving a round stops its clock and
 * the home screen never shows a stale answer. Every new game goes through the
 * era picker; "Novo Jogo" on the board sends the player back there.
 */
type Screen = 'home' | 'era' | 'game' | 'help';

export default function App() {
  const [screen, setScreen] = useState<Screen>('home');
  /** The period the mounted game draws its players from. */
  const [era, setEra] = useState<EraChoice | null>(null);

  return (
    <IonApp>
      {screen === 'home' && (
        <Home onPlay={() => setScreen('era')} onHelp={() => setScreen('help')} />
      )}
      {screen === 'help' && <Help onBack={() => setScreen('home')} />}
      {screen === 'era' && (
        <EraSelect
          onBack={() => setScreen('home')}
          onStart={(choice) => {
            setEra(choice);
            setScreen('game');
          }}
        />
      )}
      {screen === 'game' && era && (
        <Game era={era} onHome={() => setScreen('home')} onNewGame={() => setScreen('era')} />
      )}
    </IonApp>
  );
}
