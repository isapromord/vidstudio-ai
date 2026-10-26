/* VidStudio PRO - lógica de la interfaz.
   Depende de escHtml(), currentReplicaScriptEn, loadFunnelBoard(), moveFunnelCard(),
   createNewFunnelCard() y synthesizeEnglishTrack() definidos en el script inline de index.html. */

let currentTaskId = null;
let pollInterval = null;
let allBrands = {};
let activeBrandId = 'la_mente_observadora';
let chatHistory = [];
let currentReplicaPrompts = [];
let currentLang = 'es';
let analysisData = null;
let currentThumbAspect = '16:9';
let currentAbVariants = [];
let activeVariantIdx = 0;
let safeZoneVisible = true;
let repurposedClips = [];
let lastProposal = null;
let sidebarCollapsed = false;

const $ = (id) => document.getElementById(id);

function setText(id, value) {
  const el = $(id);
  if (el) el.innerText = value;
}

function safeUrl(u) {
  const s = String(u || '');
  return /^(https?:\/\/|\/)/i.test(s) ? s : '#';
}

async function apiGet(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function apiPost(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  let data = null;
  try { data = await res.json(); } catch (e) { /* respuesta sin JSON */ }
  if (!res.ok) {
    const detail = data && data.detail ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)) : `HTTP ${res.status}`;
    throw new Error(detail);
  }
  return data;
}

function setBusy(btn, busy, busyHtml) {
  if (!btn) return;
  if (busy) {
    btn.dataset.origHtml = btn.innerHTML;
    btn.innerHTML = busyHtml;
    btn.disabled = true;
  } else {
    if (btn.dataset.origHtml !== undefined) btn.innerHTML = btn.dataset.origHtml;
    btn.disabled = false;
  }
}

const SPINNER = (txt) => `<i class="ph-bold ph-spinner animate-spin text-base"></i> <span>${txt}</span>`;

function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text).catch(() => fallbackCopy(text));
  }
  fallbackCopy(text);
  return Promise.resolve();
}

function fallbackCopy(text) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); } catch (e) { /* sin portapapeles */ }
  document.body.removeChild(ta);
}

function copyToClipboard(btn, text) {
  copyText(text || '');
  if (!btn) return;
  const original = btn.innerHTML;
  btn.innerHTML = '<i class="ph-bold ph-check text-emerald-400"></i> ¡Copiado!';
  setTimeout(() => { btn.innerHTML = original; }, 2000);
}

/* ---------- Navegación ---------- */

const VIEWS = {
  radar:       { section: 'sectionRadar',       nav: 'navRadar',       title: '1. Radar de Outliers 24/7' },
  deconstruct: { section: 'sectionDeconstruct', nav: 'navDeconstruct', title: '2. Deconstrucción 1 a 1 & ADN Acústico' },
  studio:      { section: 'sectionStudio',      nav: 'navStudio',      title: '3. Taller de Guiones & Curva AVD' },
  ctrlab:      { section: 'sectionCtrLab',      nav: 'navCtrLab',      title: '4. CTR Lab: Miniaturas A/B & Safe Zones' },
  brainstorm:  { section: 'sectionBrainstorm',  nav: 'navBrainstorm',  title: '5. Copiloto Creativo & Estratégico' },
  repurpose:   { section: 'sectionRepurpose',   nav: 'navRepurpose',   title: '6. Clipper 9:16 Real (Video MP4)' },
  funnel:      { section: 'sectionFunnel',      nav: 'navFunnel',      title: '7. Tablero de Embudo' },
  research:    { section: 'sectionResearch',    nav: 'navResearch',    title: '8. Incubadora de Canales & Holding' },
  vfx:         { section: 'sectionVfx',         nav: 'navVfx',         title: '9. AI Magic VFX & Prompt Editor (Edición por Palabras)' }
};

function switchMode(mode) {
  if (mode === 'single') mode = 'deconstruct';
  if (!VIEWS[mode]) mode = 'radar';

  Object.keys(VIEWS).forEach((k) => {
    const sec = $(VIEWS[k].section);
    if (sec) sec.classList.toggle('hidden', k !== mode);
    const nav = $(VIEWS[k].nav);
    if (nav) {
      nav.classList.toggle('nav-item-active', k === mode);
      nav.classList.toggle('text-gray-400', k !== mode);
    }
  });

  setText('currentSectionTitle', VIEWS[mode].title);

  if (mode === 'radar') loadRadarChannels();
  if (mode === 'funnel') loadFunnelBoard();
  if (mode === 'studio') updateAvdRetentionAnalysis();
}

function toggleSidebar() {
  sidebarCollapsed = !sidebarCollapsed;
  const sb = $('mainSidebar');
  if (!sb) return;
  sb.classList.toggle('w-64', !sidebarCollapsed);
  sb.classList.toggle('w-20', sidebarCollapsed);
  document.querySelectorAll('.sidebar-text').forEach((t) => t.classList.toggle('hidden', sidebarCollapsed));
}

/* ---------- Marcas / canal activo ---------- */

async function reloadBrands() {
  try {
    allBrands = await apiGet('/api/brands');
    const sel = $('channelSelector');
    if (sel) {
      sel.innerHTML = '';
      Object.keys(allBrands).forEach((bId) => {
        const b = allBrands[bId];
        const opt = document.createElement('option');
        opt.value = b.id || bId;
        opt.className = 'bg-black text-white';
        opt.textContent = b.name || bId;
        sel.appendChild(opt);
      });
      if (!allBrands[activeBrandId]) activeBrandId = Object.keys(allBrands)[0] || activeBrandId;
      sel.value = activeBrandId;
    }
    updateBrandIndicators();
  } catch (e) {
    console.error('Error cargando marcas:', e);
  }
}

function onChannelChange() {
  const sel = $('channelSelector');
  if (sel) activeBrandId = sel.value;
  updateBrandIndicators();
}

function brandVoiceName(b) {
  const v = (b && b.voice) || {};
  return v.name || v.provider || 'es-US-AlonsoNeural';
}

