"use strict";
const reportButton = document.getElementById('download-report');
if (reportButton) {
  let busy = false;
  reportButton.addEventListener('click', async event => {
    event.preventDefault();
    if (busy) return;
    busy = true;
    const original = reportButton.textContent;
    const status = document.getElementById('report-status');
    reportButton.textContent = 'Preparing PDF…';
    reportButton.setAttribute('aria-disabled', 'true');
    status.hidden = false;
    status.textContent = 'Preparing your analysis report…';
    try {
      const response = await fetch(reportButton.href, {credentials: 'same-origin', cache: 'no-store'});
      if (response.redirected) throw new Error('Your session may have expired. Sign in again and retry.');
      if (!response.ok) throw new Error('The report could not be generated. Please retry or contact the administrator.');
      if (!(response.headers.get('Content-Type') || '').includes('application/pdf')) throw new Error('The server did not return a PDF. Please sign in and retry.');
      const blob = await response.blob();
      if (!blob.size) throw new Error('The report was empty. Please retry.');
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url; link.download = reportButton.dataset.filename;
      document.body.appendChild(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      status.textContent = 'PDF ready. Check your browser downloads. If nothing was saved, use Open report below.';
    } catch (error) {
      status.textContent = error.message || 'Download failed. Please use Open report or retry.';
    } finally {
      busy = false; reportButton.textContent = original; reportButton.removeAttribute('aria-disabled');
    }
  });
}
