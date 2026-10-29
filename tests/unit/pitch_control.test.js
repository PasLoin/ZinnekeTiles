import { describe, it, expect, beforeEach } from 'vitest';
import { stepPitch, PitchControl, PITCH_STEP } from '../../www/pitch_control.js';

describe('stepPitch', () => {
  it('avance au cran suivant', () => {
    expect(stepPitch(0, 1, 85)).toBe(PITCH_STEP);
    expect(stepPitch(45, 1, 85)).toBe(60);
    expect(stepPitch(37, 1, 85)).toBe(45);
  });

  it('recule au cran précédent', () => {
    expect(stepPitch(45, -1, 85)).toBe(30);
    expect(stepPitch(37, -1, 85)).toBe(30);
    expect(stepPitch(85, -1, 85)).toBe(75);
  });

  it('reste dans les bornes', () => {
    expect(stepPitch(80, 1, 85)).toBe(85);
    expect(stepPitch(85, 1, 85)).toBe(85);
    expect(stepPitch(5, -1, 85)).toBe(0);
    expect(stepPitch(0, -1, 85)).toBe(0);
  });

  it('tolère les imprécisions flottantes', () => {
    expect(stepPitch(44.9999999, 1, 85)).toBe(60);
    expect(stepPitch(45.0000001, -1, 85)).toBe(30);
  });
});

function fakeMap(pitch = 0, max = 85) {
  const handlers = {};
  return {
    pitch,
    eased: [],
    getPitch() { return this.pitch; },
    getMaxPitch: () => max,
    easeTo(opts) { this.eased.push(opts); this.pitch = opts.pitch; (handlers.pitch || []).forEach((fn) => fn()); },
    on(evt, fn) { (handlers[evt] ||= []).push(fn); },
    off(evt, fn) { handlers[evt] = (handlers[evt] || []).filter((f) => f !== fn); },
    handlers,
  };
}

describe('PitchControl', () => {
  let map;
  let ctrl;
  let el;

  beforeEach(() => {
    document.body.innerHTML = '';
    map = fakeMap();
    ctrl = new PitchControl();
    el = ctrl.onAdd(map);
    document.body.appendChild(el);
  });

  it('crée un groupe de deux boutons accessibles', () => {
    expect(el.classList.contains('maplibregl-ctrl-group')).toBe(true);
    const buttons = el.querySelectorAll('button');
    expect(buttons).toHaveLength(2);
    for (const b of buttons) expect(b.getAttribute('aria-label')).toBeTruthy();
  });

  it('désactive « redresser » à plat', () => {
    expect(el.querySelector('.pitch-down').disabled).toBe(true);
    expect(el.querySelector('.pitch-up').disabled).toBe(false);
  });

  it('incline et redresse par crans', () => {
    el.querySelector('.pitch-up').click();
    expect(map.eased.at(-1).pitch).toBe(15);
    el.querySelector('.pitch-up').click();
    expect(map.pitch).toBe(30);
    el.querySelector('.pitch-down').click();
    expect(map.pitch).toBe(15);
  });

  it('désactive « incliner » au maximum', () => {
    map.easeTo({ pitch: 85 });
    expect(el.querySelector('.pitch-up').disabled).toBe(true);
    expect(el.querySelector('.pitch-down').disabled).toBe(false);
  });

  it('se retire proprement', () => {
    ctrl.onRemove();
    expect(document.querySelector('.pitch-ctrl')).toBeNull();
    expect(map.handlers.pitch).toHaveLength(0);
  });
});
