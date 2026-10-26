'use strict';
const uploadForm = document.getElementById('upload-form');
const maxBytes = Number(document.querySelector('script[data-max-mb]').dataset.maxMb) * 1024 * 1024;
const errorBox = document.getElementById('upload-error');
const progressBox = document.getElementById('upload-progress');
const runButton = document.getElementById('run-button');
function uploadError(text) { errorBox.textContent = text; errorBox.hidden = false; }
for (const input of uploadForm.querySelectorAll('input[type=file]')) {
  const card = input.closest('.modality-card');
  const zone = card.querySelector('.dropzone');
  const info = card.querySelector('.file-info');
  function updateFile() {
    const file = input.files[0];
    info.hidden = !file;
    if (!file) return;
    if (!/\.nii(\.gz)?$/i.test(file.name) || file.size === 0 || file.size > maxBytes) {
      uploadError('Choose a non-empty .nii or .nii.gz file within the upload size limit.');
      input.value = ''; info.hidden = true; return;
    }
    errorBox.hidden = true;
    info.querySelector('span').textContent = `${file.name} · ${(file.size / 1048576).toFixed(2)} MB · Ready to upload`;
  }
  input.addEventListener('change', updateFile);
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('dragover');
    if (e.dataTransfer.files.length !== 1) { uploadError('Choose one volume per modality.'); return; }
    input.files = e.dataTransfer.files; updateFile();
  });
  card.querySelector('.remove-file').addEventListener('click', () => { input.value = ''; info.hidden = true; });
}
uploadForm.addEventListener('submit', event => {
  event.preventDefault();
  if (!uploadForm.reportValidity()) return;
  errorBox.hidden = true; progressBox.hidden = false; runButton.disabled = true;
  progressBox.textContent = 'Uploading MRI volumes…';
  const request = new XMLHttpRequest();
  request.open('POST', uploadForm.action);
  request.responseType = 'json';
  request.upload.addEventListener('progress', e => {
    if (e.lengthComputable) progressBox.textContent = `Uploading MRI volumes · ${Math.round(e.loaded / e.total * 100)}% transferred`;
  });
  request.upload.addEventListener('load', () => {
    progressBox.textContent = 'Validating NIfTI structure and spatial alignment…';
    document.querySelectorAll('.step')[1].classList.add('active');
  });
  request.addEventListener('load', () => {
    if (request.status === 202 && request.response?.url) { window.location.assign(request.response.url); return; }
    const result = request.response;
    let text = result?.error || 'The upload could not be completed. Check your session and try again.';
    if (result?.fields) text += ' ' + Object.values(result.fields).flat().map(v => v.message).join(' ');
    uploadError(text); progressBox.hidden = true; runButton.disabled = false;
  });
  request.addEventListener('error', () => {
    uploadError('Connection interrupted. Please check your connection before retrying.');
    progressBox.hidden = true; runButton.disabled = false;
  });
  request.send(new FormData(uploadForm));
});
