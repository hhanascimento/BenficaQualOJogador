import { IonContent, IonHeader, IonIcon, IonTitle, IonToolbar } from '@ionic/react';
import { arrowBack, bulb, calendar, eye, refresh, shuffle, timerOutline, trophy } from 'ionicons/icons';
import { addIcons } from 'ionicons';
import { TOTAL_PLAYERS } from '../lib/hints';
import './Help.css';

addIcons({ arrowBack, bulb, calendar, eye, refresh, shuffle, timerOutline, trophy });

interface Props {
  /** Return to the intro screen. */
  onBack: () => void;
}

const STEPS = [
  'Antes de cada jogo escolhe a época: uma década (Anos 60 … Anos 2020) ou todas. Só entram jogadores que passaram pelo Benfica nessa década.',
  'A cada ronda aparece um jogador escondido. Lê as pistas reveladas e escreve o nome dele no campo de texto.',
  'Escreve o nome completo ou só o apelido — «Eusébio», «Eusébio da Silva Ferreira» ou «Silva Ferreira» encontram o mesmo jogador. Acentos e maiúsculas não contam.',
  'Podes errar quantas vezes quiseres: não há limite de tentativas nem penalização por erro.',
  'A primeira pista aparece logo no início e é gratuita. Carrega em «Mostrar Dica» para revelar as seguintes — todos os jogadores têm 11 pistas, das mais vagas às mais reveladoras.',
  'Quando as pistas acabarem, aparece o botão «Resolve», que desvenda o jogador — e mostra a fotografia dele no fim, tal como um acerto.',
];

const RULES = [
  {
    icon: bulb,
    title: 'Pistas',
    text: 'Todos os jogadores têm 11 pistas sobre a carreira: nacionalidade, posição, época(s) no Benfica, início de carreira, clubes, temporadas/jogos/golos pelo Benfica, internacionalizações e ano de nascimento. A primeira aparece logo e é grátis; cada pista extra custa 50 pontos.',
  },
  {
    icon: timerOutline,
    title: 'Tempo',
    text: 'O cronómetro começa mal a ronda abre. Cada segundo custa 1 ponto, por isso responder depressa compensa.',
  },
  {
    icon: trophy,
    title: 'Pontuação',
    text: 'Uma ronda perfeita, sem revelar pistas extra, vale 1000 pontos. A pontuação final é 1000 − (50 × pistas extra) − segundos. Acertar com poucas pistas e pouco tempo dá a classificação «Perfeito».',
  },
  {
    icon: eye,
    title: 'Resolve',
    text: '«Resolve» desvenda o jogador mas vale 0 pontos — só aparece depois de teres visto todas as pistas.',
  },
  {
    icon: refresh,
    title: 'Repetir',
    text: 'No resumo, «Repetir» recomeça o mesmo jogador e «Próximo Jogador» avança para o seguinte.',
  },
  {
    icon: calendar,
    title: 'Época',
    text: 'O rodapé mostra a época escolhida e quantos jogadores ela tem. Dentro da mesma época, os jogadores são baralhados e não se repetem até os teres jogado todos.',
  },
  {
    icon: shuffle,
    title: 'Novo Jogo',
    text: 'A qualquer momento podes escolher outra época e começar um jogo novo.',
  },
];

/** The "how to play" screen: rules, naming, scoring and the on-screen buttons. */
export default function Help({ onBack }: Props) {
  return (
    <>
      <IonHeader>
        <IonToolbar>
          <button
            type="button"
            slot="start"
            className="newGame homeBtn"
            data-testid="back"
            title="Voltar ao ecrã inicial"
            aria-label="Voltar ao ecrã inicial"
            onClick={onBack}
          >
            <IonIcon icon={arrowBack} />
          </button>
          <IonTitle>Instruções</IonTitle>
        </IonToolbar>
      </IonHeader>

      <IonContent className="helpScreen">
        <div className="help" data-testid="help-content">
          <img className="help__logo" src="assets/qual-o-jogador-logo.svg" alt="Benfica — Qual o Jogador" />
          <h1 className="help__title">Como jogar</h1>
          <p className="help__lead">
            Um jogo sobre a história do Benfica. Em cada ronda tens de adivinhar um jogador a partir
            de pistas sobre a carreira dele.
          </p>

          <h2 className="help__head">Passo a passo</h2>
          <ol className="help__steps">
            {STEPS.map((s) => <li key={s}>{s}</li>)}
          </ol>

          <h2 className="help__head">Regras e pontuação</h2>
          <ul className="help__rules">
            {RULES.map(({ icon, title, text }) => (
              <li key={title}>
                <IonIcon icon={icon} />
                <div>
                  <strong>{title}</strong>
                  <span>{text}</span>
                </div>
              </li>
            ))}
          </ul>

          <h2 className="help__head">Progresso</h2>
          <p className="help__body">
            O progresso fica guardado neste dispositivo. A base de dados tem {TOTAL_PLAYERS}{' '}
            jogadores do Benfica, de 1961 aos dias de hoje. Na barra superior podes sempre voltar ao
            ecrã inicial com a seta à esquerda.
          </p>

          <p className="help__note">
            As pistas foram recolhidas de fontes públicas (Wikipédia e Wikidata) e as fotografias dos
            jogadores provêm de ficheiros públicos, usadas apenas para identificar os jogadores.
          </p>
        </div>
      </IonContent>
    </>
  );
}
