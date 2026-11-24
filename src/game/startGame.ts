import * as Phaser from 'phaser';
import { GameScene, type GameConfig } from './scenes/GameScene';

/** Altura fixa de 540; a largura acompanha a tela (16:9 até 21:9) para preencher o celular deitado. */
export function gameWidthFor(w: number, h: number): number {
  if (!w || !h) return 960;
  return Math.round(Math.min(1260, Math.max(960, (540 * w) / h)));
}

export function startGame(parent: HTMLElement, config: GameConfig): Phaser.Game {
  const game = new Phaser.Game({
    type: Phaser.AUTO,
    parent,
    width: gameWidthFor(parent.clientWidth, parent.clientHeight),
    height: 540,
    backgroundColor: '#5aa0e6',
    pixelArt: true,
    input: { activePointers: 4 },
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
    physics: { default: 'arcade', arcade: { gravity: { x: 0, y: 1500 }, debug: false } },
  });
  game.scene.add('GameScene', GameScene, true, config);
  return game;
}
