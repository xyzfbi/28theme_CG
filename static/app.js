const form = document.getElementById('composer-form');
const previewArea = document.getElementById('preview-area');
const btnPreview = document.getElementById('btn-preview');
const btnExport = document.getElementById('btn-export');
const btnDownloadPreview = document.getElementById('btn-download-preview');

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
    'font_color','plate_bg_color','plate_border_color','plate_border_width','plate_padding',
    'output_width','output_height','fps','ffmpeg_preset','ffmpeg_crf'
  ];
  for (const name of fields) {
    const el = formEl.querySelector(`[name="${name}"]`);
    data.append(name, el.type === 'checkbox' ? (el.checked ? 'true' : 'false') : el.value);
  }

  const useGpuEl = formEl.querySelector('[name="use_gpu"]');
  data.append('use_gpu', useGpuEl.checked ? 'true' : 'false');
  return data;
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

btnExport.addEventListener('click', async () => {
  try {
    const fd = formToFormData(form);
    setLoading(btnExport, true);
    const res = await callApi('/api/export', fd);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'meeting_output.mp4'; a.click();
  } catch (e) {
    alert(e.message || e);
  } finally {
    setLoading(btnExport, false);
  }
});

