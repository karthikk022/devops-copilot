import express from 'express';
import pino from 'pino';
import pinoHttp from 'pino-http';
import client from 'prom-client';

const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  formatters: {
    level: (label) => ({ level: label }),
  },
  timestamp: pino.stdTimeFunctions.isoTime,
});

const app = express();
app.use(express.json());
app.use(pinoHttp({ logger }));

const register = new client.Registry();
client.collectDefaultMetrics({ register });

const httpRequestsTotal = new client.Counter({
  name: 'http_requests_total',
  help: 'Total HTTP requests',
  labelNames: ['method', 'route', 'status'],
  registers: [register],
});

const httpRequestDuration = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request duration',
  labelNames: ['method', 'route', 'status'],
  buckets: [0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10],
  registers: [register],
});

const memoryLeak = [];
let unhandledCount = 0;
let requestCount = 0;

app.use((req, res, next) => {
  const start = process.hrtime.bigint();
  res.on('finish', () => {
    const duration = Number(process.hrtime.bigint() - start) / 1e9;
    const route = req.route?.path || req.path;
    httpRequestsTotal.inc({ method: req.method, route, status: res.statusCode });
    httpRequestDuration.observe({ method: req.method, route, status: res.statusCode }, duration);
  });
  next();
});

const users = new Map([
  ['1', { id: '1', name: 'Alice', email: 'alice@example.com' }],
  ['2', { id: '2', name: 'Bob', email: 'bob@example.com' }],
]);

app.get('/', (req, res) => {
  res.json({
    service: 'sample-api',
    version: '1.0.0',
    node: process.version,
    uptime: process.uptime(),
    endpoints: ['/healthz', '/api/users/:id', '/api/slow', '/api/error', '/api/leak', '/api/crash', '/metrics'],
  });
});

app.get('/healthz', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/users/:id', async (req, res) => {
  requestCount++;
  if (requestCount % 7 === 0) {
    logger.error({ userId: req.params.id, attempt: requestCount }, 'database connection timeout');
    return res.status(500).json({ error: 'database connection timeout' });
  }
  await new Promise((r) => setTimeout(r, 20 + Math.random() * 80));
  const user = users.get(req.params.id);
  if (!user) return res.status(404).json({ error: 'user not found' });
  res.json(user);
});

app.get('/api/slow', async (req, res) => {
  const delay = 2000 + Math.random() * 6000;
  logger.warn({ delay_ms: delay }, 'slow endpoint hit, simulating long query');
  await new Promise((r) => setTimeout(r, delay));
  res.json({ result: 'finally done', delay_ms: Math.round(delay) });
});

app.get('/api/error', (req, res) => {
  logger.error('intentional error endpoint hit');
  throw new Error('intentional failure for copilot demo');
});

app.get('/api/leak', (req, res) => {
  const chunk = 'x'.repeat(1024 * 100);
  for (let i = 0; i < 50; i++) memoryLeak.push(chunk + Date.now() + i);
  const heapMB = (process.memoryUsage().heapUsed / 1024 / 1024).toFixed(2);
  logger.warn({ heap_mb: heapMB, chunks: memoryLeak.length }, 'memory leak endpoint hit');
  res.json({ heap_mb: heapMB, chunks: memoryLeak.length });
});

app.get('/api/crash', (req, res) => {
  unhandledCount++;
  Promise.reject(new Error(`unhandled rejection #${unhandledCount}`));
  res.json({ triggered: true });
});

app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

app.use((err, req, res, next) => {
  logger.error({ err: err.message, stack: err.stack }, 'unhandled error');
  res.status(500).json({ error: err.message });
});

process.on('unhandledRejection', (reason) => {
  logger.fatal({ reason: String(reason) }, 'unhandled promise rejection');
});

const port = Number(process.env.PORT) || 3000;
const server = app.listen(port, '0.0.0.0', () => {
  logger.info({ port }, 'sample-api listening');
});

process.on('SIGTERM', () => {
  logger.info('SIGTERM received, refusing graceful shutdown (intentional bug)');
});
