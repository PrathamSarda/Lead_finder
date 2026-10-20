import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  Download,
  FileSpreadsheet,
  Globe,
  Loader2,
  Play,
  RotateCcw,
  Sparkles,
  StopCircle,
  Terminal,
  X,
  Zap,
} from "lucide-react";
import { leadsApi } from "../../api/leads";

const US_STATES = [
  { code: "", name: "All US States (Random Sample)" },
  { code: "TX", name: "Texas (TX)" },
  { code: "GA", name: "Georgia (GA)" },
  { code: "CA", name: "California (CA)" },
  { code: "FL", name: "Florida (FL)" },
  { code: "PA", name: "Pennsylvania (PA)" },
  { code: "OH", name: "Ohio (OH)" },
  { code: "IL", name: "Illinois (IL)" },
  { code: "NC", name: "North Carolina (NC)" },
  { code: "MI", name: "Michigan (MI)" },
];

const PRESET_COUNTS = [
  { label: "5 (Fast Benchmark)", value: 5, tip: "Instant validation test" },
  { label: "10 (Standard Run)", value: 10, tip: "Quick sample batch" },
  { label: "25 (Extended Batch)", value: 25, tip: "Deeper enrichment test" },
  { label: "80 (Daily Goal)", value: 80, tip: "Target daily volume" },
];

