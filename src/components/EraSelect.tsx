import { useState } from 'react';
import { IonButton, IonContent, IonHeader, IonIcon, IonTitle, IonToolbar } from '@ionic/react';
import { arrowBack, calendar, play } from 'ionicons/icons';
import { addIcons } from 'ionicons';
import { HINTS } from '../lib/hints';
import { ERAS, ERA_LABELS, eraCounts, loadEra, saveEra } from '../lib/game';
import type { EraChoice } from '../lib/game';
import './EraSelect.css';

addIcons({ arrowBack, calendar, play });

interface Props {
  /** Return to the intro screen without starting a game. */
  onBack: () => void;
  /** Start a game drawn from the chosen period. */
  onStart: (era: EraChoice) => void;
}

/**
 * The screen shown before every game: from which decade should the player come?
 * A player who was at Benfica in the 90s and the 2000s can be drawn in either.
 */
export default function EraSelect({ onBack, onStart }: Props) {
  const [last] = useState<EraChoice | null>(() => loadEra());
  const counts = eraCounts(HINTS);
  const total = Object.keys(HINTS).length;

  function start(choice: EraChoice) {
    saveEra(choice);
    onStart(choice);
  }

  return (
    <>
      <IonHeader>
        <IonToolbar>
          <button
            type="button"
            slot="start"
            className="newGame homeBtn"
            data-testid="era-back"
            title="Voltar ao ecrã inicial"
            aria-label="Voltar ao ecrã inicial"
            onClick={onBack}
          >
            <IonIcon icon={arrowBack} />
          </button>
          <IonTitle>Novo Jogo</IonTitle>
        </IonToolbar>
      </IonHeader>

      <IonContent className="eraScreen">
        <div className="era" data-testid="era-select">
          <h1 className="era__title">
            <IonIcon icon={calendar} /> Escolhe a época
          </h1>
          <p className="era__lead">
            De que período queres os jogadores? Só entram os que representaram o Benfica nessa
            década — quem jogou em duas aparece nas duas.
          </p>

          <div className="era__grid" role="group" aria-label="Décadas">
            <button
              type="button"
              data-testid="era-all"
              className={`era__option ${last === 'all' ? 'is-active' : ''}`}
              onClick={() => start('all')}
            >
              <span className="era__option-label">Todas as épocas</span>
              <span className="era__option-count">{total} jogadores</span>
            </button>

            {ERAS.map((era) => {
              const count = counts[era];
              return (
                <button
                  key={era}
                  type="button"
                  data-testid={`era-${era}`}
                  disabled={count === 0}
                  className={`era__option ${last === era ? 'is-active' : ''}`}
                  onClick={() => start(era)}
                >
                  <span className="era__option-label">{ERA_LABELS[era]}</span>
                  <span className="era__option-count">{count} jogadores</span>
                </button>
              );
            })}
          </div>

          <IonButton
            expand="block"
            data-testid="era-start"
            onClick={() => start(last ?? 'all')}
          >
            <IonIcon slot="start" icon={play} /> Começar
          </IonButton>

          <p className="era__note">
            Os jogadores são baralhados e não se repetem até teres passado por todos da época.
          </p>
        </div>
      </IonContent>
    </>
  );
}
