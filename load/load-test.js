// Uso: k6 run -e URL=http://IP:8000/cpu -e RATE=20 -e DURATION=60s -e OUT=resultado.json loadtest.js
import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';

const servico = new Trend('servico_ms');

const URL = __ENV.URL ;

if (!URL) {
  throw new Error('Informe a URL');
}

const RATE = parseInt(__ENV.RATE || '10');
const DURATION = __ENV.DURATION || '60s';
const OUT = __ENV.OUT || 'summary.json';

export const options = {
  scenarios: {
    carga: {
      executor: 'constant-arrival-rate',
      rate: RATE,
      timeUnit: '1s',
      duration: DURATION,
      preAllocatedVUs: Math.max(10, RATE),
      maxVUs: Math.max(200, RATE * 10),
    },
  },
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  const res = http.get(URL, { timeout: '30s' });
  const ok = check(res, { 'status 200': (r) => r.status === 200 });
  if (ok) {
    try {
      servico.add(res.json('tempo_servico_s') * 1000);
    } catch (e) {
      throw new Error('Sem respostas coletadas');
    }
  }
}

export function handleSummary(data) {
  const d = data.metrics.http_req_duration.values;
  const out = {
    url: URL,
    rate_target: RATE,
    reqs: data.metrics.http_reqs.values.count,
    throughput: data.metrics.http_reqs.values.rate,
    fail_rate: data.metrics.http_req_failed ? data.metrics.http_req_failed.values.rate : 0,
    dropped: data.metrics.dropped_iterations ? data.metrics.dropped_iterations.values.count : 0,
    avg_ms: d.avg,
    p50_ms: d.med,
    p90_ms: d['p(90)'],
    p95_ms: d['p(95)'],
    p99_ms: d['p(99)'],
    max_ms: d.max,
  };
  if (data.metrics.servico_ms) {
    out.servico_avg_ms = data.metrics.servico_ms.values.avg;
    out.servico_p95_ms = data.metrics.servico_ms.values['p(95)'];
  }
  return {
    [OUT]: JSON.stringify(out, null, 2),
    stdout: `rate=${RATE} thr=${out.throughput.toFixed(1)}/s avg=${out.avg_ms.toFixed(1)}ms p95=${out.p95_ms.toFixed(1)}ms fail=${(out.fail_rate * 100).toFixed(1)}% dropped=${out.dropped}\n`,
  };
}