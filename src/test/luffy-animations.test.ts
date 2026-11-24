import { describe, expect, it } from 'vitest';
import {
  LUFFY_CHARGE_FRAMES,
  LUFFY_CHARGE_TEXTURES,
  LUFFY_GEAR_SPECIAL_A_FRAMES,
  LUFFY_GEAR_SPECIAL_B_FRAMES,
} from '../game/luffyAnimationRules';

describe('Luffy replacement animations', () => {
  it('uses all twelve eating poses for each separate form', () => {
    expect(LUFFY_CHARGE_FRAMES).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
    expect(LUFFY_CHARGE_TEXTURES).toEqual({
      normal: 'luffy_charge',
      haki: 'luffy_haki_charge',
      gear: 'luffy_gear_charge',
    });
  });

  it('plays both Gear Second elastic stages once in source order', () => {
    expect(LUFFY_GEAR_SPECIAL_A_FRAMES).toEqual([0, 1, 2]);
    expect(LUFFY_GEAR_SPECIAL_B_FRAMES).toEqual([3, 4, 5, 6, 7]);
  });
});
