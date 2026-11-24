export type LuffyForm = 'normal' | 'haki' | 'gear';

export const LUFFY_CHARGE_TEXTURES: Record<LuffyForm, string> = {
  normal: 'luffy_charge',
  haki: 'luffy_haki_charge',
  gear: 'luffy_gear_charge',
};

export const LUFFY_CHARGE_FRAMES = Array.from({ length: 12 }, (_, frame) => frame);
export const LUFFY_GEAR_SPECIAL_A_FRAMES = [0, 1, 2];
export const LUFFY_GEAR_SPECIAL_B_FRAMES = [3, 4, 5, 6, 7];