function updateBrandIndicators() {
  const b = allBrands[activeBrandId];
  if (!b) return;
  setText('sidebarBrandName', b.name || '');
  setText('sidebarAvatar', ((b.name || 'M')[0] || 'M').toUpperCase());
  setText('mockAvatar', ((b.name || 'M')[0] || 'M').toUpperCase());

  const set = (id, v) => { const el = $(id); if (el) el.value = v; };
  set('brandFormName', b.name || '');
  set('brandFormHandle', b.handle || '');
  set('brandFormThesis', b.thesis || '');
  const v = b.voice || {};
  set('brandFormVoice', `${brandVoiceName(b)}${v.rate || v.pitch ? ` (Pitch: ${v.pitch || '0Hz'}, Rate: ${v.rate || '0%'})` : ''}`);
  set('brandFormFlow', b.flow_rules || '');
}

async function saveCurrentBrandForm() {
  const val = (id) => ($(id) ? $(id).value.trim() : '');
  const name = val('brandFormName');
  if (!name) {
    alert('El nombre del canal es obligatorio.');
    return;
  }
  const voiceStr = val('brandFormVoice');
  const base = allBrands[activeBrandId] || {};
  const pal = lastProposal && lastProposal.palette;
  const colors = pal
    ? { primary: pal.primary, accent: pal.accent, secondary: pal.secondary, highlight: pal.highlight }
    : (base.colors || { primary: '#0B0C10', accent: '#E5C158', secondary: '#66FCF1' });

  const payload = {
    name: name,
    handle: val('brandFormHandle'),
    niche: val('nicheTopicInput') || base.niche || 'General',
    archetype: (lastProposal && lastProposal.archetype) || base.archetype || 'Especialista de Alto Impacto',
    thesis: val('brandFormThesis'),
    colors: colors,
    voice: { name: voiceStr.split(' ')[0] || 'es-US-AlonsoNeural', provider: voiceStr.split(' ')[0] || 'es-US-AlonsoNeural', tone: voiceStr },
    flow_rules: val('brandFormFlow')
  };
  if (allBrands[activeBrandId] && allBrands[activeBrandId].name === name) payload.id = activeBrandId;

  try {
    const data = await apiPost('/api/brands/save', payload);
    if (data.status === 'success') {
      activeBrandId = data.brand.id;
      await reloadBrands();
      alert(`Canal "${name}" guardado. Ya está disponible en el selector superior.`);
    }
  } catch (e) {
    alert('Error al guardar el canal: ' + e.message);
  }
}

function setLanguage(lang) {
  currentLang = lang;
  const es = $('btnLangEs');
  const en = $('btnLangEn');
  const on = 'px-2.5 py-1 rounded-lg font-bold transition-all flex items-center gap-1 ';
  const off = 'px-2.5 py-1 rounded-lg font-semibold text-gray-400 hover:text-white transition-all flex items-center gap-1';
  if (es) es.className = lang === 'es' ? on + 'bg-amber-500/20 text-amber-300 border border-amber-500/30' : off;
  if (en) en.className = lang === 'en' ? on + 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : off;
  updateLanguageView();
}

function updateLanguageView() {
  if (!analysisData) return;
  const isEn = currentLang === 'en';
  const title = isEn ? analysisData.title_en : analysisData.title_es;
  const script = isEn ? analysisData.replica_script_en : (analysisData.replica_script_es || analysisData.replica_script);
  if (title && $('scriptTitle')) $('scriptTitle').value = title;
  if (script && $('scriptBody')) $('scriptBody').value = script;
  updateAvdRetentionAnalysis();
}

/* ---------- Taller de guiones / AVD ---------- */

function updateAvdRetentionAnalysis() {
  const body = $('scriptBody');
  if (!body) return;
  const text = (body.value || '').trim();
  const words = text ? text.split(/\s+/) : [];
  const wordCount = words.length;
  const estSeconds = Math.round(wordCount / 2.6);

  setText('scriptWordCount', `${wordCount} palabras • ~${estSeconds}s`);
  setText('avdTotalDuration', `~${estSeconds}s Final`);
  setText('avdPacingText', wordCount ? '2.6 palabras/segundo (Ritmo Óptimo)' : 'Sin guion');

  const hookWords = words.slice(0, 10).join(' ').toLowerCase();
  const esGreetings = ['hola', 'bienvenido', 'en este video', 'hoy te voy', 'suscríbete', 'suscribete', 'hey'];
  const enGreetings = ['hello', 'welcome', 'in this video', 'today i will', 'subscribe', 'hey guys', 'what is up'];
  const hasGreeting = [...esGreetings, ...enGreetings].some((g) => hookWords.includes(g));

  const endingWords = words.slice(-20).join(' ').toLowerCase();
  const esLeaks = ['en conclusión', 'en resumen', 'gracias por ver', 'espero que te haya', 'hasta luego', 'chao', 'adiós'];
  const enLeaks = ['in conclusion', 'to summarize', 'thanks for watching', 'hope you enjoyed', 'see you next time', 'bye'];
  const hasLeak = [...esLeaks, ...enLeaks].some((l) => endingWords.includes(l));

  const leakEl = $('avdLeakStatus');
  if (leakEl) {
    if (hasGreeting || hasLeak) {
      leakEl.innerText = hasGreeting ? '⚠ Saludo detectado en el hook' : '⚠ Fuga de cierre detectada';
      leakEl.className = 'text-rose-400 font-bold';
    } else {
      leakEl.innerText = '✓ Cero frases de fuga detectadas';
      leakEl.className = 'text-emerald-400 font-bold';
    }
  }

  let score = 100;
  if (hasGreeting) score -= 25;
  if (hasLeak) score -= 20;
  if (wordCount < 40 || wordCount > 180) score -= 15;
  score = Math.max(score, 35);

  const scoreEl = $('avdScoreBadge');
  if (scoreEl) {
    const label = score >= 80 ? 'Excelente' : score >= 60 ? 'Aceptable' : 'Mejorable';
    scoreEl.innerText = `Score AVD: ${score}/100 (${label})`;
    const tone = score >= 80 ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
      : score >= 60 ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
      : 'bg-rose-500/20 text-rose-300 border-rose-500/30';
    scoreEl.className = `text-xs px-2 py-0.5 rounded font-mono font-bold border ${tone}`;
  }
}

