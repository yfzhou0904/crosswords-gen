// src/lib/api.ts
import type { CluesData, GridGenerationResponse, UpdateCluesResponse, ExportPdfResponse } from './types';

export function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

export const clientId = generateUUID();

export function getApiHeaders(secretKey: string): HeadersInit {
  if (!secretKey) {
    throw new Error('Secret key is required');
  }
  return {
    'Content-Type': 'application/json',
    'X-Secret-Key': secretKey
  };
}

export async function generateGrid(words: string, secretKey: string): Promise<GridGenerationResponse> {
  const response = await fetch('/api/generate_grid', {
    method: 'POST',
    headers: getApiHeaders(secretKey),
    body: JSON.stringify({
      words,
      clientId,
      maxAttempts: 30
    }),
  });

  return await response.json();
}

export function streamClues(secretKey: string): EventSource {
  return new EventSource(`/api/stream_clues?clientId=${clientId}&secret=${encodeURIComponent(secretKey)}`);
}

export async function updateClues(clues: CluesData, secretKey: string): Promise<UpdateCluesResponse> {
  const response = await fetch('/api/update_clues', {
    method: 'POST',
    headers: getApiHeaders(secretKey),
    body: JSON.stringify({
      clientId,
      clues
    }),
  });

  return await response.json();
}

export async function exportPdf(secretKey: string): Promise<ExportPdfResponse> {
  const response = await fetch('/api/export_pdf', {
    method: 'POST',
    headers: getApiHeaders(secretKey),
    body: JSON.stringify({
      clientId
    }),
  });

  return await response.json();
}

export async function cleanup(secretKey: string): Promise<void> {
  try {
    await fetch('/api/cleanup', {
      method: 'POST',
      headers: getApiHeaders(secretKey),
      body: JSON.stringify({
        clientId
      }),
      keepalive: true
    });
  } catch (error) {
    console.error('Error during cleanup:', error);
  }
}
