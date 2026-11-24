import { useEffect } from "react";
import { pressTouchAction, resetTouchState, touchState, type Action } from "@/game/touch";
import { SCREEN_IMAGES } from "@/game/fighterAssets";
import type { CharacterId } from "@/game/net";

function Btn({ img, action, label, className }: { img: string; action: Action; label: string; className: string }) {
  const set = (v: boolean) => (e: React.PointerEvent) => {
    e.preventDefault();
    if (v) e.currentTarget.setPointerCapture(e.pointerId);
    if (v) pressTouchAction(action);
    else touchState[action] = false;
  };
  return (
    <button
      type="button"
      aria-label={label}
      className={`pointer-events-auto touch-none select-none transition-transform active:scale-90 ${className}`}
      onPointerDown={set(true)}
      onPointerUp={set(false)}
      onLostPointerCapture={set(false)}
      onPointerCancel={set(false)}
      onContextMenu={(e) => e.preventDefault()}
    >
      <img src={img} alt="" draggable={false} className="h-full w-full object-contain" />
    </button>
  );
}

const TRANSFORM_LABELS: Record<CharacterId, [string, string]> = {
  goku: ["Kaioken", "Super Sayajin"],
  naruto: ["Modo Sábio", "Modo 1 cauda"],
  luffy: ["Haki", "Gear Second"],
};

/** HUD de toque (só celular): andar, pular, correr (segurar), ataque, especial, carregar e transformações I (K) / II (G). */
export function TouchControls({ character }: { character: CharacterId }) {
  useEffect(() => {
    const clear = () => resetTouchState();
    window.addEventListener("blur", clear);
    document.addEventListener("visibilitychange", clear);
    return () => {
      clear();
      window.removeEventListener("blur", clear);
      document.removeEventListener("visibilitychange", clear);
    };
  }, []);
  const [t1, t2] = TRANSFORM_LABELS[character];
  const size = "size-[13vmin] max-h-20 max-w-20";
  return (
    <div className="pointer-events-none absolute inset-0 z-10 hidden [@media(pointer:coarse)]:block">
      <div className="absolute bottom-[4vmin] left-[3vmin] flex items-end gap-[2vmin]">
        <Btn img={SCREEN_IMAGES.touch_left} action="left" label="Esquerda" className={size} />
        <Btn img={SCREEN_IMAGES.touch_right} action="right" label="Direita" className={size} />
      </div>
      <div className="absolute bottom-[4vmin] right-[3vmin] grid grid-cols-4 items-end gap-[1.5vmin]">
        <Btn img={SCREEN_IMAGES.touch_k} action="kaioken" label={`Transformar I (${t1})`} className={size} />
        <Btn img={SCREEN_IMAGES.touch_g} action="ssj" label={`Transformar II (${t2})`} className={size} />
        <Btn img={SCREEN_IMAGES.btn_special} action="charge" label="Carregar energia" className={`${size} opacity-90`} />
        <Btn img={SCREEN_IMAGES.touch_jump} action="jump" label="Pular" className={size} />
        <Btn img={SCREEN_IMAGES.touch_run} action="run" label="Correr (segurar)" className={size} />
        <Btn img={SCREEN_IMAGES.touch_special} action="shoot" label="Ataque especial" className={size} />
        <Btn img={SCREEN_IMAGES.touch_punch} action="punch" label="Ataque" className={`${size} col-span-2 justify-self-center`} />
      </div>
    </div>
  );
}
