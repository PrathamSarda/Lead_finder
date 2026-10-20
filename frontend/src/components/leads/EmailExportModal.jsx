import { useState } from "react";
import { Check, Copy, Mail, Send, X } from "lucide-react";

export default function EmailExportModal({ isOpen, onClose, emails = [] }) {
  const [format, setFormat] = useState("newline"); // 'newline' | 'comma' | 'json'
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const validEmails = Array.from(new Set(emails.filter(Boolean)));

  let formattedText = "";
  if (format === "newline") {
    formattedText = validEmails.join("\n");
  } else if (format === "comma") {
    formattedText = validEmails.join(", ");
  } else if (format === "json") {
    formattedText = JSON.stringify(validEmails, null, 2);
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(formattedText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 p-5 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">
              <Mail className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Export Discovered Emails</h3>
              <p className="text-xs text-slate-400">
                {validEmails.length} verified company email addresses ready for outreach
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          {/* Format selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-medium">Format:</span>
            {[
              { id: "newline", label: "One per line" },
              { id: "comma", label: "Comma separated" },
              { id: "json", label: "JSON Array" },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setFormat(f.id)}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium border transition-colors ${
                  format === f.id
                    ? "border-indigo-500 bg-indigo-500/20 text-indigo-300 font-semibold"
                    : "border-slate-800 bg-slate-950 text-slate-400 hover:bg-slate-800"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Textarea */}
          <textarea
            readOnly
            value={formattedText}
            rows={10}
            className="w-full rounded-xl border border-slate-800 bg-slate-950 p-3 font-mono text-xs text-slate-300 focus:outline-none select-all"
          />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-800 bg-slate-950/80 p-4">
          <button
            onClick={onClose}
            className="rounded-xl border border-slate-800 px-4 py-2 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            Close
          </button>
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 transition-all active:scale-[0.98]"
          >
            {copied ? (
              <>
                <Check className="h-4 w-4 text-emerald-400" />
                <span>Copied to Clipboard!</span>
              </>
            ) : (
              <>
                <Copy className="h-4 w-4" />
                <span>Copy All {validEmails.length} Emails</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
