import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import {
  DynamoDBDocumentClient,
  PutCommand,
  GetCommand,
  ScanCommand,
} from '@aws-sdk/lib-dynamodb';

const TABLE_NAME = process.env.TABLE_NAME || 'ShichidaInvoices';

const clientConfig = { region: process.env.AWS_REGION || 'ap-south-1' };
if (process.env.DYNAMODB_ENDPOINT) {
  clientConfig.endpoint = process.env.DYNAMODB_ENDPOINT;
  clientConfig.credentials = { accessKeyId: 'local', secretAccessKey: 'local' };
}

const ddb = DynamoDBDocumentClient.from(
  new DynamoDBClient(clientConfig),
  { marshallOptions: { removeUndefinedValues: true } }
);

const CORS_HEADERS = {
  'Content-Type': 'application/json',
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
};

function ok(body) {
  return { statusCode: 200, headers: CORS_HEADERS, body: JSON.stringify(body) };
}

function err(statusCode, message) {
  return { statusCode, headers: CORS_HEADERS, body: JSON.stringify({ error: message }) };
}

export const handler = async (event) => {
  const method = event.requestContext?.http?.method || event.httpMethod;
  const path = event.rawPath || event.path || '';
  const pathParams = event.pathParameters || {};

  // CORS preflight
  if (method === 'OPTIONS') return { statusCode: 200, headers: CORS_HEADERS, body: '' };

  try {
    // POST /invoices — save invoice
    if (method === 'POST' && path === '/invoices') {
      const body = JSON.parse(event.body || '{}');
      if (!body.invoiceNumber) return err(400, 'invoiceNumber is required');

      const regFee = body.registrationFee || 0;
      const sessionFee = body.sessionFeeAmount || 0;
      const extrasTotal = (body.extraItems || []).reduce((s, e) => s + e.amount * e.quantity, 0);
      const deductionsTotal = (body.deductions || []).reduce((s, e) => s + e.amount * e.quantity, 0);
      const subtotal = regFee + sessionFee + extrasTotal - deductionsTotal;
      const gstPercent = body.gstPercent || 0;
      const gstAmount = Math.round(subtotal * gstPercent / 100);
      const debitBroughtForward = body.debitBroughtForward || 0;
      const totalAmount = subtotal + gstAmount + debitBroughtForward;

      const item = {
        ...body,
        createdAt: body.createdAt || new Date().toISOString(),
        status: 'generated',
        totalAmount,
      };

      await ddb.send(new PutCommand({ TableName: TABLE_NAME, Item: item }));
      return ok({ success: true, invoiceNumber: item.invoiceNumber });
    }

    // GET /invoices/{invoiceNumber} — get one
    if (method === 'GET' && pathParams.invoiceNumber) {
      const result = await ddb.send(
        new GetCommand({ TableName: TABLE_NAME, Key: { invoiceNumber: pathParams.invoiceNumber } })
      );
      if (!result.Item) return err(404, 'Invoice not found');
      return ok(result.Item);
    }

    // GET /invoices — list all
    if (method === 'GET' && path === '/invoices') {
      const result = await ddb.send(
        new ScanCommand({
          TableName: TABLE_NAME,
          ProjectionExpression:
            'invoiceNumber, studentName, parentName, centerCode, invoiceDate, totalAmount, #s, createdAt',
          ExpressionAttributeNames: { '#s': 'status' },
          Limit: 200,
        })
      );
      const items = (result.Items || []).sort((a, b) =>
        (b.invoiceNumber || '').localeCompare(a.invoiceNumber || '')
      );
      return ok({ invoices: items, count: items.length });
    }

    return err(404, 'Not found');
  } catch (e) {
    console.error('Lambda error', e);
    return err(500, e.message);
  }
};
