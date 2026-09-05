'use client';

import { useReducer, useCallback, useRef, useEffect } from 'react';
import type {
  EvaluationRequest,
  EvaluationResponse,
  EvaluationError,
  EvaluationState,
} from '@/types/evaluation';

// ---------------------------------------------------------------------------
// Action types – discriminated union for the reducer
// ---------------------------------------------------------------------------
type EvaluationAction =
  | { type: 'EVALUATE_START' }
  | { type: 'EVALUATE_SUCCESS'; payload: EvaluationResponse }
  | { type: 'EVALUATE_ERROR'; payload: EvaluationError | { error_code: string; message: string } }
  | { type: 'RESET' };

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------
function evaluationReducer(_state: EvaluationState, action: EvaluationAction): EvaluationState {
  switch (action.type) {
    case 'EVALUATE_START':
      return { status: 'loading' };
    case 'EVALUATE_SUCCESS':
      return { status: 'success', data: action.payload };
    case 'EVALUATE_ERROR':
      return { status: 'error', error: action.payload };
    case 'RESET':
      return { status: 'idle' };
    default:
      return _state;
  }
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const TIMEOUT_MS = 4_000;
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const EVALUATE_ENDPOINT = `${API_BASE}/api/v1/evaluate`;

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export interface UseEvaluationReturn {
  state: EvaluationState;
  evaluate: (req: EvaluationRequest) => Promise<void>;
  reset: () => void;
}

export function useEvaluation(): UseEvaluationReturn {
  const [state, dispatch] = useReducer(evaluationReducer, { status: 'idle' });
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cleanup any in-flight request on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const evaluate = useCallback(async (req: EvaluationRequest): Promise<void> => {
    // Cancel any previous in-flight request
    abortControllerRef.current?.abort();

    const controller = new AbortController();
    abortControllerRef.current = controller;

    // 4-second timeout
    const timeoutId = setTimeout(() => {
      controller.abort();
    }, TIMEOUT_MS);

    dispatch({ type: 'EVALUATE_START' });

    try {
      const response = await fetch(EVALUATE_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        // Attempt to parse structured error from the backend
        let errorPayload: EvaluationError | { error_code: string; message: string };
        try {
          errorPayload = (await response.json()) as EvaluationError;
        } catch {
          errorPayload = {
            error_code: `HTTP_${response.status}`,
            message: response.statusText || 'An unexpected error occurred.',
          };
        }
        dispatch({ type: 'EVALUATE_ERROR', payload: errorPayload });
        return;
      }

      const data = (await response.json()) as EvaluationResponse;
      dispatch({ type: 'EVALUATE_SUCCESS', payload: data });
    } catch (err: unknown) {
      clearTimeout(timeoutId);

      // Distinguish between timeout abort and other errors
      if (err instanceof DOMException && err.name === 'AbortError') {
        dispatch({
          type: 'EVALUATE_ERROR',
          payload: {
            error_code: 'TIMEOUT',
            message: 'The evaluation service is taking too long. Please try again.',
          },
        });
        return;
      }

      dispatch({
        type: 'EVALUATE_ERROR',
        payload: {
          error_code: 'NETWORK_ERROR',
          message:
            err instanceof Error
              ? err.message
              : 'A network error occurred. Please check your connection and try again.',
        },
      });
    }
  }, []);

  const reset = useCallback(() => {
    abortControllerRef.current?.abort();
    dispatch({ type: 'RESET' });
  }, []);

  return { state, evaluate, reset };
}
