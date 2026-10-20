export const PITCH_STEP = 15;
const EPSILON = 1e-6;

const ICON_TILT = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M8 19h8l-1.6-7H9.6z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M12 9V3M9.5 5.5 12 3l2.5 2.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const ICON_FLAT = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><rect x="7" y="12" width="10" height="7" rx="0.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M12 3v6M9.5 6.5 12 9l2.5-2.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';

export function stepPitch(current, direction, max, step = PITCH_STEP) {
  const ratio = current / step;
  const next = direction > 0
    ? (Math.floor(ratio + EPSILON) + 1) * step
    : (Math.ceil(ratio - EPSILON) - 1) * step;
  return Math.min(max, Math.max(0, next));
}

export class PitchControl {
  constructor({ step = PITCH_STEP, duration = 300 } = {}) {
    this.step = step;
    this.duration = duration;
    this.refresh = this.refresh.bind(this);
  }

  onAdd(map) {
    this.map = map;
    this.container = document.createElement('div');
    this.container.className = 'maplibregl-ctrl maplibregl-ctrl-group pitch-ctrl';
    this.up = this.addButton('pitch-up', 'Incliner la vue', ICON_TILT, 1);
    this.down = this.addButton('pitch-down', 'Redresser la vue', ICON_FLAT, -1);
    map.on('pitch', this.refresh);
    this.refresh();
    return this.container;
  }

  onRemove() {
    this.map.off('pitch', this.refresh);
    this.container.remove();
    this.map = null;
  }

  addButton(className, label, icon, direction) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = className;
    button.title = label;
    button.setAttribute('aria-label', label);
    button.innerHTML = icon;
    button.addEventListener('click', () => this.tilt(direction));
    this.container.appendChild(button);
    return button;
  }

  tilt(direction) {
    const pitch = stepPitch(this.map.getPitch(), direction, this.map.getMaxPitch(), this.step);
    this.map.easeTo({ pitch, duration: this.duration });
  }

  refresh() {
    const pitch = this.map.getPitch();
    this.up.disabled = pitch >= this.map.getMaxPitch() - 0.5;
    this.down.disabled = pitch <= 0.5;
  }
}
