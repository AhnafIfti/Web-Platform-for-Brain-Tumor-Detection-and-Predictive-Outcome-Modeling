'use strict';
document.querySelector('.mobile-menu')?.addEventListener('click', function () {
  const open = document.querySelector('#sidebar').classList.toggle('open');
  this.setAttribute('aria-expanded', String(open));
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    document.querySelector('#sidebar')?.classList.remove('open');
    document.querySelector('.mobile-menu')?.setAttribute('aria-expanded', 'false');
  }
});
document.querySelector('.delete-form')?.addEventListener('submit', event => {
  if (!window.confirm('Permanently delete this analysis, uploaded MRI files, and all results?')) event.preventDefault();
});
