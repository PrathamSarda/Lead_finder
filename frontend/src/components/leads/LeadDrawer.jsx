import { useState } from "react";
import {
  Building2,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  ExternalLink,
  Globe,
  Mail,
  MapPin,
  Phone,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";

function LinkedInIcon({ className = "h-4 w-4" }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z" />
    </svg>
  );
}

export default function LeadDrawer({ lead, isOpen, onClose }) {
  const [copiedField, setCopiedField] = useState(null);

  if (!isOpen || !lead) return null;

  const copyToClipboard = (text, fieldName) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedField(fieldName);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const isFullLead = lead.lead_tier === "FULL_LEAD";
  const isWebOnly = lead.lead_tier === "WEBSITE_ONLY";
  const isReview = lead.status === "NEEDS_REVIEW";
  const isVerified = lead.status === "VERIFIED";

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="absolute inset-y-0 right-0 flex max-w-full pl-10">
        <div className="relative w-screen max-w-xl bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col">
          {/* Header */}
          <div className="flex items-start justify-between border-b border-slate-800 p-6 bg-slate-950/60">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                {isFullLead && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-bold text-emerald-400 border border-emerald-500/30">
                    <Sparkles className="h-3.5 w-3.5" /> Full Lead (Web + Contact)
                  </span>
                )}
                {isWebOnly && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-500/15 px-3 py-1 text-xs font-bold text-sky-400 border border-sky-500/30">
                    <Globe className="h-3.5 w-3.5" /> Website Verified
                  </span>
                )}
                {isReview && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/15 px-3 py-1 text-xs font-bold text-amber-400 border border-amber-500/30">
                    <ShieldAlert className="h-3.5 w-3.5" /> Needs Review
                  </span>
                )}
                {!isVerified && !isReview && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-400 border border-slate-700">
                    Unresolved
                  </span>
                )}
                <span className="text-xs font-mono text-slate-500">
                  Score: {Number(lead.confidence || 0).toFixed(2)}
                </span>
              </div>
              <h2 className="text-xl font-bold text-white tracking-tight">
                {lead.company_name}
              </h2>
              <div className="flex items-center gap-4 text-xs text-slate-400">
                <span className="flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5 text-slate-500" />
                  {lead.location || "US (Nationwide)"}
                </span>
                <span className="flex items-center gap-1">
                  <Users className="h-3.5 w-3.5 text-slate-500" />
                  1–20 Employees (Small Business)
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Drawer Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Primary Profiles & Contact Channels */}
            <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 space-y-3.5">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Verified LinkedIn & Executive Profiles
              </h3>

              {/* Company LinkedIn */}
              <div className="flex items-center justify-between rounded-lg bg-slate-900 p-3 border border-slate-800/80">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/15 text-sky-400">
                    <LinkedInIcon className="h-4 w-4" />
                  </div>
                  <div>
                    <span className="text-[11px] font-medium text-slate-500 block">Company LinkedIn</span>
                    {lead.company_linkedin_url || lead.linkedin ? (
                      <a
                        href={lead.company_linkedin_url || lead.linkedin}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-semibold text-sky-300 hover:underline flex items-center gap-1.5"
                      >
                        <span className="truncate max-w-xs">{lead.company_linkedin_url || lead.linkedin}</span>
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : (
                      <span className="text-xs text-slate-500 italic">No LinkedIn page resolved</span>
                    )}
                  </div>
                </div>
                {(lead.company_linkedin_url || lead.linkedin) && (
                  <button
                    onClick={() => copyToClipboard(lead.company_linkedin_url || lead.linkedin, "company_linkedin")}
                    className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-300 hover:text-white transition-colors"
                  >
                    {copiedField === "company_linkedin" ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                )}
              </div>

              {/* Decision Maker Direct LinkedIn Profile */}
              <div className="flex items-center justify-between rounded-lg bg-slate-900 p-3 border border-slate-800/80">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/15 text-indigo-400">
                    <Users className="h-4 w-4" />
                  </div>
                  <div>
                    <span className="text-[11px] font-medium text-slate-500 block">
                      Decision Maker: {lead.decision_maker_name || lead.owner_name || "Executive"}
                    </span>
                    {lead.decision_maker_linkedin_url ? (
                      <a
                        href={lead.decision_maker_linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-semibold text-indigo-300 hover:underline flex items-center gap-1.5"
                      >
                        <span className="truncate max-w-xs">{lead.decision_maker_linkedin_url}</span>
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : (
                      <span className="text-xs text-slate-500 italic">No personal profile URL found</span>
                    )}
                  </div>
                </div>
                {lead.decision_maker_linkedin_url && (
                  <button
                    onClick={() => copyToClipboard(lead.decision_maker_linkedin_url, "dm_linkedin")}
                    className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-300 hover:text-white transition-colors"
                  >
                    {copiedField === "dm_linkedin" ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                )}
              </div>

              {/* Phone */}
              <div className="flex items-center justify-between rounded-lg bg-slate-900 p-3 border border-slate-800/80">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
                    <Phone className="h-4 w-4" />
                  </div>
                  <div>
                    <span className="text-[11px] font-medium text-slate-500 block">Verified Phone</span>
                    {lead.phone ? (
                      <a
                        href={`tel:${lead.phone}`}
                        className="text-sm font-semibold text-emerald-300 hover:underline"
                      >
                        {lead.phone}
                      </a>
                    ) : (
                      <span className="text-xs text-slate-500 italic">No phone number extracted</span>
                    )}
                  </div>
                </div>
                {lead.phone && (
                  <button
                    onClick={() => copyToClipboard(lead.phone, "phone")}
                    className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-300 hover:text-white transition-colors"
                  >
                    {copiedField === "phone" ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {/* Official Website Intelligence */}
            <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Domain & Web Presence
              </h3>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Official URL:</span>
                  {lead.website ? (
                    <a
                      href={lead.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 font-semibold text-indigo-400 hover:underline truncate max-w-xs"
                    >
                      <span>{lead.website}</span>
                      <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                    </a>
                  ) : (
                    <span className="text-slate-500 italic">None resolved</span>
                  )}
                </div>

                {lead.phone_source && (
                  <div className="flex items-start justify-between pt-1 border-t border-slate-800/60">
                    <span className="text-slate-400">Phone Provenance Page:</span>
                    <a
                      href={lead.phone_source}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-slate-300 hover:underline truncate max-w-xs text-right font-mono text-[11px]"
                    >
                      {lead.phone_source}
                    </a>
                  </div>
                )}
              </div>
            </div>

            {/* Verification Reason & Decision Logic */}
            <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 space-y-2">
              <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <ShieldCheck className="h-3.5 w-3.5 text-indigo-400" />
                Lead Verification Decision
              </h3>
              <p className="text-xs leading-relaxed text-slate-300 bg-slate-900 p-3 rounded-lg border border-slate-800">
                {lead.status_reason || "Verification status assigned based on domain matching and contact discovery signals."}
              </p>
              <div className="grid grid-cols-2 gap-2 pt-2 text-[11px] text-slate-400">
                <div>
                  <span className="text-slate-500 block">Discovery Sources</span>
                  <span className="font-medium text-slate-300">{lead.source || "FMCSA"}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Resolution Time</span>
                  <span className="font-medium text-slate-300">
                    {lead.elapsed_seconds ? `${lead.elapsed_seconds}s` : "Cached"}
                  </span>
                </div>
              </div>
            </div>

            {/* Top 3 Alternative Candidates for Client Review */}
            {lead.candidate_results && Array.isArray(lead.candidate_results) && lead.candidate_results.length > 0 && (
              <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-amber-400">
                    <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                    Top Candidates for Manual Review
                  </h3>
                  <span className="text-[10px] text-amber-500 font-mono">
                    {lead.candidate_results.length} available
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Review the alternative web destinations identified during discovery to select the genuine business site:
                </p>
                <div className="space-y-2">
                  {lead.candidate_results.slice(0, 3).map((cand, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-slate-800 bg-slate-900/90 p-3 text-xs space-y-1.5 hover:border-indigo-500/50 transition-colors"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-slate-200 line-clamp-1">
                          {idx + 1}. {cand.title || "Alternative Result"}
                        </span>
                        {cand.score && (
                          <span className="shrink-0 text-[10px] font-mono rounded bg-slate-800 px-1.5 py-0.5 text-slate-400 border border-slate-700">
                            Score: {cand.score}
                          </span>
                        )}
                      </div>
                      {cand.url && (
                        <div className="flex items-center justify-between gap-2">
                          <a
                            href={cand.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 font-mono text-[11px] text-indigo-400 hover:underline truncate"
                          >
                            <span className="truncate">{cand.url}</span>
                            <ExternalLink className="h-3 w-3 shrink-0" />
                          </a>
                          <a
                            href={`mailto:info@${cand.url.replace(/^https?:\/\//, '').split('/')[0].replace(/^www\./, '')}?subject=Inquiry for ${encodeURIComponent(lead.company_name)}`}
                            className="shrink-0 rounded bg-indigo-600/20 px-2 py-0.5 text-[10px] font-medium text-indigo-300 hover:bg-indigo-600/30 border border-indigo-500/30 flex items-center gap-1"
                          >
                            <Mail className="h-2.5 w-2.5" />
                            <span>Email</span>
                          </a>
                        </div>
                      )}
                      {cand.snippet && (
                        <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                          {cand.snippet}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Full JSON Raw Data */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Raw Record (Audit Provenance)
                </span>
                <button
                  onClick={() => copyToClipboard(JSON.stringify(lead, null, 2), "json")}
                  className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white transition-colors"
                >
                  {copiedField === "json" ? (
                    <span className="text-emerald-400">JSON Copied</span>
                  ) : (
                    <>
                      <Copy className="h-3 w-3" />
                      <span>Copy JSON</span>
                    </>
                  )}
                </button>
              </div>
              <pre className="terminal-window rounded-xl p-3 text-[10px] text-slate-400 overflow-x-auto max-h-40">
                {JSON.stringify(lead, null, 2)}
              </pre>
            </div>
          </div>

          {/* Drawer Footer Actions */}
          <div className="flex items-center justify-between border-t border-slate-800 bg-slate-950/80 p-4">
            <button
              onClick={onClose}
              className="rounded-xl border border-slate-800 px-4 py-2 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
            >
              Close
            </button>
            <div className="flex items-center gap-2">
              {lead.website && (
                <a
                  href={lead.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 rounded-xl border border-indigo-500/30 bg-indigo-500/10 px-4 py-2 text-xs font-semibold text-indigo-300 hover:bg-indigo-500/20 transition-colors"
                >
                  <span>Visit Website</span>
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
