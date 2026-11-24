import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { SCREEN_IMAGES } from "@/game/fighterAssets";
import type { CharacterId, NetLink } from "@/game/net";
import { TouchControls } from "@/components/game/TouchControls";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Anime Nexus — Goku, Naruto e Luffy" },
      { name: "description", content: "Luta de plataforma 2D com Goku, Naruto e Luffy: treino solo ou duelo online com um amigo." },
      { property: "og:title", content: "Anime Nexus — Goku, Naruto e Luffy" },
      { property: "og:description", content: "Treino solo ou duelo online entre Goku, Naruto e Luffy." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

type Mode = "single" | "multi";
type Screen =
  | { s: "menu" }
  | { s: "select"; mode: Mode }
  | { s: "lobby"; ch: CharacterId }
  | { s: "game"; mode: Mode; ch: CharacterId; net?: NetLink };

function Index() {
  const [screen, setScreen] = useState<Screen>({ s: "menu" });
  return (
    <main className="relative flex h-dvh w-screen items-center justify-center overflow-hidden bg-foreground">
      {screen.s === "menu" && <Menu onPick={(mode) => setScreen({ s: "select", mode })} />}
      {screen.s === "select" && (
        <Select
          onBack={() => setScreen({ s: "menu" })}
          onPick={(ch) => setScreen(screen.mode === "multi" ? { s: "lobby", ch } : { s: "game", mode: "single", ch })}
        />
      )}
      {screen.s === "lobby" && (
        <Lobby ch={screen.ch} onBack={() => setScreen({ s: "menu" })} onReady={(net) => setScreen({ s: "game", mode: "multi", ch: screen.ch, net })} />
      )}
      {screen.s === "game" && (
        <Game mode={screen.mode} ch={screen.ch} net={screen.net} onExit={() => { screen.net?.close(); setScreen({ s: "menu" }); }} />
      )}
    </main>
  );
}

/** Caixa 16:9 que cabe na tela; filhos posicionados em %. */
function Stage({ children }: { children: React.ReactNode }) {
  return <div className="relative aspect-video w-[min(100vw,177.78dvh)]">{children}</div>;
}

/** Tela cheia + paisagem no celular (precisa ser chamado por um toque). */
function goImmersive() {
  if (typeof window === "undefined" || !window.matchMedia("(pointer: coarse)").matches) return;
  const el = document.documentElement;
  void el.requestFullscreen?.().then(() => (screen.orientation as ScreenOrientation & { lock?: (o: string) => Promise<void> }).lock?.("landscape")).catch(() => {});
}

function Menu({ onPick }: { onPick: (m: Mode) => void }) {
  const pick = (m: Mode) => { goImmersive(); onPick(m); };
  return (
    <Stage>
      <img src={SCREEN_IMAGES.menu} alt="Anime Nexus" className="absolute inset-0 h-full w-full select-none" draggable={false} />
      <button aria-label="Singleplayer" className="absolute left-[29.5%] top-[65.5%] h-[10%] w-[41%] cursor-pointer rounded-full" onClick={() => pick("single")} />
      <button aria-label="Multiplayer" className="absolute left-[30.5%] top-[78.5%] h-[10.5%] w-[39%] cursor-pointer rounded-full" onClick={() => pick("multi")} />
    </Stage>
  );
}

const ROSTER: CharacterId[] = ["naruto", "goku", "luffy"];
const NAMES: Record<CharacterId, string> = { naruto: "NARUTO", goku: "GOKU", luffy: "LUFFY" };
/** Posição (%) de cada retrato na arte da seleção. */
const CARD_LEFT: Record<CharacterId, string> = { naruto: "left-[31.4%]", goku: "left-[44.5%]", luffy: "left-[57.2%]" };

export function CharacterPicker({ onPick, onBack, title }: { onPick: (c: CharacterId) => void; onBack?: () => void; title?: string }) {
  const [ch, setCh] = useState<CharacterId | null>(null);
  const step = (d: number) => setCh((c) => ROSTER[(ROSTER.indexOf(c ?? "goku") + d + ROSTER.length) % ROSTER.length] ?? "naruto");
  const hot = "absolute cursor-pointer";
  const selectionImage = ch === "naruto" ? SCREEN_IMAGES.select_naruto_new : ch === "goku" ? SCREEN_IMAGES.select_goku_new : ch === "luffy" ? SCREEN_IMAGES.select_luffy : SCREEN_IMAGES.select_new;
  return (
    <Stage>
      <img src={selectionImage} alt={ch ? `Seleção: ${NAMES[ch]} destacado` : "Seleção de personagem"} className="absolute inset-0 h-full w-full select-none" draggable={false} />
      {ROSTER.map((c) => (
        <button
          key={c}
          aria-label={NAMES[c]}
          aria-pressed={ch === c}
          className={`${hot} ${CARD_LEFT[c]} top-[37.5%] h-[22.5%] w-[11.8%] rounded-sm transition-shadow ${ch === c ? "select-glow" : ""}`}
          onClick={() => setCh(c)}
        />
      ))}
      <button aria-label="Anterior" className={`${hot} left-[27%] top-[44%] h-[10%] w-[4%]`} onClick={() => step(-1)} />
      <button aria-label="Próximo" className={`${hot} left-[69.5%] top-[44%] h-[10%] w-[4%]`} onClick={() => step(1)} />
      <button
        aria-label="Select"
        disabled={!ch}
        className={`${hot} left-[36.5%] top-[77.5%] h-[12.5%] w-[27%] disabled:cursor-not-allowed`}
        onClick={() => ch && onPick(ch)}
      />
      <p className="absolute top-[64%] w-full text-center font-game text-[3.4vmin] text-game-gold drop-shadow-[0_2px_0_oklch(0.2_0.05_30)]">
        {ch ? NAMES[ch] : title ?? "Escolha seu personagem"}
      </p>
      {onBack && <button className="game-btn-sm absolute left-[2%] top-[3%]" onClick={onBack}>← Voltar</button>}
    </Stage>
  );
}

function Select({ onPick, onBack }: { onPick: (c: CharacterId) => void; onBack: () => void }) {
  return <CharacterPicker onPick={onPick} onBack={onBack} />;
}

function Lobby({ ch, onReady, onBack }: { ch: CharacterId; onReady: (n: NetLink) => void; onBack: () => void }) {
  const [code, setCode] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const cancelRef = useRef<() => void>(() => {});
  const attemptRef = useRef(0);
  useEffect(() => () => { attemptRef.current++; cancelRef.current(); }, []);

  const connect = async (hosting: boolean) => {
    if (busy || (!hosting && !code.trim())) return;
    const attempt = ++attemptRef.current;
    cancelRef.current();
    setBusy(true);
    try {
      const net = await import("@/game/net");
      if (attempt !== attemptRef.current) return;
      const c = hosting ? net.makeRoomCode() : code;
      setStatus(hosting ? `Sala ${c} criada. Passe o código para seu amigo. Esperando...` : "Entrando...");
      const { link, cancel } = hosting ? await net.hostRoom(c, ch) : net.joinRoom(c, ch);
      cancelRef.current = cancel;
      const l = await link;
      if (attempt !== attemptRef.current) { l.close(); return; }
      cancelRef.current = () => {};
      onReady(l);
    } catch {
      if (attempt === attemptRef.current) setStatus(hosting ? "Não deu para criar a sala. Tente de novo." : "Sala não encontrada.");
    } finally {
      if (attempt === attemptRef.current) setBusy(false);
    }
  };
  return (
    <Stage>
      <img src={SCREEN_IMAGES.arena} alt="" className="absolute inset-0 h-full w-full object-cover brightness-50" />
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 px-4 text-center">
        <h2 className="font-game text-[4vmin] text-game-gold">MULTIPLAYER</h2>
        <button className="game-btn" disabled={busy} onClick={() => void connect(true)}>CRIAR SALA</button>
        <div className="flex gap-2">
          <input
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="CÓDIGO"
            maxLength={5}
            className="w-36 rounded-md border-2 border-game-gold bg-background px-3 py-2 text-center font-game text-xl text-foreground"
          />
          <button className="game-btn-sm" disabled={busy} onClick={() => void connect(false)}>ENTRAR</button>
        </div>
        <p className="min-h-6 font-game text-lg text-background">{status}</p>
        <button className="game-btn-sm" onClick={onBack}>← Menu</button>
      </div>
    </Stage>
  );
}

type GameHandle = {
  destroy: (a: boolean, b: boolean) => void;
  events: { emit: (e: string, ...args: unknown[]) => void; on: (e: string, f: (...args: never[]) => void) => void };
};

function Game({ mode, ch, net, onExit }: { mode: Mode; ch: CharacterId; net?: NetLink | undefined; onExit: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const gameRef = useRef<GameHandle | null>(null);
  const [current, setCurrent] = useState(ch);
  /** null = partida rolando; senão: resultado e etapa da revanche. */
  const [end, setEnd] = useState<null | { won: boolean; stage: "result" | "pick" | "waiting" }>(null);
  useEffect(() => {
    let game: GameHandle | undefined;
    let cancelled = false;
    import("../game/startGame").then(({ startGame }) => {
      if (cancelled || !ref.current) return;
      game = startGame(ref.current, net ? { mode, character: ch, net } : { mode, character: ch }) as unknown as GameHandle;
      game.events.on("match-end", (won: boolean) => setEnd({ won, stage: "result" }));
      game.events.on("round-ready", (picked: CharacterId) => { setCurrent(picked); setEnd(null); });
      gameRef.current = game;
    });
    return () => {
      cancelled = true;
      game?.destroy(true, false);
      gameRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div className="absolute inset-0">
      <div ref={ref} className="h-full w-full" />
      <div className="absolute right-3 top-3 z-20 flex gap-2">
        {mode === "single" && (
          <button className="game-btn-sm" onClick={() => gameRef.current?.events.emit("spawn-dummy")}>+ Dummy</button>
        )}
        <button className="game-btn-sm" onClick={onExit}>Menu</button>
      </div>
      {!end && <TouchControls character={current} />}
      {end && (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-overlay">
          {end.stage === "pick" ? (
            <CharacterPicker
              title="Revanche: escolha o personagem"
              onPick={(c) => { setEnd({ ...end, stage: "waiting" }); gameRef.current?.events.emit("rematch-pick", c); }}
            />
          ) : (
            <div className="flex flex-col items-center gap-5 text-center">
              <h2 className="font-game text-[8vmin] text-game-gold drop-shadow-[0_4px_0_oklch(0.3_0.1_30)]">
                {end.won ? "VITÓRIA!" : "DERROTA"}
              </h2>
              {end.stage === "waiting" ? (
                <p className="font-game text-[3vmin] text-background">Esperando o outro jogador escolher...</p>
              ) : (
                <div className="flex gap-4">
                  <button className="game-btn" onClick={() => setEnd({ ...end, stage: "pick" })}>REVANCHE</button>
                  <button className="game-btn" onClick={onExit}>SAIR</button>
                </div>
              )}
              {end.stage === "waiting" && <button className="game-btn-sm" onClick={onExit}>Sair</button>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