export default function RunModal({ isOpen, onClose, onRunComplete }) {
  const [count, setCount] = useState(10);
  const [selectedState, setSelectedState] = useState("");
  const [mode, setMode] = useState("discovery"); // 'discovery' | 'test_batch'
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [runState, setRunState] = useState({
    status: "idle",
    current_step: "Idle",
    processed_count: 0,
    requested_count: 10,
    verified_count: 0,
    full_lead_count: 0,
    elapsed_seconds: 0,
    current_company: null,
    logs: [],
    error: null,
  });

  const logsEndRef = useRef(null);

  // Poll run status while open
  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    const fetchStatus = async () => {
      try {
        const data = await leadsApi.getRunStatus();
        if (isMounted) {
          setRunState(data);
          if (data.status === "completed" && onRunComplete) {
            onRunComplete();
          }
        }
      } catch (err) {
        console.error("Error polling run status:", err);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 1500);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [isOpen, onRunComplete]);

  // Auto scroll logs window
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [runState.logs]);

  if (!isOpen) return null;

  const isRunning = runState.status === "running";
  const isCompleted = runState.status === "completed";
  const isError = runState.status === "error";

  const progressPercent =
    runState.requested_count > 0
      ? Math.min(100, Math.round((runState.processed_count / runState.requested_count) * 100))
      : 0;

  const handleStartRun = async () => {
    setIsSubmitting(true);
    try {
      await leadsApi.triggerRun({
        count: Number(count),
        state: selectedState || null,
        mode,
      });
      // immediate refresh
      const data = await leadsApi.getRunStatus();
      setRunState(data);
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to trigger pipeline run.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelRun = async () => {
    try {
      await leadsApi.cancelRun();
    } catch (err) {
      console.error("Cancel failed:", err);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative flex max-h-[90vh] w-full max-w-3xl flex-col rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl shadow-indigo-500/10 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              <Zap className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                Run Lead Discovery Pipeline
                {isRunning && (
                  <span className="flex items-center gap-1.5 rounded-full bg-amber-500/20 px-2.5 py-0.5 text-xs font-semibold text-amber-400 border border-amber-500/30">
                    <Loader2 className="h-3 w-3 animate-spin" /> In Progress
                  </span>
                )}
                {isCompleted && (
                  <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-xs font-semibold text-emerald-400 border border-emerald-500/30">
                    <CheckCircle2 className="h-3 w-3" /> Completed
                  </span>
                )}
              </h2>
              <p className="text-xs text-slate-400">
                Configure company batch size, target geography, and execute real-time verification.
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

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Configuration Form (Only enabled when not currently running) */}
          <div className={`space-y-5 ${isRunning ? "opacity-60 pointer-events-none" : ""}`}>
            {/* Mode Selector */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Discovery Mode
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setMode("discovery")}
                  className={`flex flex-col text-left p-3.5 rounded-xl border transition-all ${
                    mode === "discovery"
                      ? "border-indigo-500 bg-indigo-500/15 text-white shadow-sm shadow-indigo-500/20"
                      : "border-slate-800 bg-slate-950/50 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                  }`}
                >
                  <div className="flex items-center gap-2 font-semibold text-sm">
                    <Globe className="h-4 w-4 text-indigo-400" />
                    <span>Live FMCSA Discovery</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-400">
                    Queries active US small companies from registry, resolves official domains, and scrapes verified emails.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setMode("test_batch")}
                  className={`flex flex-col text-left p-3.5 rounded-xl border transition-all ${
                    mode === "test_batch"
                      ? "border-purple-500 bg-purple-500/15 text-white shadow-sm shadow-purple-500/20"
                      : "border-slate-800 bg-slate-950/50 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                  }`}
                >
                  <div className="flex items-center gap-2 font-semibold text-sm">
                    <Sparkles className="h-4 w-4 text-purple-400" />
                    <span>Curated Test Benchmark</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-400">
                    Fast automated test suite across benchmark companies for instant verification benchmarking.
                  </p>
                </button>
              </div>
            </div>

            {/* Company Count Selector */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Number of Companies to Find & Verify
                </label>
                <span className="text-sm font-bold text-indigo-400 bg-indigo-500/15 px-2.5 py-0.5 rounded-lg border border-indigo-500/30">
                  {count} Companies
                </span>
              </div>

              {/* Slider */}
              <input
                type="range"
                min="2"
                max="80"
                step="1"
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
                className="w-full accent-indigo-500 bg-slate-800 rounded-lg cursor-pointer h-2"
              />

              {/* Quick Presets */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3">
                {PRESET_COUNTS.map((preset) => (
                  <button
                    key={preset.value}
                    type="button"
                    onClick={() => setCount(preset.value)}
                    className={`rounded-lg px-3 py-2 text-xs font-medium border transition-all text-center ${
                      count === preset.value
                        ? "border-indigo-500 bg-indigo-600/25 text-indigo-200 font-semibold"
                        : "border-slate-800 bg-slate-950/40 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                    }`}
                  >
                    <div>{preset.label}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* US State Filter */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Filter by State (Optional)
              </label>
              <select
                value={selectedState}
                onChange={(e) => setSelectedState(e.target.value)}
                className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                {US_STATES.map((st) => (
                  <option key={st.code} value={st.code}>
                    {st.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Real-time Progress Bar & Live Status (Visible when running or completed) */}
          {(isRunning || isCompleted || isError) && (
            <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  {isRunning && <Loader2 className="h-4 w-4 animate-spin text-indigo-400" />}
                  {isCompleted && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
                  {isError && <AlertCircle className="h-4 w-4 text-red-400" />}
                  <span className="font-semibold text-slate-200">
                    {runState.current_step || "Processing..."}
                  </span>
                </div>
                <span className="font-mono text-slate-400">
                  {runState.processed_count} / {runState.requested_count} ({progressPercent}%) •{" "}
                  {runState.elapsed_seconds || 0}s
                </span>
              </div>

              {/* Progress bar */}
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-400 transition-all duration-300"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>

              {/* Progress Stats Pills */}
              <div className="flex flex-wrap items-center gap-3 pt-1 text-xs">
                <div className="flex items-center gap-1.5 rounded-lg bg-emerald-500/10 px-2.5 py-1 text-emerald-400 border border-emerald-500/20">
                  <span className="font-bold">{runState.verified_count || 0}</span> Verified Leads
                </div>
                <div className="flex items-center gap-1.5 rounded-lg bg-indigo-500/10 px-2.5 py-1 text-indigo-400 border border-indigo-500/20">
                  <span className="font-bold">{runState.full_lead_count || 0}</span> Full Leads (Web + Contact)
                </div>
                {runState.current_company && (
                  <div className="text-slate-400 truncate max-w-xs">
                    Current: <span className="text-slate-200">{runState.current_company}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Live Terminal Logs Window */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <Terminal className="h-4 w-4 text-indigo-400" />
                Pipeline Execution Logs
              </label>
              <span className="text-[11px] text-slate-500 font-mono">
                {runState.logs.length} events logged
              </span>
            </div>

            <div className="terminal-window rounded-xl p-3 h-48 overflow-y-auto text-xs leading-relaxed text-slate-300 space-y-1">
              {runState.logs.length === 0 ? (
                <div className="flex h-full items-center justify-center text-slate-600 italic">
                  Pipeline logs will appear here in real-time when execution starts...
                </div>
              ) : (
                runState.logs.map((log, idx) => {
                  let colorClass = "text-slate-300";
                  if (log.includes("[FULL LEAD]")) colorClass = "text-emerald-400 font-semibold";
                  else if (log.includes("[WEBSITE ONLY]")) colorClass = "text-sky-400";
                  else if (log.includes("[NEEDS REVIEW]")) colorClass = "text-amber-400";
                  else if (log.includes("[UNRESOLVED]")) colorClass = "text-slate-500";
                  else if (log.includes("[ERROR]") || log.includes("FATAL")) colorClass = "text-red-400 font-bold";
                  else if (log.includes("[Step")) colorClass = "text-indigo-400 font-semibold";

                  return (
                    <div key={idx} className={`font-mono text-[11px] ${colorClass}`}>
                      {log}
                    </div>
                  );
                })
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>

        {/* Modal Footer Controls */}
        <div className="flex items-center justify-between border-t border-slate-800 bg-slate-950/80 px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-slate-800 px-4 py-2 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            {isRunning ? "Hide (Runs in Background)" : "Close"}
          </button>

          <div className="flex items-center gap-3">
            {isRunning ? (
              <button
                type="button"
                onClick={handleCancelRun}
                className="flex items-center gap-2 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-2 text-xs font-semibold text-red-400 hover:bg-red-500/20 transition-colors"
              >
                <StopCircle className="h-4 w-4" />
                <span>Stop Pipeline</span>
              </button>
            ) : isCompleted ? (
              <button
                type="button"
                onClick={() => {
                  setRunState((prev) => ({ ...prev, status: "idle" }));
                }}
                className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 transition-all"
              >
                <RotateCcw className="h-4 w-4" />
                <span>Run Another Batch</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={handleStartRun}
                disabled={isSubmitting}
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 px-6 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Starting Engine...</span>
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 fill-current" />
                    <span>Start Run ({count} Companies)</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