function renderFlowScenes() {
  const list = $('flowScenesList');
  if (!list) return;
  if (!currentReplicaPrompts.length) return;
  list.innerHTML = currentReplicaPrompts.map((p) => `
    <div class="p-3 bg-black/40 rounded-xl border border-white/5 text-xs text-gray-300 space-y-1">
      <div class="flex justify-between font-bold text-amber-300 text-[11px]">
        <span>Escena ${escHtml(p.escena)} (${escHtml(p.segundos)})</span>
        <span class="font-mono text-gray-400">${escHtml(p.tipo)}</span>
      </div>
      <p class="text-[11px] text-gray-400">${escHtml(p.descripcion)}</p>
      <p class="text-[11px] font-mono text-cyan-200/90 select-all">${escHtml(p.prompt_en)}</p>
    </div>`).join('');
}

function copyAllFlowPrompts() {
  const btn = $('btnCopyAllFlow');
  if (!currentReplicaPrompts.length) {
    alert('No hay prompts cargados. Deconstruye un video primero.');
    return;
  }
  const title = ($('scriptTitle') && $('scriptTitle').value) || 'Secuencia Cinemática';
  let full = `=== HOJA DE STORYBOARD GOOGLE FLOW: ${title} ===\nFormato: 9:16 Vertical\n\n`;
  currentReplicaPrompts.forEach((p) => {
    full += `[ESCENA ${p.escena} (${p.segundos}) - ${p.tipo}]\nConcepto: ${p.descripcion}\nPrompt: ${p.prompt_en}\n\n`;
  });
  copyToClipboard(btn, full);
}

async function startRender() {
  const script = ($('scriptBody').value || '').trim();
  const title = ($('scriptTitle').value || '').trim() || 'Regla de Oro';
  if (!script) {
    alert('Escribe o genera un guion antes de producir.');
    return;
  }
  const btn = $('btnProduceVideo');
  setBusy(btn, true, SPINNER('Iniciando render...'));
  if (pollInterval) clearInterval(pollInterval);

  try {
    const data = await apiPost('/api/render', {
      script_text: script,
      title: title,
      brand_id: activeBrandId,
      voice_name: currentLang === 'en' ? 'en-US-AndrewNeural' : brandVoiceName(allBrands[activeBrandId]),
      language: currentLang
    });
    if (data.status === 'started' && data.task_id) {
      currentTaskId = data.task_id;
      pollTaskStatus(btn);
    } else {
      setBusy(btn, false);
      alert('No se pudo iniciar el render.');
    }
  } catch (err) {
    console.error('Error starting render:', err);
    setBusy(btn, false);
    alert('Error al iniciar el render: ' + err.message);
  }
}

function pollTaskStatus(btn) {
  const labels = {
    queued: 'En cola...',
    generating_audio: '1/3 Generando audio...',
    syncing_subtitles: '2/3 Sincronizando subtítulos...',
    rendering_video: '3/3 Ensamblando video...'
  };
  pollInterval = setInterval(async () => {
    if (!currentTaskId) return;
    try {
      const task = await apiGet(`/api/task/${currentTaskId}`);
      if (task.status === 'completed') {
        clearInterval(pollInterval);
        setBusy(btn, false);
        showRenderResult(task);
      } else if (task.status === 'failed') {
        clearInterval(pollInterval);
        setBusy(btn, false);
        alert('El render falló: ' + (task.error || 'error desconocido'));
      } else if (btn) {
        btn.innerHTML = SPINNER(`${labels[task.status] || 'Procesando...'} ${task.progress || 0}%`);
      }
    } catch (e) {
      clearInterval(pollInterval);
      setBusy(btn, false);
      console.error('Error consultando tarea:', e);
    }
  }, 1500);
}

function showRenderResult(task) {
  let box = $('renderResultBox');
  if (!box) {
    box = document.createElement('div');
    box.id = 'renderResultBox';
    box.className = 'mt-4 p-4 rounded-xl bg-black/60 border border-emerald-500/30 space-y-3';
    const anchor = $('btnProduceVideo').parentElement;
    anchor.insertAdjacentElement('afterend', box);
  }
  const link = (href, label) => href
    ? `<a href="${escHtml(safeUrl(href))}" download class="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-[11px] font-semibold">${label}</a>` : '';
  box.innerHTML = `
    <div class="text-xs font-bold text-emerald-300">Video producido correctamente</div>
    <video controls class="w-full max-h-96 rounded-lg bg-black" src="${escHtml(safeUrl(task.video_url))}?t=${Date.now()}"></video>
    <div class="flex flex-wrap gap-2">
      ${link(task.video_url, 'Descargar MP4')}${link(task.audio_url, 'Descargar WAV')}${link(task.srt_url, 'Descargar SRT')}${link(task.cover_url, 'Descargar portada')}
    </div>`;
}

async function exportProductionZip() {
  const btn = $('btnGlobalExportZip');
  const title = ($('scriptTitle').value || '').trim() || 'Proyecto_Viral';
  const meta = analysisData ? (currentLang === 'en' ? analysisData.metadata_en : analysisData.metadata_es) : null;
  const flowRule = (analysisData && analysisData.visual_inspection && analysisData.visual_inspection.regla_flow_mimic)
    || (allBrands[activeBrandId] && allBrands[activeBrandId].flow_rules) || '';
  setBusy(btn, true, SPINNER('Generando ZIP...'));
  try {
    const data = await apiPost('/api/export/zip', {
      task_id: currentTaskId,
      title: title,
      script_text: ($('scriptBody').value || '').trim(),
      script_en: currentReplicaScriptEn || '',
      language: currentLang,
      replica_prompts: currentReplicaPrompts,
      flow_rule: flowRule,
      metadata: meta || { title: title, description: '', tags: [] },
      thumb_title: ($('thumbHookText') && $('thumbHookText').value) || title,
      brand_id: activeBrandId
    });
    if (data.status === 'success' && data.zip_url) {
      const a = document.createElement('a');
      a.href = data.zip_url;
      a.download = data.filename || 'Produccion_Kit.zip';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } else {
      alert('Error al generar el kit de producción.');
    }
  } catch (e) {
    alert('Error al exportar ZIP: ' + e.message);
  } finally {
    setBusy(btn, false);
  }
}

/* ---------- Radar ---------- */

async function loadRadarChannels() {
  try {
    renderRadarDashboard(await apiGet('/api/radar/channels'));
  } catch (e) {
    console.error('Error cargando radar:', e);
  }
}

async function selectNichePreset(presetKey, query) {
  const inputEl = $('radarChannelInput');
  if (inputEl) {
    inputEl.value = query;
  }
  await scanRadarChannel();
}

