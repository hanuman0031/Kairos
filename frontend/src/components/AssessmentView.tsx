'use client';

import { useState, useCallback, type FormEvent } from 'react';
import { useEvaluation } from '@/hooks/useEvaluation';
import type { EvaluationRequest } from '@/types/evaluation';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const SUBJECTS = [
  'Mathematics',
  'Physics',
  'Chemistry',
  'Biology',
  'Computer Science',
  'History',
  'English',
  'Geography',
] as const;

const DIFFICULTY_LEVELS = [1, 2, 3, 4, 5] as const;

const DIFFICULTY_LABELS: Record<number, string> = {
  1: 'Beginner',
  2: 'Elementary',
  3: 'Intermediate',
  4: 'Advanced',
  5: 'Expert',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Animated loading dots rendered inside the submit button. */
function LoadingDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-label="Evaluating">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="inline-block h-1.5 w-1.5 rounded-full bg-white"
          style={{
            animation: `dot-pulse 1.4s ease-in-out ${i * 0.2}s infinite`,
          }}
        />
      ))}
    </span>
  );
}

/** Success icon (checkmark in circle). */
function CheckIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

/** Warning icon (triangle). */
function AlertIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

/** Error icon (X in circle). */
function ErrorIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export function AssessmentView() {
  // Form state
  const [questionText, setQuestionText] = useState('');
  const [studentAnswer, setStudentAnswer] = useState('');
  const [subject, setSubject] = useState('');
  const [difficultyLevel, setDifficultyLevel] = useState<number>(3);

  const { state, evaluate, reset } = useEvaluation();

  const isLoading = state.status === 'loading';

  const handleSubmit = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();

      const request: EvaluationRequest = {
        student_id: 'student_001',
        question_id: `q_${Date.now()}`,
        question_text: questionText.trim(),
        student_answer: studentAnswer.trim(),
        ...(subject ? { subject } : {}),
        ...(difficultyLevel ? { difficulty_level: difficultyLevel } : {}),
      };

      await evaluate(request);
    },
    [questionText, studentAnswer, subject, difficultyLevel, evaluate],
  );

  const handleReset = useCallback(() => {
    reset();
  }, [reset]);

  return (
    <div className="flex min-h-screen flex-col items-center px-4 py-12 sm:py-16">
      {/* ---------------------------------------------------------------- */}
      {/* Branding                                                         */}
      {/* ---------------------------------------------------------------- */}
      <header className="mb-10 text-center animate-fade-in">
        <h1 className="text-5xl sm:text-6xl font-extrabold tracking-tight">
          <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-purple-400 bg-clip-text text-transparent">
            Kairos
          </span>
        </h1>
        <p className="mt-3 text-sm sm:text-base text-slate-400 tracking-wide">
          AI-Powered Micro-Feedback
        </p>
      </header>

      {/* ---------------------------------------------------------------- */}
      {/* Form Card                                                        */}
      {/* ---------------------------------------------------------------- */}
      <div className="w-full max-w-2xl animate-fade-in" style={{ animationDelay: '0.15s' }}>
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 sm:p-8 backdrop-blur-xl shadow-2xl"
        >
          <h2 className="mb-6 text-lg font-semibold text-slate-200">
            Submit an Answer for Evaluation
          </h2>

          {/* Question Text */}
          <div className="mb-5">
            <label
              htmlFor="question-text"
              className="mb-1.5 block text-sm font-medium text-slate-300"
            >
              Question <span className="text-rose-400">*</span>
            </label>
            <textarea
              id="question-text"
              required
              rows={3}
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
              placeholder="Enter the question text..."
              className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none transition-all duration-200 focus:border-indigo-500/50 focus:ring-2 focus:ring-indigo-500/20 resize-none"
            />
          </div>

          {/* Student Answer */}
          <div className="mb-5">
            <label
              htmlFor="student-answer"
              className="mb-1.5 block text-sm font-medium text-slate-300"
            >
              Student Answer <span className="text-rose-400">*</span>
            </label>
            <textarea
              id="student-answer"
              required
              rows={3}
              value={studentAnswer}
              onChange={(e) => setStudentAnswer(e.target.value)}
              placeholder="Enter the student's answer..."
              className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none transition-all duration-200 focus:border-indigo-500/50 focus:ring-2 focus:ring-indigo-500/20 resize-none"
            />
          </div>

          {/* Subject & Difficulty — side by side on sm+ */}
          <div className="mb-6 grid grid-cols-1 gap-5 sm:grid-cols-2">
            {/* Subject */}
            <div>
              <label
                htmlFor="subject"
                className="mb-1.5 block text-sm font-medium text-slate-300"
              >
                Subject
              </label>
              <select
                id="subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-100 outline-none transition-all duration-200 focus:border-indigo-500/50 focus:ring-2 focus:ring-indigo-500/20 appearance-none cursor-pointer"
              >
                <option value="" className="bg-slate-900">
                  Select a subject
                </option>
                {SUBJECTS.map((s) => (
                  <option key={s} value={s} className="bg-slate-900">
                    {s}
                  </option>
                ))}
              </select>
            </div>

            {/* Difficulty Level */}
            <div>
              <label
                htmlFor="difficulty"
                className="mb-1.5 block text-sm font-medium text-slate-300"
              >
                Difficulty —{' '}
                <span className="text-indigo-400 font-semibold">
                  {DIFFICULTY_LABELS[difficultyLevel]}
                </span>
              </label>
              <input
                id="difficulty"
                type="range"
                min={1}
                max={5}
                step={1}
                value={difficultyLevel}
                onChange={(e) => setDifficultyLevel(Number(e.target.value))}
                className="w-full accent-indigo-500 mt-2 cursor-pointer"
              />
              <div className="mt-1 flex justify-between text-[10px] text-slate-500">
                {DIFFICULTY_LEVELS.map((level) => (
                  <span key={level}>{level}</span>
                ))}
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="group relative w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/20 transition-all duration-200 hover:scale-[1.02] hover:shadow-xl hover:shadow-indigo-500/30 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:hover:shadow-lg"
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                Evaluating <LoadingDots />
              </span>
            ) : (
              'Evaluate Answer'
            )}

            {/* Subtle glow behind button on hover */}
            <span className="pointer-events-none absolute inset-0 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 opacity-0 blur-xl transition-opacity duration-300 group-hover:opacity-40" />
          </button>
        </form>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* Feedback Card — Success                                          */}
      {/* ---------------------------------------------------------------- */}
      {state.status === 'success' && (
        <div
          className="mt-8 w-full max-w-2xl animate-slide-up"
          role="region"
          aria-label="Evaluation feedback"
        >
          <div
            className={`rounded-2xl border p-6 sm:p-8 backdrop-blur-xl shadow-2xl ${
              state.data.evaluation.is_correct
                ? 'border-emerald-500/30 bg-emerald-500/[0.04] animate-success-glow'
                : 'border-amber-500/30 bg-amber-500/[0.04] animate-pulse-glow'
            }`}
          >
            {/* Header: Correct / Needs Review */}
            <div className="flex items-center gap-3 mb-6">
              {state.data.evaluation.is_correct ? (
                <>
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/20">
                    <CheckIcon className="h-5 w-5 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-emerald-400">
                      Correct!
                    </h3>
                    <p className="text-xs text-slate-400">
                      Great work — your answer is on point.
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-500/20">
                    <AlertIcon className="h-5 w-5 text-amber-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-amber-400">
                      Needs Review
                    </h3>
                    <p className="text-xs text-slate-400">
                      Let&apos;s identify where you can improve.
                    </p>
                  </div>
                </>
              )}
            </div>

            {/* Knowledge Gap */}
            <div className="mb-4 rounded-xl border border-white/5 bg-white/[0.03] p-4">
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                Knowledge Gap
              </p>
              <p className="text-sm leading-relaxed text-slate-200">
                {state.data.evaluation.gap_concept}
              </p>
            </div>

            {/* Hint */}
            <div className="mb-6 rounded-xl border border-indigo-500/10 bg-indigo-500/[0.04] p-4">
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-widest text-indigo-400">
                💡 Hint
              </p>
              <p className="text-sm leading-relaxed text-slate-200">
                {state.data.evaluation.hint}
              </p>
            </div>

            {/* Metadata footer */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/5 pt-4 text-[11px] text-slate-500">
              <span>
                Model:{' '}
                <span className="text-slate-400">{state.data.model_used}</span>
              </span>
              <span>
                Latency:{' '}
                <span className="text-slate-400">
                  {state.data.latency_ms}ms
                </span>
              </span>
              <span>
                Request:{' '}
                <span className="text-slate-400 font-mono">
                  {state.data.request_id}
                </span>
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Error Card                                                       */}
      {/* ---------------------------------------------------------------- */}
      {state.status === 'error' && (
        <div
          className="mt-8 w-full max-w-2xl animate-slide-up"
          role="alert"
        >
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/[0.04] p-6 sm:p-8 backdrop-blur-xl shadow-2xl animate-error-glow">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-rose-500/20">
                <ErrorIcon className="h-5 w-5 text-rose-400" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-rose-400">
                  Evaluation Failed
                </h3>
                <p className="text-xs text-slate-400">
                  Error code:{' '}
                  <span className="font-mono text-rose-400/80">
                    {state.error.error_code}
                  </span>
                </p>
              </div>
            </div>

            <p className="mb-6 text-sm leading-relaxed text-slate-300">
              {state.error.message}
            </p>

            <button
              type="button"
              onClick={handleReset}
              className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-5 py-2.5 text-sm font-medium text-rose-300 transition-all duration-200 hover:bg-rose-500/20 hover:scale-[1.02] focus:outline-none focus:ring-2 focus:ring-rose-500/30"
            >
              Try Again
            </button>
          </div>
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Footer                                                           */}
      {/* ---------------------------------------------------------------- */}
      <footer className="mt-auto pt-16 pb-6 text-center text-[11px] text-slate-600">
        Built with Next.js &amp; AI · Kairos Platform
      </footer>
    </div>
  );
}
