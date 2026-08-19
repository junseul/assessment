window.createGameProgress = function (target, total, durationMs, unit) {
  const panel = document.createElement('div');
  const count = document.createElement('strong');
  const time = document.createElement('span');
  const startedAt = performance.now();
  let current = 0;
  unit = unit || '시행';

  panel.className = 'game-progress';
  panel.setAttribute('role', 'status');
  panel.setAttribute('aria-live', 'polite');
  panel.append(count, time);
  target.before(panel);

  function format(ms, round) {
    const seconds = Math.max(0, round(ms / 1000));
    return Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0');
  }

  function render() {
    const elapsed = performance.now() - startedAt;
    count.textContent = total
      ? '진행 ' + current + ' / ' + total + unit + ' · 남은 ' + Math.max(0, total - current) + unit
      : '시간 진행 중';
    time.textContent = '경과 ' + format(elapsed, Math.floor)
      + (durationMs ? ' · 남은 시간 ' + format(durationMs - elapsed, Math.ceil) : '');
  }

  const timer = setInterval(render, 1000);
  render();
  return {
    set: function (value) { current = value; render(); },
    finish: function () { clearInterval(timer); panel.remove(); },
  };
};
