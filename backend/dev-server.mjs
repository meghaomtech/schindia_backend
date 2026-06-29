// Local dev API server — runs the Lambda handler directly against DynamoDB Local.
// Start with: node backend/dev-server.mjs
// Requires DynamoDB Local on port 8000: docker compose up -d

import http from 'http';
import { DynamoDBClient, CreateTableCommand, DescribeTableCommand } from '@aws-sdk/client-dynamodb';
import { handler } from './lambda/index.mjs';

const PORT = 3001;
const TABLE_NAME = 'ShichidaInvoices';
const DYNAMODB_ENDPOINT = 'http://localhost:8000';

// Point the Lambda handler at local DynamoDB
process.env.TABLE_NAME = TABLE_NAME;
process.env.AWS_REGION = 'local';
process.env.DYNAMODB_ENDPOINT = DYNAMODB_ENDPOINT;

const dbClient = new DynamoDBClient({
  endpoint: DYNAMODB_ENDPOINT,
  region: 'local',
  credentials: { accessKeyId: 'local', secretAccessKey: 'local' },
});

async function ensureTable() {
  try {
    await dbClient.send(new DescribeTableCommand({ TableName: TABLE_NAME }));
    console.log(`  Table "${TABLE_NAME}" ready`);
  } catch {
    await dbClient.send(new CreateTableCommand({
      TableName: TABLE_NAME,
      AttributeDefinitions: [{ AttributeName: 'invoiceNumber', AttributeType: 'S' }],
      KeySchema: [{ AttributeName: 'invoiceNumber', KeyType: 'HASH' }],
      BillingMode: 'PAY_PER_REQUEST',
    }));
    console.log(`  Table "${TABLE_NAME}" created`);
  }
}

async function buildLambdaEvent(req) {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const pathParams = {};
  const invoiceMatch = url.pathname.match(/^\/invoices\/(.+)$/);
  if (invoiceMatch) pathParams.invoiceNumber = decodeURIComponent(invoiceMatch[1]);

  let body = '';
  for await (const chunk of req) body += chunk;

  return {
    requestContext: { http: { method: req.method, path: url.pathname } },
    rawPath: url.pathname,
    pathParameters: Object.keys(pathParams).length ? pathParams : null,
    body: body || null,
  };
}

const server = http.createServer(async (req, res) => {
  try {
    const event = await buildLambdaEvent(req);
    const result = await handler(event);
    Object.entries(result.headers || {}).forEach(([k, v]) => res.setHeader(k, v));
    res.writeHead(result.statusCode);
    res.end(result.body ?? '');
  } catch (e) {
    console.error('Dev server error:', e);
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: e.message }));
  }
});

try {
  await ensureTable();
} catch (e) {
  console.error('\n  ❌  Cannot connect to DynamoDB Local.');
  console.error('     Make sure Docker is running: docker compose up -d\n');
  process.exit(1);
}

server.listen(PORT, () => {
  console.log(`\n  ✅  Local API running at http://localhost:${PORT}`);
  console.log(`      DynamoDB Local     : ${DYNAMODB_ENDPOINT}`);
  console.log(`      Table              : ${TABLE_NAME}\n`);
});