async function scanRadarChannel() {
  const input = ($('radarChannelInput').value || '').trim();
  if (!input) {
    alert('Ingresa un tema, nicho o canal de YouTube.');
    return;
  }
  const btn = $('btnScanRadar');
  setBusy(btn, true, SPINNER('Explorando nicho & anomalías...'));
  try {
    const data = await apiPost('/api/radar/scan', { channel_input: input });
    if (data.status === 'success') {
      await loadRadarChannels();
    } else {
      alert('No se pudo escanear el nicho o canal.');
    }
  } catch (e) {
    alert('Error al escanear el canal: ' + e.message);
  } finally {
    setBusy(btn, false);
  }
}

function renderRadarDashboard(db) {
  const chList = $('radarChannelsList');
  const feed = $('radarOutliersFeed');
  if (!chList || !feed) return;
  const keys = Object.keys(db || {});
  setText('radarChannelsCount', `${keys.length} canales monitoreados`);
  chList.innerHTML = '';
  feed.innerHTML = '';
  const all = [];

  keys.forEach((handle) => {
    const ch = db[handle];
    const card = document.createElement('div');
    card.className = 'glass-card rounded-xl p-4 border-white/10 space-y-2';
    card.innerHTML = `
      <div class="flex items-center justify-between">
        <h4 class="font-bold text-white text-sm">${escHtml(ch.channel_title)}</h4>
        <span class="text-[10px] text-gray-400 font-mono">${escHtml(ch.handle || handle)}</span>
      </div>
      <div class="flex items-center justify-between text-xs pt-1 border-t border-white/5">
        <span class="text-gray-400">Media base (Baseline):</span>
        <span class="font-bold text-amber-300 font-mono">${Number(ch.baseline_views || 0).toLocaleString()} vistas</span>
      </div>`;
    chList.appendChild(card);
    (ch.videos || []).forEach((v) => all.push({ ...v, channel_name: ch.channel_title }));
  });

  all.sort((a, b) => (b.outlier_ratio || 0) - (a.outlier_ratio || 0));
  all.forEach((v) => {
    const isOutlier = v.is_outlier || v.outlier_ratio >= 2.0;
    const card = document.createElement('div');
    card.className = `glass-card rounded-2xl p-5 space-y-4 border transition-all flex flex-col justify-between ${isOutlier ? 'border-rose-500/40 bg-rose-950/10' : 'border-white/10'}`;
    const badge = isOutlier ? 'bg-rose-500/20 text-rose-300 border-rose-500/50' : 'bg-gray-800 text-gray-300 border-gray-700';
    card.innerHTML = `
      <div class="space-y-3">
        <div class="flex items-center justify-between gap-2">
          <span class="px-2.5 py-1 rounded-md text-[11px] font-bold border ${badge}">${escHtml(v.velocity_label)}</span>
          <span class="text-xs text-gray-400 font-mono">${escHtml(v.duration || '')}</span>
        </div>
        <div class="relative rounded-xl overflow-hidden bg-black/60 aspect-video border border-white/10">
          <img src="${escHtml(safeUrl(v.thumbnail))}" alt="Portada" class="w-full h-full object-cover" />
          <div class="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/80 text-[10px] text-white font-mono font-bold">${Number(v.view_count || 0).toLocaleString()} vistas</div>
        </div>
        <div class="space-y-1">
          <div class="text-[10px] text-gray-400 uppercase font-semibold">${escHtml(v.channel_name || 'Competidor')}</div>
          <h4 class="font-bold text-white text-xs leading-snug line-clamp-2">${escHtml(v.title)}</h4>
        </div>
      </div>
      <button type="button" class="mimic-btn w-full mt-2 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-black font-extrabold text-xs flex items-center justify-center gap-2 transition-all">
        <i class="ph-bold ph-lightning"></i> Mimic en 1-Clic (Deconstruir & Clonar)
      </button>`;
    card.querySelector('.mimic-btn').addEventListener('click', () => mimicOutlierVideo(v.url));
    feed.appendChild(card);
  });
}

function mimicOutlierVideo(url) {
  if (!url) return;
  switchMode('deconstruct');
  $('urlInput').value = url;
  analyzeVideo();
}

/* ---------- Deconstrucción 1 a 1 ---------- */

async function analyzeVideo() {
  const url = ($('urlInput').value || '').trim();
  if (!url) {
    alert('Pega la URL de un video de YouTube.');
    return;
  }
  const views = parseInt($('customViewsInput').value, 10);
  const btn = $('btnAnalyze');
  setBusy(btn, true, SPINNER('Deconstruyendo audio y video...'));
  try {
    const data = await apiPost('/api/analyze', { video_url: url, custom_views: views > 0 ? views : null });
    if (data.status !== 'success') throw new Error('Respuesta inválida del servidor');
    const a = data.analysis;
    const dna = a.dna_analysis || {};
    const snd = dna.diseno_sonoro || {};

    setText('valViews', Number(a.actual_views || 0).toLocaleString());
    setText('valEarnings', `$${a.video_earnings.min} - $${a.video_earnings.max}`);
    setText('valRpm', `RPM: ${a.rpm_range} / 1K vistas`);
    setText('valNiche', a.author || '');
    setText('valAudience', a.outlier_score || '');
    setText('valFormat', a.is_short ? 'Short (9:16)' : 'Largo (16:9)');
    setText('dnaLanguageBadge', `Idioma Detectado: ${dna.idioma_original || ''}`);
    setText('dnaRawTranscript', `"${dna.transcripcion_original || ''}"`);
    setText('dnaContexto', dna.contexto_original || '');
    setText('dnaCortes', dna.ritmo_cortes || '');
    setText('dnaSonido', `${snd.tipo_musica || ''} (${snd.tempo_bpm || ''})`);
    setText('dnaVisual', dna.estilo_visual || '');

    analysisData = a;
    currentReplicaPrompts = a.replica_prompts || [];
    currentReplicaScriptEn = a.replica_script_en || '';
    renderFlowScenes();
    updateLanguageView();
    setText('activeSceneBadge', `Réplica de: ${(a.title_es || a.title || '').substring(0, 30)}`);
  } catch (err) {
    alert('Error al deconstruir el video: ' + err.message);
  } finally {
    setBusy(btn, false);
  }
}

/* ---------- CTR Lab ---------- */

