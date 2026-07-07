/**
 * Reusable content container with optional title/description header.
 */
export default function Card({ title, description, actions, children, className = "" }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>
      {(title || description || actions) && (
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-5 py-4">
          <div>
            {title && <h3 className="text-base font-semibold text-slate-900">{title}</h3>}
            {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className="px-5 py-4">{children}</div>
    </div>
  );
}
