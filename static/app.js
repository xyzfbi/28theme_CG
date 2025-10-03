const form = document.getElementById('composer-form');
const previewArea = document.getElementById('preview-area');
const btnPreview = document.getElementById('btn-preview');
const btnExport = document.getElementById('btn-export');
const btnDownloadPreview = document.getElementById('btn-download-preview');
const progressBox = document.getElementById('export-progress');
const progressValue = document.getElementById('progress-value');
const barFill = document.getElementById('bar-fill');
const btnDownloadVideo = document.getElementById('btn-download-video');
let currentJobId = null;
const widthSelect = document.querySelector('[name="output_width"]');
const heightSelect = document.querySelector('[name="output_height"]');
const speakerWidthInput = document.querySelector('[name="speaker_width"]');
const speakerHeightInput = document.querySelector('[name="speaker_height"]');
const speakerWidthDisp = document.getElementById('speaker_width_disp');
const speakerHeightDisp = document.getElementById('speaker_height_disp');
const platePaddingInput = document.querySelector('[name="plate_padding"]');
const platePaddingDisp = document.getElementById('plate_padding_disp');

function formToFormData(formEl) {
  const data = new FormData();
  const fileBackground = formEl.querySelector('input[name="background"]').files[0];
  const fileSpeaker1 = formEl.querySelector('input[name="speaker1"]').files[0];
  const fileSpeaker2 = formEl.querySelector('input[name="speaker2"]').files[0];
  if (!fileBackground || !fileSpeaker1 || !fileSpeaker2) {
    throw new Error('Загрузите все три файла');
  }
  data.append('background', fileBackground);
  data.append('speaker1', fileSpeaker1);
  data.append('speaker2', fileSpeaker2);

  const fields = [
    'speaker1_name','speaker2_name','speaker_width','speaker_height','manual_font_size',
    'font_family','font_color','plate_bg_color','plate_border_color','plate_border_width','plate_padding',
    'output_width','output_height','fps','ffmpeg_preset','ffmpeg_crf'
  ];
  for (const name of fields) {
    const el = formEl.querySelector(`[name="${name}"]`);
    data.append(name, el.value);
  }

  // GPU: всегда включено
  data.append('use_gpu', 'true');
  return data;
}

function applySpeakerBounds() {
  const outW = parseInt(widthSelect.value, 10);
  const outH = parseInt(heightSelect.value, 10);
  const maxW = Math.max(1, Math.floor(outW * 0.46));
  const maxH = Math.max(1, Math.floor(outH * 0.55));
  speakerWidthInput.max = String(maxW);
  speakerHeightInput.max = String(maxH);
  if (parseInt(speakerWidthInput.value || '0', 10) > maxW) speakerWidthInput.value = String(maxW);
  if (parseInt(speakerHeightInput.value || '0', 10) > maxH) speakerHeightInput.value = String(maxH);
  speakerWidthDisp.textContent = speakerWidthInput.value;
  speakerHeightDisp.textContent = speakerHeightInput.value;
}

widthSelect.addEventListener('change', applySpeakerBounds);
heightSelect.addEventListener('change', applySpeakerBounds);
applySpeakerBounds();

speakerWidthInput.addEventListener('input', () => { speakerWidthDisp.textContent = speakerWidthInput.value; });
speakerHeightInput.addEventListener('input', () => { speakerHeightDisp.textContent = speakerHeightInput.value; });
platePaddingInput.addEventListener('input', () => { platePaddingDisp.textContent = platePaddingInput.value; });

// dnd удалён

// Only auto-trigger preview when all files are present
function hasAllFiles() {
  const b = form.querySelector('input[name="background"]').files[0];
  const s1 = form.querySelector('input[name="speaker1"]').files[0];
  const s2 = form.querySelector('input[name="speaker2"]').files[0];
  return !!(b && s1 && s2);
}

async function callApi(endpoint, formData) {
  const res = await fetch(endpoint, { method: 'POST', body: formData });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || 'API error');
  }
  return res;
}

function setLoading(targetBtn, isLoading) {
  targetBtn.disabled = isLoading;
  targetBtn.dataset.loading = isLoading ? '1' : '';
  targetBtn.textContent = isLoading ? 'Подождите…' : targetBtn.id === 'btn-preview' ? 'Сгенерировать предпросмотр' : 'Создать видео';
}

btnPreview.addEventListener('click', async () => {
  try {
    const fd = formToFormData(form);
    setLoading(btnPreview, true);
    const res = await callApi('/api/preview', fd);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    previewArea.innerHTML = '';
    const img = document.createElement('img');
    img.src = url;
    previewArea.appendChild(img);
    btnDownloadPreview.disabled = false;
    btnDownloadPreview.onclick = () => {
      const a = document.createElement('a');
      a.href = url; a.download = 'preview.jpg'; a.click();
    };
  } catch (e) {
    alert(e.message || e);
  } finally {
    setLoading(btnPreview, false);
  }
});

// Авто-превью на изменения
function setupAutoPreview() {
  const trigger = () => {
    if (btnPreview.disabled) return; // простая защита от спама
    if (!hasAllFiles()) return; // триггер только если все файлы загружены
    btnPreview.click();
  };
  // изменения конфигурации
  form.querySelectorAll('input, select').forEach(el => {
    el.addEventListener('change', trigger);
    if (el.type === 'range' || el.type === 'color' || el.type === 'text' || el.type === 'number') {
      el.addEventListener('input', () => { clearTimeout(el._t); el._t = setTimeout(trigger, 400); });
    }
  });
  // файлы — показываем превью после дропа/выбора
  form.querySelectorAll('input[type="file"]').forEach(el => {
    el.addEventListener('change', trigger);
  });
}
setupAutoPreview();

btnExport.addEventListener('click', async () => {
  try {
    if (!hasAllFiles()) { alert('Загрузите фон и оба видео прежде чем экспортировать'); return; }
    const fd = formToFormData(form);
    setLoading(btnExport, true);
    // Start export job
    const startRes = await callApi('/api/export', fd);
    const { job_id } = await startRes.json();
    currentJobId = job_id;
    progressBox.classList.remove('hidden');
    btnDownloadVideo.disabled = true;
    await pollProgress(job_id);
  } catch (e) {
    alert(e.message || e);
  } finally {
    setLoading(btnExport, false);
  }
});

async function pollProgress(jobId) {
  const poll = async () => {
    const r = await fetch(`/api/export/status/${jobId}`);
    if (!r.ok) throw new Error('status error');
    const { status, progress, error } = await r.json();
    progressValue.textContent = String(Math.floor(progress));
    barFill.style.width = `${Math.floor(progress)}%`;
    if (status === 'done') {
      btnDownloadVideo.disabled = false;
      btnDownloadVideo.onclick = async () => {
        const dl = await fetch(`/api/export/download/${jobId}`);
        if (!dl.ok) { alert('Файл ещё не готов'); return; }
        const blob = await dl.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'meeting_output.mp4'; a.click();
      };
      return true;
    }
    if (status === 'error') { alert('Ошибка рендера: ' + (error || '')); return true; }
    return false;
  };

  // Simple interval polling
  const interval = setInterval(async () => {
    try {
      const done = await poll();
      if (done) clearInterval(interval);
    } catch (e) {
      clearInterval(interval);
      console.error(e);
    }
  }, 1000);
}