function setThumbAspect(aspect) {
  currentThumbAspect = aspect;
  const on = 'px-3 py-1 rounded-lg font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 transition-all';
  const off = 'px-3 py-1 rounded-lg font-bold text-gray-400 hover:text-white transition-all';
  if ($('btnAspect916')) $('btnAspect916').className = aspect === '9:16' ? on : off;
  if ($('btnAspect169')) $('btnAspect169').className = aspect === '16:9' ? on : off;
}

function toggleSafeZoneOverlay() {
  safeZoneVisible = !safeZoneVisible;
  const overlay = $('safeZoneOverlay');
  if (overlay) overlay.style.display = safeZoneVisible ? '' : 'none';
  setText('safeZoneStatusText', safeZoneVisible ? 'Zonas Seguras: ON' : 'Zonas Seguras: OFF');
}

function thumbInputs() {
  return {
    title: ($('thumbHookText').value || '').trim() || 'EL PODER DEL SILENCIO',
    highlight_word: ($('thumbHighlightWord').value || '').trim() || 'SILENCIO',
    aspect_ratio: currentThumbAspect,
    brand_id: activeBrandId
  };
}

async function generateAbThumbnails() {
  const btn = $('btnGenerateAbThumb');
  setBusy(btn, true, SPINNER('Generando 3 variantes...'));
  try {
    const data = await apiPost('/api/thumbnail/ab-variants', thumbInputs());
    if (data.status === 'success' && data.variants && data.variants.length) {
      currentAbVariants = data.variants;
      activeVariantIdx = 0;
      renderAbVariantTabs();
      selectAbVariant(0);
      $('thumbAbContainer').classList.remove('hidden');
    } else {
      alert('No se pudieron generar las variantes.');
    }
  } catch (e) {
    alert('Error al generar variantes A/B: ' + e.message);
  } finally {
    setBusy(btn, false);
  }
}

function renderAbVariantTabs() {
  const box = $('abVariantTabs');
  if (!box) return;
  box.innerHTML = '';
  const medals = ['🥇', '🥈', '🥉'];
  currentAbVariants.forEach((v, idx) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.id = `tabVariant_${idx}`;
    b.addEventListener('click', () => selectAbVariant(idx));
    b.innerHTML = `
      <div class="flex items-center justify-between font-bold text-[11px]">
        <span>${medals[idx] || '•'} Variante ${escHtml(v.variant_id)}</span>
      </div>
      <div class="text-[10px] text-gray-300 truncate mt-0.5">${escHtml(String(v.name || '').split('(')[0])}</div>`;
    box.appendChild(b);
  });
}

function selectAbVariant(idx) {
  const v = currentAbVariants[idx];
  if (!v) return;
  activeVariantIdx = idx;
  currentAbVariants.forEach((_, i) => {
    const tab = $(`tabVariant_${i}`);
    if (tab) {
      tab.className = 'p-2 rounded-xl text-left border transition-all text-xs ' + (i === idx
        ? 'bg-amber-500/20 border-amber-500/50 text-amber-200 shadow-md shadow-amber-500/10'
        : 'bg-black/40 border-white/10 text-gray-400 hover:text-white');
    }
  });
  showThumbnail(v.url, v.flow_prompt, v.ctr_prediction);
}

function showThumbnail(url, prompt, ctr) {
  const b = allBrands[activeBrandId] || { name: 'La Mente Observadora' };
  const img = $('thumbPreviewImg');
  if (img) img.src = `${url}?t=${Date.now()}`;
  const dl = $('btnDownloadThumb');
  if (dl) dl.href = url;
  setText('thumbFlowPromptText', prompt || '');
  setText('mockVariantCtr', ctr || '');
  setText('mockVideoTitle', `${$('thumbHookText').value || ''} • ${b.name}`);
  setText('mockChannelMeta', `${b.name} • 148K vistas • hace 3 horas`);
  setText('mockAvatar', ((b.name || 'M')[0] || 'M').toUpperCase());
}

async function generateCustomThumbnail() {
  const btn = $('btnGenerateThumb');
  setBusy(btn, true, SPINNER('Generando portada HD...'));
  try {
    const data = await apiPost('/api/thumbnail/generate', thumbInputs());
    if (data.status === 'success') {
      currentAbVariants = [];
      const tabs = $('abVariantTabs');
      if (tabs) tabs.innerHTML = '';
      showThumbnail(data.thumbnail_url, data.flow_prompt, 'Portada simple');
      $('thumbAbContainer').classList.remove('hidden');
    } else {
      alert('No se pudo generar la portada.');
    }
  } catch (e) {
    alert('Error al generar portada: ' + e.message);
  } finally {
    setBusy(btn, false);
  }
}

/* ---------- Clipper ---------- */

const CLIP_BADGES = {
  rose: 'bg-rose-500/15 text-rose-300 border-rose-500/40',
  cyan: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/40',
  purple: 'bg-purple-500/15 text-purple-300 border-purple-500/40',
  amber: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
  emerald: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40'
};

function getSelectedCropMode() {
  const radios = document.getElementsByName('cropModeRadio');
  for (let r of radios) {
    if (r.checked) return r.value;
  }
  return 'auto';
}

function updateCropModeUi() {
  const mode = getSelectedCropMode();
  const autoLbl = $('lblCropAuto');
  const splitLbl = $('lblCropSplit');
  const fullLbl = $('lblCropFull');
  
  const activeClass = 'cursor-pointer flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold transition-all';
  const inactiveClass = 'cursor-pointer flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 text-gray-400 hover:text-white border border-white/10 font-medium transition-all';
  
  if (autoLbl) autoLbl.className = mode === 'auto' ? activeClass : inactiveClass;
  if (splitLbl) splitLbl.className = mode === 'split' ? activeClass : inactiveClass;
  if (fullLbl) fullLbl.className = mode === 'full' ? activeClass : inactiveClass;
}

async function processRepurpose() {
  const url = ($('repurposeUrlInput').value || '').trim();
  if (!url) {
    alert('Ingresa una URL de YouTube válida.');
    return;
  }
  const cropMode = getSelectedCropMode();
  const btn = $('btnRepurpose');
  setBusy(btn, true, SPINNER('Analizando caras y recortando con FFmpeg...'));
  try {
    const data = await apiPost('/api/repurpose', { video_url: url, crop_mode: cropMode, brand_id: activeBrandId });
    if (data.status === 'success' && data.clips) {
      repurposedClips = data.clips;
      renderClips();
      $('repurposeResults').classList.remove('hidden');
    } else {
      alert('No se pudieron extraer clips del video.');
    }
  } catch (e) {
    alert('Error al procesar el video: ' + e.message);
  } finally {
    setBusy(btn, false);
  }
}

