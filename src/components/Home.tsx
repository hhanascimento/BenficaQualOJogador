import { IonButton, IonContent, IonIcon } from '@ionic/react';
import { helpCircle, play } from 'ionicons/icons';
import { addIcons } from 'ionicons';
import { loadStats } from '../lib/game';
import { TOTAL_PLAYERS } from '../lib/hints';
import './Home.css';

addIcons({ play, helpCircle });

interface Props {
  /** Start a game (opens the era picker). */
  onPlay: () => void;
  /** Open the "how to play" screen. */
  onHelp: () => void;
}

/** The intro screen: the Benfica crest + "QUAL O JOGADOR" wordmark lockup,
 *  the promise of the game and the two ways in. */
export default function Home({ onPlay, onHelp }: Props) {
  const stats = loadStats();

  return (
    <IonContent className="homeScreen">
      <div className="home">
        <img className="home__logo" src="assets/qual-o-jogador-logo.svg" alt="" />
        <h1 className="home__srTitle">Benfica — Qual o Jogador</h1>
        <p className="home__tagline">
          Lê as pistas sobre a carreira de um jogador do Benfica e descobre quem é.
          Menos dicas e mais rapidez valem mais pontos.
        </p>

        <div className="home__actions">
          <IonButton expand="block" size="large" data-testid="play" onClick={onPlay}>
            <IonIcon slot="start" icon={play} /> Jogar
          </IonButton>
          <IonButton
            expand="block"
            size="large"
            fill="outline"
            color="medium"
            data-testid="help"
            onClick={onHelp}
          >
            <IonIcon slot="start" icon={helpCircle} /> Instruções
          </IonButton>
        </div>

        {stats.played > 0 && (
          <p className="home__stats">
            {stats.solved}/{stats.played} adivinhados · melhor sequência {stats.bestStreak} ·{' '}
            {stats.totalScore} pontos
          </p>
        )}
        <p className="home__note">{TOTAL_PLAYERS} jogadores na base de dados</p>
      </div>
    </IonContent>
  );
}
