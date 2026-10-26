'use strict';
window.NeuroCharts = {
  colors: ['#22d3ee', '#f59e0b', '#ec4899'],
  context(canvas) {
    const width = canvas.clientWidth || 500, height = canvas.clientHeight || 215;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = width * ratio; canvas.height = height * ratio;
    const ctx = canvas.getContext('2d'); ctx.scale(ratio, ratio);
    ctx.font = '10px Inter, system-ui';
    return {ctx, width, height};
  },
  bars(canvas, values, labels = ['WT', 'TC', 'ET']) {
    const {ctx, width, height} = this.context(canvas);
    const left = 52, right = 28, top = 20, bottom = height - 36;
    ctx.fillStyle = '#6f8aa3';
    for (let i = 0; i <= 4; i++) {
      const x = left + (width - left - right) * i / 4;
      ctx.strokeStyle = '#213246'; ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, bottom); ctx.stroke();
      ctx.fillText((i / 4).toFixed(2), x - 9, bottom + 20);
    }
    values.forEach((v, i) => {
      const y = top + i * (bottom - top) / 3 + 13;
      ctx.fillStyle = '#a3bacd'; ctx.fillText(labels[i], 20, y + 7);
      ctx.fillStyle = this.colors[i];
      ctx.fillRect(left, y - 6, Math.max(0, v * (width - left - right)), 16);
      ctx.fillStyle = '#deedf8'; ctx.fillText(v.toFixed(4), left + 5, y + 6);
    });
  },
  areas(canvas, slices, selected) {
    const {ctx, width, height} = this.context(canvas);
    const left = 48, right = 24, top = 20, bottom = height - 36;
    const maximum = Math.max(1, ...slices.flatMap(s => s.areas));
    const chartWidth = width - left - right;
    for (let i = 0; i <= 4; i++) {
      const y = bottom - i * (bottom - top) / 4;
      ctx.strokeStyle = '#213246'; ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(width - right, y); ctx.stroke();
      ctx.fillStyle = '#6f8aa3'; ctx.fillText(String(Math.round(maximum * i / 4)), 6, y + 3);
    }
    for (let c = 0; c < 3; c++) {
      ctx.strokeStyle = this.colors[c]; ctx.lineWidth = 1.8; ctx.beginPath();
      slices.forEach((s, i) => {
        const x = left + i / Math.max(1, slices.length - 1) * chartWidth;
        const y = bottom - s.areas[c] / maximum * (bottom - top);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();
    }
    const x = left + selected / Math.max(1, slices.length - 1) * chartWidth;
    ctx.strokeStyle = '#bed8eb'; ctx.lineWidth = 1; ctx.setLineDash([3, 4]); ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, bottom); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = '#819bb0'; ctx.fillText('Slice 1', left, bottom + 21); ctx.fillText(String(slices.length), width - right - 15, bottom + 21);
    canvas.onclick = e => {
      const localX = e.clientX - canvas.getBoundingClientRect().left;
      const index = Math.round(Math.max(0, Math.min(1, (localX - left) / chartWidth)) * (slices.length - 1));
      canvas.dispatchEvent(new CustomEvent('slice-select', {detail: index}));
    };
  }
};
const benchmarkData = document.getElementById('benchmark-data');
if (benchmarkData) {
  const data = JSON.parse(benchmarkData.textContent);
  const select = document.getElementById('benchmark-select');
  const draw = () => {
    const row = data[Number(select.value)];
    window.NeuroCharts.bars(document.getElementById('benchmark-chart'), [row.Dice_WT, row.Dice_TC, row.Dice_ET]);
    const comparison = document.getElementById('comparison-chart');
    comparison.style.height = `${Math.max(170, data.length * 26 + 35)}px`;
    const {ctx, width} = window.NeuroCharts.context(comparison);
    const left = width < 500 ? 70 : 290;
    const available = width - left - 75;
    data.forEach((item, index) => {
      const y = 22 + index * 26;
      ctx.fillStyle = '#9bb2c8';
      const label = width < 500 ? `Row ${index + 1}` : `${index + 1}. ${item.Model.slice(0, 35)}${item.Model.length > 35 ? '…' : ''}`;
      ctx.fillText(label, 18, y + 7);
      ctx.fillStyle = item.Dataset === 'BraTS2021' ? '#f59e0b' : '#22d3ee';
      ctx.fillRect(left, y - 4, Math.max(0, available * item.Avg_Dice), 14);
      ctx.fillStyle = '#bbd2e4'; ctx.fillText(item.Avg_Dice.toFixed(4), left + available * item.Avg_Dice + 9, y + 7);
    });
  };
  select.addEventListener('change', draw); window.addEventListener('resize', draw); draw();
}