function renderClips() {
  const grid = $('clipsGrid');
  grid.innerHTML = '';
  repurposedClips.forEach((clip, idx) => {
    const card = document.createElement('div');
    card.className = 'glass-card rounded-2xl p-5 space-y-3 border-cyan-500/20 flex flex-col justify-between';
    const badge = CLIP_BADGES[clip.role_badge] || CLIP_BADGES.cyan;
    const player = clip.video_url
      ? `<video controls class="w-full max-h-80 rounded-lg bg-black" src="${escHtml(safeUrl(clip.video_url))}"></video>
         <div class="flex gap-2">
           <a href="${escHtml(safeUrl(clip.video_url))}" download class="flex-1 text-center py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-[11px] font-semibold">Descargar MP4</a>
           <a href="${escHtml(safeUrl(clip.srt_url))}" download class="flex-1 text-center py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-[11px] font-semibold">Descargar SRT</a>
         </div>`
      : '<div class="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-[11px] text-rose-300">FFmpeg no pudo generar este clip.</div>';
    card.innerHTML = `
      <div class="space-y-3">
        <div class="flex items-center justify-between gap-2">
          <span class="px-2.5 py-1 rounded-md text-[11px] font-bold border ${badge}">${escHtml(clip.role)}</span>
          <span class="text-xs text-gray-400 font-mono">${escHtml(clip.timestamp || clip.duracion || '')}</span>
        </div>
        <h4 class="font-bold text-white text-sm leading-snug">${escHtml(clip.titulo)}</h4>
        ${player}
        <div class="p-3 bg-black/60 rounded-xl border border-white/5 text-xs text-gray-200 italic max-h-28 overflow-y-auto select-all">"${escHtml(clip.statement)}"</div>
        <div class="grid grid-cols-3 gap-1.5">
          <button type="button" data-act="tiktok" class="px-2 py-1.5 rounded-lg bg-black/50 hover:bg-white/10 border border-white/10 text-[10px] text-gray-300">🎵 TikTok</button>
          <button type="button" data-act="reels" class="px-2 py-1.5 rounded-lg bg-black/50 hover:bg-white/10 border border-white/10 text-[10px] text-gray-300">📸 Reels</button>
          <button type="button" data-act="shorts" class="px-2 py-1.5 rounded-lg bg-black/50 hover:bg-white/10 border border-white/10 text-[10px] text-gray-300">🔴 Shorts</button>
        </div>
        <button type="button" data-act="flow" class="w-full py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 text-[11px] font-bold border border-cyan-500/20">Copiar Prompt Google Flow</button>
      </div>
      <button type="button" data-act="studio" class="w-full mt-3 py-2.5 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 font-bold text-xs border border-amber-500/40">Cargar al Taller de Guiones</button>`;
    card.querySelectorAll('[data-act]').forEach((b) => {
      b.addEventListener('click', () => {
        const act = b.dataset.act;
        if (act === 'flow') copyToClipboard(b, clip.prompt_flow);
        else if (act === 'studio') sendEpisodeToProduction(clip.titulo, clip.statement);
        else copySocialCopy(idx, act, b);
      });
    });
    grid.appendChild(card);
  });
}

function copySocialCopy(idx, platform, btn) {
  const clip = repurposedClips[idx];
  const sc = clip && clip.social_copies && clip.social_copies[platform];
  if (!sc) {
    alert('Copy no disponible para esta plataforma.');
    return;
  }
  copyToClipboard(btn, `${sc.copy}\n\n👉 ${sc.cta}\n\n${sc.hashtags}`);
}

function sendEpisodeToProduction(title, hook) {
  switchMode('studio');
  $('scriptTitle').value = title || '';
  $('scriptBody').value = hook || '';
  setText('activeSceneBadge', `Cargado: ${String(title || '').substring(0, 25)}`);
  updateAvdRetentionAnalysis();
}

/* ---------- Brainstorming ---------- */

function chatBubble(html, cls) {
  const box = $('chatHistoryBox');
  const el = document.createElement('div');
  el.className = cls;
  el.innerHTML = html;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  return el;
}

async function sendChatMessage() {
  const input = $('chatInput');
  const msg = (input.value || '').trim();
  if (!msg) return;
  input.value = '';
  const box = $('chatHistoryBox');
  if (!chatHistory.length) box.innerHTML = '';

  chatBubble(`<span class="font-bold text-[10px] text-purple-300 block mb-0.5 uppercase">Tú:</span>${escHtml(msg)}`,
    'p-3 rounded-xl bg-purple-600/30 border border-purple-400/40 text-purple-100 ml-8');
  const loading = chatBubble(SPINNER('Analizando ángulo estratégico...'),
    'p-2.5 rounded-xl bg-black/40 border border-white/10 text-gray-400 flex items-center gap-2');

  try {
    const data = await apiPost('/api/brainstorm', { history: chatHistory, message: msg, brand_id: activeBrandId });
    loading.remove();
    const r = data.result;
    const replyText = r.reply || r.content || '';
    chatHistory.push({ role: 'user', content: msg });
    chatHistory.push({ role: 'assistant', content: replyText });
    
    // Render Assistant message
    chatBubble(`<div class="flex items-center gap-2 mb-1.5"><span class="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 font-extrabold text-[10px] uppercase border border-amber-500/20 tracking-wider">🧠 Copiloto La Mente Observadora</span></div><div class="text-xs text-gray-200 leading-relaxed space-y-2">${escHtml(replyText).replace(/\n\n/g, '<br/><br/>').replace(/\n/g, '<br/>')}</div>`,
      'p-3.5 rounded-xl bg-black/70 border border-white/10 shadow-lg');

    // Render Action Card if provided by Copilot
    if (r.action_card) {
      const card = r.action_card;
      const cardEl = chatBubble(`
        <div class="space-y-2">
          <div class="flex items-center justify-between gap-2 border-b border-amber-500/20 pb-2">
            <span class="text-amber-400 font-extrabold text-xs flex items-center gap-1.5">
              <i class="ph-bold ph-lightning text-sm"></i> Propuesta Lista para Producción
            </span>
            <button type="button" class="btn-execute-card px-3 py-1 rounded-lg bg-gradient-to-r from-amber-500 to-rose-500 hover:from-amber-400 hover:to-rose-400 text-black font-extrabold text-xs shadow-md shadow-amber-500/20 flex items-center gap-1">
              <span>Cargar al Taller</span> <i class="ph-bold ph-arrow-right"></i>
            </button>
          </div>
          <div class="text-white font-bold text-sm">${escHtml(card.title || 'Guion Estratégico')}</div>
          <p class="text-gray-300 text-xs italic">"${escHtml(card.hook || '')}"</p>
          <div class="text-[11px] text-gray-400">${escHtml(card.synopsis || '')}</div>
        </div>`,
        'p-4 rounded-xl bg-gradient-to-br from-amber-950/40 to-black/80 border border-amber-500/40 shadow-xl space-y-2');
      
      cardEl.querySelector('.btn-execute-card').addEventListener('click', () => {
        sendEpisodeToProduction(card.title, card.hook);
      });
    }

    if (r.has_series && r.episodes && r.episodes.length) renderEpisodes(r.series_title, r.episodes);
  } catch (err) {
    loading.remove();
    chatBubble(`Error conectando con el motor de brainstorming: ${escHtml(err.message)}`,
      'p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300');
  }
}

