const form = document.querySelector('#ask-form');
const question = document.querySelector('#question');
const result = document.querySelector('#result');
const answer = document.querySelector('#answer');
const sources = document.querySelector('#sources');
const button = form.querySelector('button');

const escapeHtml = value => value.replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));

fetch('/api/status').then(r => r.json()).then(data => {
  document.querySelector('#status').textContent = `${data.documents} documents · ${data.chunks} indexed sections`;
}).catch(() => document.querySelector('#status').textContent = 'Vault status unavailable');

form.addEventListener('submit', async event => {
  event.preventDefault();
  button.disabled = true;
  button.textContent = 'Searching…';
  const started = performance.now();
  try {
    const response = await fetch('/api/ask', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:question.value})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Request failed');
    answer.className = 'answer';
    answer.textContent = data.answer;
    document.querySelector('#mode').textContent = data.mode === 'generated' ? `GROUNDED ANSWER · ${data.model}` : 'LOCAL RETRIEVAL';
    document.querySelector('#timing').textContent = `${Math.round(performance.now()-started)} MS`;
    sources.innerHTML = data.sources.map((source,index) => `<article class="source"><strong>[S${index+1}] ${escapeHtml(source.title)}</strong><br><span>${escapeHtml(source.path)} · ${escapeHtml(source.section)} · line ${source.line}</span><p>${escapeHtml(source.text)}</p></article>`).join('') || '<p>No sources found.</p>';
  } catch (error) {
    answer.className = 'answer error'; answer.textContent = error.message; sources.innerHTML = '';
  } finally {
    result.hidden = false; result.scrollIntoView({behavior:'smooth',block:'start'});
    button.disabled = false; button.innerHTML = 'Search DD-KB <b>→</b>';
  }
});

question.addEventListener('keydown', event => {
  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') form.requestSubmit();
});
