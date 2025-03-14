// src/lib/types.ts
export interface ClueItem {
  word: string;
  clue: string;
}

export interface CluesData {
  across: Record<string, ClueItem>;
  down: Record<string, ClueItem>;
}

export interface GridGenerationResponse {
  success: boolean;
  message?: string;
  questionImage?: string;
  answerImage?: string;
  cluesStructure?: CluesData;
}

export interface ClueProgressEvent {
  error?: string;
  complete?: boolean;
  progress?: number;
  direction?: string;
  number?: string;
  currentWord?: string;
  clue?: string;
  clues?: CluesData;
}

export interface UpdateCluesResponse {
  success: boolean;
  message?: string;
}

export interface ExportPdfResponse {
  success: boolean;
  message?: string;
  questionPdfUrl?: string;
  answerPdfUrl?: string;
}

export interface UserInfo {
  id: number;
  name: string;
  email?: string;
  profile_image?: string;
  last_active_ip?: string;
  last_active?: string;
}