function renderEpisodes(seriesTitle, episodes) {
  chatBubble(`<div class="font-bold text-amber-300 text-xs">${escHtml(seriesTitle)}</div>`, 'pt-2');
  episodes.forEach((ep) => {
    const el = chatBubble(`
      <div class="flex items-center justify-between gap-2">
        <span class="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 font-bold text-[10px] border border-amber-500/20">Episodio ${escHtml(ep.num)}</span>
        <button type="button" class="ep-load px-2.5 py-1 rounded bg-amber-500 hover:bg-amber-400 text-black font-extrabold text-[10px]">Cargar al Taller</button>
      </div>
      <h4 class="font-bold text-white text-xs mt-1">${escHtml(ep.titulo)}</h4>
      <p class="text-[11px] text-gray-300 italic">"${escHtml(ep.hook)}"</p>`,
      'p-3 rounded-xl bg-black/60 border border-amber-500/30 space-y-1');
    el.querySelector('.ep-load').addEventListener('click', () => sendEpisodeToProduction(ep.titulo, ep.hook));
  });
}

/* ---------- Incubadora de canales ---------- */

function researchBox() {
  let box = $('researchResultsBox');
  if (!box) {
    box = document.createElement('div');
    box.id = 'researchResultsBox';
    box.className = 'glass-card rounded-2xl p-6 border-white/10 space-y-4';
    $('sectionResearch').appendChild(box);
  }
  return box;
}

async function conductResearch() {
  const topic = ($('nicheTopicInput').value || '').trim();
  if (!topic) {
    alert('Ingresa un nicho para investigar.');
    return;
  }
  const btn = $('btnResearch');
  setBusy(btn, true, SPINNER('Rastreando YouTube en vivo...'));
  try {
    const data = await apiPost('/api/research', { niche_topic: topic });
    if (data.status !== 'success') throw new Error('Respuesta inválida del servidor');
    const r = data.research || {};
    const p = data.proposal || {};
    lastProposal = p;
    const m = r.metrics || {};
    const names = p.detailed_names || (p.suggested_names || []).map((n) => ({ name: n }));

    const set = (id, v) => { const el = $(id); if (el && v !== undefined) el.value = v; };
    const first = names[0];
    if (first) {
      const n = typeof first === 'string' ? first : first.name;
      set('brandFormName', n);
      set('brandFormHandle', (first && first.handle) || `@${String(n).replace(/\s+/g, '')}`);
    }
    set('brandFormThesis', p.thesis || '');
    if (p.voice) set('brandFormVoice', `${p.voice.name || p.voice.provider || ''}${p.voice.desc ? ' - ' + p.voice.desc : ''}`);
    set('brandFormFlow', p.flow_rules || '');

    const box = researchBox();
    box.innerHTML = `
      <h3 class="font-bold text-white text-base">Resultados de la investigación: ${escHtml(r.topic || topic)}</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
        <div class="p-3 rounded-xl bg-black/40 border border-white/5"><span class="text-gray-400 block">Nivel</span><b class="text-white">${escHtml(m.tier || 'Estándar')}</b></div>
        <div class="p-3 rounded-xl bg-black/40 border border-white/5"><span class="text-gray-400 block">RPM largo</span><b class="text-emerald-300">${escHtml(m.rpm_long || m.rpm_long_format || '-')}</b></div>
        <div class="p-3 rounded-xl bg-black/40 border border-white/5"><span class="text-gray-400 block">RPM shorts</span><b class="text-emerald-300">${escHtml(m.rpm_short || m.rpm_shorts_format || '-')}</b></div>
      </div>
      <div><div class="text-[10px] uppercase text-gray-400 font-semibold mb-1">Nombres sugeridos (clic para aplicar)</div><div id="researchNames" class="flex flex-wrap gap-2"></div></div>
      <div><div class="text-[10px] uppercase text-gray-400 font-semibold mb-1">Outliers reales detectados</div><div id="researchOutliers" class="grid grid-cols-1 md:grid-cols-2 gap-3"></div></div>
      <div><div class="text-[10px] uppercase text-gray-400 font-semibold mb-1">Ángulos de posicionamiento</div>
        <ul class="text-xs text-gray-300 space-y-1">${(r.suggested_angles || []).map((a) => `<li>• ${escHtml(a)}</li>`).join('')}</ul></div>`;

    const namesBox = $('researchNames');
    names.forEach((item) => {
      const n = typeof item === 'string' ? item : item.name;
      const h = (item && item.handle) || `@${String(n).replace(/\s+/g, '')}`;
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'px-3 py-1.5 rounded-xl bg-black/60 hover:bg-amber-500/20 text-xs text-amber-300 font-bold border border-white/10 hover:border-amber-400 transition-all';
      chip.textContent = n;
      chip.addEventListener('click', () => { set('brandFormName', n); set('brandFormHandle', h); });
      namesBox.appendChild(chip);
    });

    const outBox = $('researchOutliers');
    const outliers = r.top_outliers || [];
    if (!outliers.length) {
      outBox.innerHTML = '<p class="text-xs text-gray-400">Sin outliers anómalos inmediatos.</p>';
    }
    outliers.forEach((vid) => {
      const card = document.createElement('div');
      card.className = 'p-3 rounded-xl bg-black/60 border border-cyan-500/30 space-y-2';
      card.innerHTML = `
        <div class="text-[11px] text-cyan-300 font-mono">🔥 ${escHtml(vid.views_formatted)} views</div>
        <h4 class="text-xs font-bold text-white line-clamp-2">${escHtml(vid.title)}</h4>
        <p class="text-[11px] text-gray-400">Canal: ${escHtml(vid.channel)}</p>
        <button type="button" class="out-btn w-full py-1.5 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 font-bold text-xs border border-cyan-500/30">Deconstruir 1 a 1</button>`;
      card.querySelector('.out-btn').addEventListener('click', () => mimicOutlierVideo(vid.url));
      outBox.appendChild(card);
    });
    box.scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    alert('Error al ejecutar la investigación: ' + err.message);
  } finally {
    setBusy(btn, false);
  }
}

