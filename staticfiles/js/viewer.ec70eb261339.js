'use strict';
const processing = document.getElementById('processing');
if (processing) {
  let failures = 0;
  async function poll() {
    try {
      const response = await fetch(processing.dataset.url, {headers: {'Accept': 'application/json'}, cache: 'no-store'});
      if (!response.ok || response.redirected) throw new Error('Session or connection unavailable');
      const data = await response.json(); failures = 0;
      if (data.status === 'completed' || data.status === 'failed') { window.location.reload(); return; }
      document.getElementById('stage').textContent = data.stage;
      document.getElementById('processed').textContent = data.number_of_slices ? `${data.processed_slices} of ${data.number_of_slices} slices prepared` : 'Your scan is saved and waiting for the analysis worker.';
      const bar = document.getElementById('real-progress');
      bar.hidden = !data.number_of_slices; bar.max = data.number_of_slices || 1; bar.value = data.processed_slices;
    } catch (_) {
      failures++;
      document.getElementById('processed').textContent = 'Unable to refresh status. Reconnecting… Your saved analysis is retained.';
    }
    window.setTimeout(poll, Math.min(15000, 1500 * (failures + 1)));
  }
  poll();
}
const viewer = document.getElementById('viewer');
if (viewer) {
  const metadata = JSON.parse(document.getElementById('result-data').textContent);
  const canvas = document.getElementById('mri-canvas'), context = canvas.getContext('2d');
  const layers = document.createElement('canvas'); layers.width = 224; layers.height = 224;
  const layerContext = layers.getContext('2d');
  const slider = document.getElementById('slice-range');
  const loading = document.getElementById('viewer-loading');
  let slice = Number(viewer.dataset.slice), mode = 'overlay', opacity = .65, zoom = 1;
  let frames = null, loadToken = 0;
  const regions = ['wt', 'tc', 'et'];
  function image(url) {
    return new Promise((resolve, reject) => { const img = new Image(); img.onload = () => resolve(img); img.onerror = reject; img.src = url; });
  }
  function draw() {
    context.globalAlpha = 1; context.fillStyle = '#02070d'; context.fillRect(0, 0, 224, 224);
    if (!frames) return;
    if (mode !== 'mask') context.drawImage(frames[0], 0, 0);
    if (mode !== 'original') {
      // Composite at full alpha first, then apply opacity once. Nested masks
      // retain the legend colors and match the PDF's topmost-region overlay.
      layerContext.clearRect(0, 0, 224, 224);
      regions.forEach((name, i) => {
        if (document.querySelector(`[data-region="${name}"]`).checked) layerContext.drawImage(frames[i + 1], 0, 0);
      });
      context.globalAlpha = mode === 'mask' ? 1 : opacity;
      context.drawImage(layers, 0, 0);
    }
    context.globalAlpha = 1;
  }
  function charts() {
    window.NeuroCharts.areas(document.getElementById('area-chart'), metadata.slices, slice);
    window.NeuroCharts.bars(document.getElementById('probability-chart'), metadata.slices[slice].peaks);
  }
  async function showSlice(value) {
    slice = Math.max(0, Math.min(Number(viewer.dataset.count) - 1, Number(value)));
    slider.value = slice;
    document.getElementById('slice-label').textContent = `${slice + 1} / ${viewer.dataset.count}`;
    document.getElementById('prev-slice').disabled = slice === 0;
    document.getElementById('next-slice').disabled = slice === Number(viewer.dataset.count) - 1;
    const token = ++loadToken, requestedSlice = slice;
    frames = null; draw(); loading.hidden = false; loading.textContent = 'Loading slice…';
    document.getElementById('download-image').disabled = true;
    charts();
    try {
      const loaded = await Promise.all(['original', ...regions].map(kind => image(`${viewer.dataset.base}${requestedSlice}/${kind}/`)));
      if (token !== loadToken) return;
      frames = loaded; loading.hidden = true; draw();
      document.getElementById('download-image').disabled = false;
    } catch (_) {
      if (token === loadToken) loading.textContent = 'This slice could not be loaded. Try another slice or refresh.';
    }
  }
  slider.addEventListener('input', () => showSlice(slider.value));
  document.getElementById('prev-slice').onclick = () => showSlice(slice - 1);
  document.getElementById('next-slice').onclick = () => showSlice(slice + 1);
  document.addEventListener('keydown', e => {
    if (['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(e.target.tagName)) return;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { e.preventDefault(); showSlice(slice + (e.key === 'ArrowRight' ? 1 : -1)); }
  });
  for (const button of document.querySelectorAll('[data-mode]')) {
    button.onclick = () => {
      mode = button.dataset.mode;
      document.querySelectorAll('[data-mode]').forEach(b => { b.classList.toggle('selected', b === button); b.setAttribute('aria-pressed', String(b === button)); }); draw();
    };
  }
  document.querySelectorAll('[data-region]').forEach(input => input.addEventListener('change', draw));
  document.getElementById('opacity').oninput = e => {
    opacity = Number(e.target.value) / 100; document.getElementById('opacity-label').textContent = `${e.target.value}%`; draw();
  };
  function setZoom(value) { zoom = Math.max(.5, Math.min(3, value)); canvas.style.transform = `scale(${zoom})`; document.getElementById('zoom-label').textContent = `${Math.round(zoom * 100)}%`; }
  document.getElementById('zoom-in').onclick = () => setZoom(zoom + .25);
  document.getElementById('zoom-out').onclick = () => setZoom(zoom - .25);
  document.getElementById('fit').onclick = () => setZoom(1);
  document.getElementById('reset').onclick = () => {
    setZoom(1); document.querySelector('[data-mode="overlay"]').click();
    document.querySelectorAll('[data-region]').forEach(input => { input.checked = true; });
    const opacityInput = document.getElementById('opacity'); opacityInput.value = 65; opacityInput.dispatchEvent(new Event('input'));
    showSlice(viewer.dataset.slice);
  };
  document.getElementById('download-image').onclick = () => {
    const output = document.createElement('canvas'); output.width = 448; output.height = 492;
    const ctx = output.getContext('2d'); ctx.fillStyle = '#07111f'; ctx.fillRect(0, 0, 448, 492); ctx.drawImage(canvas, 0, 0, 448, 448);
    ctx.fillStyle = '#b7cedd'; ctx.font = '11px system-ui'; ctx.fillText(`NeuroVision AI · Slice ${slice + 1} · ${mode.toUpperCase()} · Research only`, 12, 471);
    const link = document.createElement('a'); link.download = `neurovision-slice-${slice + 1}-${mode}.png`; link.href = output.toDataURL('image/png'); link.click();
  };
  document.getElementById('area-chart').addEventListener('slice-select', e => showSlice(e.detail));
  document.querySelectorAll('.probability').forEach(el => { el.textContent = `${(Number(el.dataset.value) * 100).toFixed(2)}%`; });
  window.addEventListener('resize', charts); showSlice(slice);
}
