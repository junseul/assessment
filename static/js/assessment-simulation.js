(() => {
  'use strict';
  const form = document.getElementById('simulation-form');
  const inputs = document.getElementById('simulation-inputs');
  const start = document.getElementById('simulation-start');
  const resume = document.getElementById('simulation-resume');
  const stop = document.getElementById('simulation-stop');
  const download = document.getElementById('simulation-download');
  const status = document.getElementById('simulation-status');
  const error = document.getElementById('simulation-error');
  const progress = document.getElementById('simulation-progress');
  let token = null, running = false, stopRequested = false, done = false, report = null;

  async function post(data) {
    data.set('csrfmiddlewaretoken', form.elements.csrfmiddlewaretoken.value);
    const response = await fetch(form.action, {method: 'POST', body: data});
    if (!response.headers.get('content-type')?.includes('application/json')) {
      throw new Error('로그인 상태 또는 서버 응답을 확인하세요.');
    }
    const result = await response.json();
    if (!response.ok) {
      const fields = result.fields ? Object.values(result.fields).flat().map(e => e.message).join(' ') : '';
      throw new Error((result.error || '요청 실패') + ' ' + fields);
    }
    return result;
  }

  function controls() {
    inputs.disabled = running;
    start.disabled = running;
    resume.disabled = running || !token || done;
    stop.disabled = !running;
    download.disabled = !report || running;
  }

  function logRow(row) {
    const tr = document.createElement('tr');
    [row.observation.task + ' / ' + (row.seq + 1), JSON.stringify(row.effective_action),
      row.simulated_rt_ms, row.llm_latency_ms, row.reason].forEach(value => {
      const td = document.createElement('td');
      td.textContent = value;
      tr.appendChild(td);
    });
    document.getElementById('simulation-log').appendChild(tr);
  }

  function showResult(result) {
    const detail = document.createElement('details');
    detail.open = true;
    const title = document.createElement('summary');
    title.textContent = result.title + ' · ' + result.summary.n_trials + '/' + result.summary.protocol_trials
      + (result.summary.complete_protocol ? '회 완료' : '회 (부분 테스트)');
    detail.appendChild(title);
    if (result.summary.domain_scores) {
      const list = document.createElement('ul');
      result.summary.domain_scores.forEach(domain => {
        const item = document.createElement('li');
        item.textContent = domain.label + ': ' + (domain.score ?? '응답 없음') + ' / 100 · 응답 ' + domain.answered + '/17';
        list.appendChild(item);
      });
      detail.appendChild(list);
    } else {
      const p = document.createElement('p');
      p.textContent = result.summary.final_total !== undefined ? '누적 자원: ' + result.summary.final_total
        : '텍스트 상황 정확도: ' + (result.summary.accuracy * 100).toFixed(1) + '%';
      detail.appendChild(p);
    }
    const pre = document.createElement('pre');
    pre.style.whiteSpace = 'pre-wrap';
    pre.textContent = JSON.stringify(result.summary, null, 2);
    detail.appendChild(pre);
    document.getElementById('simulation-results').appendChild(detail);
  }

  async function run() {
    running = true; stopRequested = false; error.textContent = ''; controls();
    try {
      while (!done && !stopRequested) {
        status.textContent = `LLM 응답 대기 중 · ${report.records.length}/${progress.max}회 완료`;
        const data = new FormData(); data.set('action', 'step'); data.set('state', token);
        const result = await post(data);
        token = result.state; done = result.done;
        report.records.push(result.row);
        progress.value = report.records.length;
        logRow(result.row);
        if (result.completed) {
          report.results.push({task: result.completed.task, title: result.completed.title, summary: result.completed.summary});
          showResult(result.completed);
        }
      }
      report.complete = done;
      status.textContent = `${done ? '완료' : '중지됨'} · ${report.records.length}/${progress.max}회`;
    } catch (e) {
      error.textContent = e.message;
      status.textContent = '실행이 중단되었습니다. 기존 결과를 다운로드하거나 현재 단계에서 재시도할 수 있습니다.';
    } finally { running = false; controls(); }
  }

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (running) return;
    const data = new FormData(form); data.set('action', 'start');
    running = true; controls(); error.textContent = '';
    try {
      const result = await post(data);
      token = result.state; done = false;
      report = {synthetic: true, observation_mode: 'text', complete: false,
        limitation: '실제 화면 조작/사람의 지각·반응시간·채용 타당도 검증이 아님',
        started_at: new Date().toISOString(), ...result.metadata, records: [], results: []};
      progress.max = result.total; progress.value = 0;
      document.getElementById('simulation-log').replaceChildren();
      document.getElementById('simulation-results').replaceChildren();
      await run();
    } catch (e) { error.textContent = e.message; }
    finally { running = false; controls(); }
  });
  resume.addEventListener('click', run);
  stop.addEventListener('click', () => {
    stopRequested = true; stop.disabled = true;
    status.textContent = '진행 중인 LLM 응답을 받은 후 중지합니다.';
  });
  download.addEventListener('click', () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], {type: 'application/json'}));
    const a = document.createElement('a'); a.href = url; a.download = `simulation-${report.id}.json`; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
})();
