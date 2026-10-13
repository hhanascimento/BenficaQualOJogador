import { IonBadge, IonButton, IonIcon } from '@ionic/react';
import { trophy, timerOutline, flame, refresh, eye } from 'ionicons/icons';
import { addIcons } from 'ionicons';
import { initialsFor } from '../lib/text';
import type { RoundResult } from '../lib/game';
import { formatTime } from '../lib/game';
import type { PlayerCard } from '../lib/hints';
import './Summary.css';

addIcons({ trophy, timerOutline, flame, refresh, eye });

interface Props {
  card: PlayerCard;
  result: RoundResult;
  seconds: number;
  streak: number;
  resolved: boolean;
  hintsUsed: number;
  onNext: () => void;
  onReplay: () => void;
}

/** The end-of-round recap: the revealed player, the score and the way on. */
export default function Summary({
  card, result, seconds, streak, resolved, hintsUsed, onNext, onReplay,
}: Props) {
  const headline = result.solved ? 'Acertaste!' : 'Jogador revelado';
  const initials = initialsFor(card);
  // The display name is often only the name he was known by, so the reveal also
  // spells out the first + last name when the dataset knows it.
  const fullName = card.fullName?.trim() || null;

  return (
    <div className="summary" data-testid="summary">
      <div className="reveal">
        {card.photo ? (
          <img className="reveal__photo" src={card.photo} alt={`Fotografia de ${card.name}`} />
        ) : (
          <div className="reveal__photo reveal__photo--initials" aria-hidden>{initials}</div>
        )}
        <div className="reveal__info">
          <p className="reveal__name" data-testid="answer">{card.name}</p>
          {fullName ? <p className="reveal__fullname" data-testid="full-name">{fullName}</p> : null}
          {card.position ? (
            <p className="reveal__meta">
              <IonBadge color="primary">{card.position}</IonBadge>
            </p>
          ) : null}
        </div>
      </div>

      <p className="summary__head">
        <IonIcon icon={resolved ? eye : trophy} /> {headline}
      </p>

      <div className="summary__grid">
        <div className="summary__cell">
          <IonIcon icon={trophy} />
          <strong>{result.points}</strong>
          <span>pontos</span>
        </div>
        <div className="summary__cell">
          <IonIcon icon={timerOutline} />
          <strong>{formatTime(seconds)}</strong>
          <span>tempo</span>
        </div>
        <div className="summary__cell">
          <IonIcon icon={flame} />
          <strong>{streak}</strong>
          <span>sequência</span>
        </div>
      </div>

      <ul className="summary__breakdown">
        <li><span>Classificação</span><b>{result.grade}</b></li>
        <li><span>Dicas usadas ({hintsUsed})</span><b>−{result.hintPenalty}</b></li>
        <li><span>1.ª pista</span><b>grátis</b></li>
        <li><span>Tempo ({formatTime(seconds)})</span><b>−{result.timePenalty}</b></li>
        <li><span>Pontuação base</span><b>{result.base}</b></li>
      </ul>

      <div className="summary__actions">
        <IonButton fill="outline" size="small" color="medium" onClick={onReplay}>
          <IonIcon slot="start" icon={refresh} /> Repetir
        </IonButton>
        <IonButton size="small" onClick={onNext}>Próximo Jogador</IonButton>
      </div>
    </div>
  );
}
