// src/lib/api.ts
import type { CluesData, GridGenerationResponse, UpdateCluesResponse, ExportPdfResponse, UserInfo } from './types';

export function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

export const clientId = generateUUID();

export function getApiHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json'
  };
}

export async function generateGrid(words: string): Promise<GridGenerationResponse> {
  const response = await fetch('/api/generate_grid', {
    method: 'POST',
    headers: getApiHeaders(),
    body: JSON.stringify({
      words,
      clientId,
      maxAttempts: 30
    }),
    credentials: 'include', // Include cookies in the request
  });

  return await response.json();
}

export function streamClues(): EventSource {
  return new EventSource(`/api/stream_clues?clientId=${clientId}`, { withCredentials: true });
}

export async function updateClues(clues: CluesData): Promise<UpdateCluesResponse> {
  const response = await fetch('/api/update_clues', {
    method: 'POST',
    headers: getApiHeaders(),
    body: JSON.stringify({
      clientId,
      clues
    }),
    credentials: 'include', // Include cookies in the request
  });

  return await response.json();
}

export async function exportPdf(): Promise<ExportPdfResponse> {
  const response = await fetch('/api/export_pdf', {
    method: 'POST',
    headers: getApiHeaders(),
    body: JSON.stringify({
      clientId
    }),
    credentials: 'include', // Include cookies in the request
  });

  return await response.json();
}

export async function cleanup(): Promise<void> {
  try {
    await fetch('/api/cleanup', {
      method: 'POST',
      headers: getApiHeaders(),
      body: JSON.stringify({
        clientId
      }),
      credentials: 'include', // Include cookies in the request
      keepalive: true
    });
  } catch (error) {
    console.error('Error during cleanup:', error);
  }
}

// Function to check if the user is authenticated
export async function checkAuth(): Promise<UserInfo | null> {
  try {
    const response = await fetch('https://auth.yfzhou.fyi/webapi/user', {
      method: 'GET',
      credentials: 'include',
    });
    
    if (response.ok) {
      return await response.json();
    }
    return null;
  } catch (error) {
    console.error('Error checking authentication:', error);
    return null;
  }
}