/* ---------- Arranque ---------- */

window.addEventListener('DOMContentLoaded', async () => {
  const body = $('scriptBody');
  if (body) body.addEventListener('input', updateAvdRetentionAnalysis);
  setThumbAspect(currentThumbAspect);
  switchMode('radar');
  await reloadBrands();
  updateAvdRetentionAnalysis();
});


// ==========================================
// 9. AI MAGIC VFX & PROMPT EDITOR MODULE
// ==========================================

const VFX_PRESETS = {
  film_noir_punch: "Color grading Film Noir blanco y negro dramático, zoom punch dinámico en momentos clave y lower-third elegante que diga 'VIDSTUDIO' y 'Master Edition'.",
  cyberpunk_neon: "Estilo Cyberpunk con sombras azules profundas y neón magenta, barra de progreso inferior y subtítulos dinámicos de alto impacto.",
  podcast_pro: "Superponer micrófono de podcast al frente con escala y posición natural sin tapar elementos clave, color cálido cinematográfico y lower third.",
  change_clothes: "Cambiar la ropa por un traje ejecutivo negro elegante, iluminación de estudio profesional y relación de aspecto vertical 9:16.",
  kinetic_viral: "Subtítulos estilo Hormozi amarillos con palabras clave destacadas en oro, grano vintage VHS y punch zoom en momentos de énfasis."
};

function applyVfxPreset(presetKey) {
  const promptInput = $('vfxPromptInput');
  if (promptInput && VFX_PRESETS[presetKey]) {
    promptInput.value = VFX_PRESETS[presetKey];
    promptInput.focus();
  }
}

async function triggerVfxRender() {
  const promptInput = $('vfxPromptInput');
  const btn = $('btnRenderVfx');
  const prompt = promptInput ? promptInput.value.trim() : '';
  
  if (!prompt) {
    alert('Por favor escribe una orden o instrucción en lenguaje natural para editar el video.');
    return;
  }

  const aspect = $('vfxAspectSelect') ? $('vfxAspectSelect').value : 'keep';
  const sourceRadio = document.querySelector('input[name="vfxSourceRadio"]:checked');
  const sourceVal = sourceRadio ? sourceRadio.value : 'default';

  const logsContainer = $('vfxLogsContainer');
  if (logsContainer) {
    logsContainer.innerHTML = '<div class="text-fuchsia-400 font-bold">> Enviando orden al Motor VFX de Inteligencia Artificial...</div>';
  }

  const badge = $('vfxExecutionBadge');
  if (badge) {
    badge.innerText = 'Procesando prompt con IA... por favor espera unos segundos.';
  }

  setBusy(btn, true, '<i class="ph-bold ph-spinner animate-spin"></i> Renderizando VFX...');

  try {
    const res = await apiPost('/api/vfx/render', {
      prompt: prompt,
      aspect_ratio: aspect,
      video_source: null
    });

    if (res.status === 'success') {
      // 1. Mostrar Logs
      if (logsContainer && res.logs) {
        logsContainer.innerHTML = res.logs.map(l => `<div class="text-gray-300">> ${escHtml(l)}</div>`).join('');
      }

      // 2. Mostrar Receta JSON
      const recipeBox = $('vfxRecipeContainer');
      const recipeJson = $('vfxRecipeJson');
      if (recipeBox && recipeJson && res.recipe) {
        recipeJson.innerText = JSON.stringify(res.recipe, null, 2);
        recipeBox.classList.remove('hidden');
      }

      // 3. Cargar Video
      const player = $('vfxVideoPlayer');
      const placeholder = $('vfxVideoPlaceholder');
      const actionBtns = $('vfxActionButtons');
      const dlLink = $('vfxDownloadLink');
      const meta = $('vfxResultMeta');

      if (player && res.video_url) {
        player.src = res.video_url;
        player.classList.remove('hidden');
        if (placeholder) placeholder.classList.add('hidden');
        if (actionBtns) actionBtns.classList.remove('hidden');
        if (dlLink) dlLink.href = res.video_url;
        if (meta) meta.innerText = `${res.resolution} | ${res.duration.toFixed(1)}s`;
        player.play().catch(() => {});
      }

      if (badge) {
        badge.innerHTML = '<span class="text-emerald-400 font-bold">¡Video renderizado con éxito!</span>';
      }
    } else {
      throw new Error(res.detail || 'Error desconocido al renderizar el video.');
    }
  } catch (err) {
    console.error('Error VFX:', err);
    if (logsContainer) {
      logsContainer.innerHTML += `<div class="text-rose-400 font-bold">> Error: ${escHtml(err.message)}</div>`;
    }
    if (badge) {
      badge.innerHTML = `<span class="text-rose-400 font-bold">Error: ${escHtml(err.message)}</span>`;
    }
  } finally {
    setBusy(btn, false);
  }
}

async function sendVfxToFunnel() {
  const promptInput = $('vfxPromptInput');
  const title = promptInput && promptInput.value ? 'VFX: ' + promptInput.value.slice(0, 35) + '...' : 'Nuevo Video VFX IA';
  try {
    await apiPost('/api/funnel/projects', {
      title: title,
      status: 'production',
      notes: 'Renderizado con AI Magic VFX por palabras.',
      brand_id: activeBrandId || 'la_mente_observadora'
    });
    alert('¡Video enviado a la columna de Producción en el Embudo!');
    switchMode('funnel');
  } catch (e) {
    alert('Error al enviar al embudo: ' + e.message);
  }
}
