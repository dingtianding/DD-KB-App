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

const compactNumber = value => new Intl.NumberFormat('en-US', {notation:'compact',maximumFractionDigits:1}).format(value);
const askAbout = topic => {
  question.value = `What does my knowledge base say about ${topic}?`;
  question.focus();
  window.scrollTo({top:0,behavior:'smooth'});
};

fetch('/api/insights').then(r => {
  if (!r.ok) throw new Error('Insights unavailable');
  return r.json();
}).then(data => {
  document.querySelector('#stat-notes').textContent = data.documents.toLocaleString();
  document.querySelector('#stat-sections').textContent = data.chunks.toLocaleString();
  document.querySelector('#stat-words').textContent = compactNumber(data.words);
  document.querySelector('#indexed-at').textContent = `INDEXED ${new Date(data.indexed_at).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'})}`;

  const largest = Math.max(...data.topics.map(topic => topic.notes), 1);
  document.querySelector('#topics').innerHTML = data.topics.map(topic => `
    <button class="topic" type="button" data-topic="${escapeHtml(topic.name)}">
      <span class="topic-row"><strong>${escapeHtml(topic.name)}</strong><em>${topic.notes}</em></span>
      <span class="bar"><i style="width:${Math.round(topic.notes/largest*100)}%"></i></span>
    </button>`).join('') || '<p class="empty">No indexed topics yet.</p>';
  document.querySelectorAll('.topic').forEach(item => item.addEventListener('click', () => askAbout(item.dataset.topic)));

  document.querySelector('#recent').innerHTML = data.recent.map(note => `
    <div class="recent-note"><strong>${escapeHtml(note.title)}</strong><span>${escapeHtml(note.path)} · ${new Date(note.updated_at).toLocaleDateString([], {month:'short',day:'numeric'})}</span></div>
  `).join('') || '<p class="empty">No notes yet.</p>';

  document.querySelector('#tags').innerHTML = data.tags.map(tag => `
    <button type="button" data-tag="${escapeHtml(tag.name)}"><span>#${escapeHtml(tag.name)}</span><em>${tag.notes}</em></button>
  `).join('') || '<span class="empty">Add frontmatter tags to see topic signals here.</span>';
  document.querySelectorAll('[data-tag]').forEach(item => item.addEventListener('click', () => askAbout(item.dataset.tag)));
}).catch(() => {
  document.querySelector('.insights').classList.add('insights-error');
  document.querySelector('#topics').innerHTML = '<p class="error">Vault insights are unavailable.</p>';
});

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
