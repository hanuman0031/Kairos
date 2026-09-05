import { AssessmentView } from '@/components/AssessmentView';

export default function HomePage() {
  return (
    <main className="grid-bg min-h-screen relative">
      {/* Ambient glow orbs for visual depth */}
      <div
        className="pointer-events-none fixed inset-0 overflow-hidden"
        aria-hidden="true"
      >
        <div className="absolute -top-40 -left-40 h-[500px] w-[500px] rounded-full bg-indigo-600/10 blur-[128px]" />
        <div className="absolute -bottom-40 -right-40 h-[500px] w-[500px] rounded-full bg-violet-600/10 blur-[128px]" />
      </div>

      {/* Content */}
      <div className="relative z-10">
        <AssessmentView />
      </div>
    </main>
  );
}
