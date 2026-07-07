/**
 * Reusable loading indicator. Use `fullScreen` for page-level loading states.
 */
export default function Loading({ label = "Loading...", fullScreen = false }) {
  const content = (
    <div className="flex flex-col items-center gap-3 text-slate-500">
      <span className="h-8 w-8 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" />
      <span className="text-sm">{label}</span>
    </div>
  );

  if (fullScreen) {
    return <div className="flex h-screen w-full items-center justify-center">{content}</div>;
  }

  return <div className="flex w-full items-center justify-center py-10">{content}</div>;
}
