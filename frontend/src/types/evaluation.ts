export interface EvaluationRequest {
  student_id: string;
  question_id: string;
  question_text: string;
  student_answer: string;
  subject?: string;
  difficulty_level?: number;
}

export interface LLMEvaluationOutput {
  is_correct: boolean;
  gap_concept: string;
  hint: string;
}

export interface EvaluationResponse {
  request_id: string;
  student_id: string;
  question_id: string;
  evaluation: LLMEvaluationOutput;
  model_used: string;
  latency_ms: number;
  timestamp: string;
}

export interface EvaluationError {
  request_id: string;
  error_code: string;
  message: string;
  timestamp: string;
}

export type EvaluationState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: EvaluationResponse }
  | { status: 'error'; error: EvaluationError | { error_code: string; message: string } };
