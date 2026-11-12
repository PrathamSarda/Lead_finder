import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Download,
  FileSpreadsheet,
  Globe,
  Loader2,
  Play,
  RotateCcw,
  Sparkles,
  StopCircle,
  Terminal,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import { leadsApi } from "../../api/leads";

const TARGET_REGIONS = [
  { code: "US", name: "United States (US)", flag: "🇺🇸", desc: "US FMCSA & Google Maps" },
  { code: "UK", name: "United Kingdom (UK)", flag: "🇬🇧", desc: "UK Companies & Indeed.co.uk" },
  { code: "AU", name: "Australia (AU)", flag: "🇦🇺", desc: "Australian SMBs & au.Indeed.com" },
  { code: "CA", name: "Canada (CA)", flag: "🇨🇦", desc: "Canadian SMBs & ca.Indeed.com" },
];

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
  const [city, setCity] = useState("");
  const [selectedRegions, setSelectedRegions] = useState(["US"]);
  const [showRegionOptions, setShowRegionOptions] = useState(false);
  const [afterDate, setAfterDate] = useState("");
  const [mode, setMode] = useState("bookkeeping");
  const [niche, setNiche] = useState("bookkeeping, accounting, tax preparation, payroll, or scaling support");
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

  const terminalLogsContainerRef = useRef(null);
  const modalBodyRef = useRef(null);

  // Keep modal scroll position pinned at top whenever modal opens
  useEffect(() => {
    if (isOpen && modalBodyRef.current) {
      modalBodyRef.current.scrollTop = 0;
    }
  }, [isOpen]);

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

  // Auto-scroll ONLY inside the internal terminal logs window (never scroll parent modal or page)
  useEffect(() => {
    const el = terminalLogsContainerRef.current;
    if (!el) return;
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 70;
    if (isNearBottom) {
      el.scrollTop = el.scrollHeight;
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
      const regionParam = selectedRegions.length > 0 ? selectedRegions.join(",") : "US";
      await leadsApi.triggerRun({
        count: Number(count),
        state: selectedState || null,
        city: city.trim() || null,
        mode,
        niche,
        region: regionParam,
        after_date: afterDate || null,
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

  const toggleRegion = (code) => {
    setSelectedRegions((prev) => {
      if (prev.includes(code)) {
        const next = prev.filter((c) => c !== code);
        return next.length > 0 ? next : ["US"];
      } else {
        return [...prev, code];
      }
    });
  };

  const handleCancelRun = async () => {
    try {
      await leadsApi.cancelRun();
      setRunState((prev) => ({
        ...prev,
        status: "idle",
        current_step: "Stopped by user",
      }));
    } catch (err) {
      console.error("Cancel failed:", err);
    }
  };

  const handleClearLogs = async () => {
    try {
      await leadsApi.clearLogs();
      setRunState((prev) => ({
        ...prev,
        logs: [],
        current_step: prev.status === "running" ? prev.current_step : "Idle",
      }));
    } catch (err) {
      console.error("Failed to clear logs:", err);
      // Fallback: clear local logs state
      setRunState((prev) => ({ ...prev, logs: [] }));
    }
  };

  const handleClose = () => {
    if (onClose) {
      onClose();
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
            onClick={handleClose}
            type="button"
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
            title="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div ref={modalBodyRef} className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Configuration Form (Only enabled when not currently running) */}
          <div className={`space-y-5 ${isRunning ? "opacity-60 pointer-events-none" : ""}`}>
              {/* Active end-to-end workflow */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Workflow
              </label>
              <div className="grid grid-cols-1 gap-3">
                <button
                  type="button"
                  onClick={() => setMode("bookkeeping")}
                  className={`flex flex-col text-left p-3.5 rounded-xl border transition-all ${
                    mode === "bookkeeping"
                      ? "border-emerald-500 bg-emerald-500/15 text-white shadow-sm shadow-emerald-500/20"
                      : "border-slate-800 bg-slate-950/50 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                  }`}
                >
                  <div className="flex items-center gap-2 font-semibold text-sm">
                    <Sparkles className="h-4 w-4 text-emerald-400" />
                    <span>Hiring Intent Fast Mode: Companies Needing Bookkeeping Services</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-400">
                    Directly scans public Indeed & LinkedIn job postings for companies actively hiring bookkeepers, accountants, and QuickBooks specialists. Filters for 10–15 headcount and extracts verified corporate & decision-maker emails.
                  </p>
                </button>
              </div>
            </div>

            {/* Target Region / Country Expansion (Default: US) */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Target Region / Country
                </label>
                <button
                  type="button"
                  onClick={() => setShowRegionOptions((prev) => !prev)}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  <Globe className="h-3.5 w-3.5" />
                  <span>{showRegionOptions ? "Hide Country Options" : "Change Region / Expand"}</span>
                  <ChevronDown className={`h-3 w-3 transition-transform ${showRegionOptions ? "rotate-180" : ""}`} />
                </button>
              </div>

              {/* Default Region View (Clean, non-distracting) */}
              {!showRegionOptions ? (
                <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-slate-700 transition-all">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5">
                      {selectedRegions.map((code) => {
                        const reg = TARGET_REGIONS.find((r) => r.code === code) || { flag: "🇺🇸", name: code };
                        return (
                          <span
                            key={code}
                            className="inline-flex items-center gap-1.5 text-xs bg-slate-900 px-2.5 py-1 rounded-lg border border-slate-700/80 font-bold text-slate-100 shadow-sm"
                          >
                            <span className="text-base">{reg.flag}</span>
                            <span>{code}</span>
                          </span>
                        );
                      })}
                    </div>
                    <div className="text-xs">
                      {selectedRegions.length === 1 && selectedRegions[0] === "US" ? (
                        <div className="text-slate-300">
                          <span className="text-emerald-400 font-semibold mr-1.5">Default Region:</span>
                          <span>United States (FMCSA & Google Maps)</span>
                        </div>
                      ) : (
                        <div className="text-slate-300">
                          <span className="text-indigo-400 font-semibold mr-1.5">Custom Regions:</span>
                          <span>Targeting {selectedRegions.join(", ")}</span>
                        </div>
                      )}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowRegionOptions(true)}
                    className="rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition-colors"
                  >
                    Change
                  </button>
                </div>
              ) : (
                /* Expanded Region Selector (Allows Client to select which all regions they want) */
                <div className="space-y-3 rounded-xl border border-indigo-500/40 bg-slate-950/80 p-3.5 animate-in fade-in duration-150">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 font-medium">
                      Select which all regions you want to search:
                    </span>
                    {!(selectedRegions.length === 1 && selectedRegions[0] === "US") && (
                      <button
                        type="button"
                        onClick={() => setSelectedRegions(["US"])}
                        className="text-[11px] font-semibold text-amber-400 hover:text-amber-300 underline"
                      >
                        Reset to US (Default)
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {TARGET_REGIONS.map((r) => {
                      const isSelected = selectedRegions.includes(r.code);
                      return (
                        <button
                          key={r.code}
                          type="button"
                          onClick={() => toggleRegion(r.code)}
                          className={`flex flex-col items-start p-2.5 rounded-xl border transition-all text-left ${
                            isSelected
                              ? "border-indigo-500 bg-indigo-500/20 text-white shadow-sm shadow-indigo-500/20"
                              : "border-slate-800 bg-slate-900/40 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                          }`}
                        >
                          <div className="flex items-center justify-between w-full">
                            <span className="text-lg">{r.flag}</span>
                            {isSelected ? (
                              <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/20 px-1.5 py-0.5 rounded border border-emerald-500/30">
                                Active
                              </span>
                            ) : (
                              <span className="text-[10px] text-slate-500">+ Select</span>
                            )}
                          </div>
                          <span className="text-xs font-bold mt-1 text-slate-100">{r.name}</span>
                          <span className="text-[10px] text-slate-400 leading-tight mt-0.5">{r.desc}</span>
                        </button>
                      );
                    })}
                  </div>

                  <div className="flex items-center justify-between pt-1 border-t border-slate-800/80 text-[11px] text-slate-400">
                    <span>
                      Active: <strong className="text-slate-200">{selectedRegions.join(", ")}</strong>
                    </span>
                    <button
                      type="button"
                      onClick={() => setShowRegionOptions(false)}
                      className="text-xs font-semibold text-indigo-400 hover:text-indigo-300"
                    >
                      Done Selecting
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Date Option: Services Needed After Date */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Services Needed On / After Date (LinkedIn & Indeed)
                </label>
                {afterDate && (
                  <span className="text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    After {afterDate}
                  </span>
                )}
              </div>
              <div className="flex flex-col sm:flex-row gap-2">
                <input
                  type="date"
                  value={afterDate}
                  onChange={(e) => setAfterDate(e.target.value)}
                  className="rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-sm text-slate-200 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 flex-1"
                />
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => setAfterDate("")}
                    className={`rounded-lg px-2.5 py-2 text-xs font-medium border transition-all ${
                      !afterDate
                        ? "border-emerald-500 bg-emerald-500/20 text-emerald-300 font-semibold"
                        : "border-slate-800 bg-slate-950/40 text-slate-400 hover:bg-slate-800"
                    }`}
                  >
                    Any (Last 90d)
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const d = new Date();
                      d.setDate(d.getDate() - 30);
                      setAfterDate(d.toISOString().slice(0, 10));
                    }}
                    className="rounded-lg px-2.5 py-2 text-xs font-medium border border-slate-800 bg-slate-950/40 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-all"
                  >
                    Last 30 Days
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const d = new Date();
                      d.setDate(d.getDate() - 60);
                      setAfterDate(d.toISOString().slice(0, 10));
                    }}
                    className="rounded-lg px-2.5 py-2 text-xs font-medium border border-slate-800 bg-slate-950/40 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-all"
                  >
                    Last 60 Days
                  </button>
                </div>
              </div>
              <p className="mt-1.5 text-[11px] text-slate-400">
                Only confirms companies if their LinkedIn posts or Indeed job ads indicate bookkeeping services needed on or after this date.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Target niche / buying intent</label>
              <input value={niche} onChange={(event) => setNiche(event.target.value)} maxLength={200} className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" placeholder="Bookkeeping, payroll, tax prep, or scaling support" />
            </div>

            {/* Company Count Selector */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Qualified Leads Target
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
                Filter by City (Optional)
              </label>
              <input
                value={city}
                onChange={(e) => setCity(e.target.value)}
                maxLength={100}
                placeholder="Austin"
                className="mb-3 w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
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
              <div className="flex items-center gap-2">
                {runState.logs.length > 0 && (
                  <button
                    type="button"
                    onClick={handleClearLogs}
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800/80 px-2 py-0.5 text-[11px] font-semibold text-slate-300 hover:border-red-500/40 hover:bg-red-500/10 hover:text-red-400 transition-colors"
                    title="Clear terminal logs"
                  >
                    <Trash2 className="h-3 w-3" />
                    <span>Clear Logs</span>
                  </button>
                )}
                <span className="text-[11px] text-slate-500 font-mono">
                  {runState.logs.length} events logged
                </span>
              </div>
            </div>

            <div
              ref={terminalLogsContainerRef}
              className="terminal-window rounded-xl p-3 h-48 overflow-y-auto text-xs leading-relaxed text-slate-300 space-y-1"
            >
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
            </div>
          </div>
        </div>

        {/* Modal Footer Controls */}
        <div className="flex items-center justify-between border-t border-slate-800 bg-slate-950/80 px-6 py-4">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleClose}
              className="rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition-colors"
            >
              {isRunning ? "Hide (Runs in Background)" : "Close"}
            </button>
            {runState.logs.length > 0 && (
              <button
                type="button"
                onClick={handleClearLogs}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 px-3 py-2 text-xs font-medium text-slate-400 hover:border-slate-700 hover:bg-slate-800/50 hover:text-slate-300 transition-colors"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>Clear Logs</span>
              </button>
            )}
          </div>

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
