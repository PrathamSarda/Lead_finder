import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Briefcase,
  Building2,
  Check,
  CheckCircle2,
  ChevronDown,
  Clock,
  Compass,
  Copy,
  Download,
  ExternalLink,
  Eye,
  FileSpreadsheet,
  Filter,
  Globe,
  HelpCircle,
  History,
  Layers,
  Loader2,
  Mail,
  MapPin,
  Phone,
  Play,
  RotateCcw,
  Search,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";
import { leadsApi } from "../api/leads";
import RunModal from "../components/pipeline/RunModal";
import LeadDrawer from "../components/leads/LeadDrawer";

function LinkedInIcon({ className = "h-3.5 w-3.5" }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z" />
    </svg>
  );
}

export default function Dashboard() {
  // State for leads & runs
  const [leads, setLeads] = useState([]);
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState("latest");
  const [summary, setSummary] = useState({
    total_leads: 0,
    filtered_leads: 0,
    verified_count: 0,
    full_lead_count: 0,
    website_only_count: 0,
    needs_review_count: 0,
    unresolved_count: 0,
    emails_count: 0,
    phones_count: 0,
    avg_confidence: 0,
    verification_rate: 0,
    full_lead_rate: 0,
  });

  const [isLoading, setIsLoading] = useState(true);
  const [activeRunState, setActiveRunState] = useState(null);

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [tierFilter, setTierFilter] = useState("ALL");
  const [intentSourceFilter, setIntentSourceFilter] = useState("ALL");
  const [regionFilter, setRegionFilter] = useState("ALL");
  const [emailFilter, setEmailFilter] = useState("ALL");
  const [onlyWithLinkedIn, setOnlyWithLinkedIn] = useState(false);
  const [onlyWithPhone, setOnlyWithPhone] = useState(false);
  const [onlyHighConfidence, setOnlyHighConfidence] = useState(false);
  const [stateFilter, setStateFilter] = useState("ALL");

  // Selection
  const [selectedLeadIds, setSelectedLeadIds] = useState(new Set());
  const [inspectedLead, setInspectedLead] = useState(null);

  // Modals
  const [isRunModalOpen, setIsRunModalOpen] = useState(false);

  // Feedback notifications
  const [toastMessage, setToastMessage] = useState(null);

  const showNotification = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleCopyEmail = (emailStr) => {
    if (!emailStr) return;
    navigator.clipboard.writeText(emailStr);
    showNotification(`Copied to clipboard: ${emailStr}`);
  };

  // 1. Fetch available runs
  const fetchRuns = async () => {
    try {
      const data = await leadsApi.getRuns();
      setRuns(data.runs || []);
    } catch (err) {
      console.error("Error fetching runs:", err);
    }
  };

  // 2. Fetch leads based on active run & filters
  const fetchLeads = async () => {
    setIsLoading(true);
    try {
      const params = {
        run_id: selectedRunId,
        tier: tierFilter !== "ALL" ? tierFilter : undefined,
        query: searchQuery || undefined,
        state: stateFilter !== "ALL" ? stateFilter : undefined,
        has_linkedin: onlyWithLinkedIn ? true : undefined,
        has_phone: onlyWithPhone ? true : undefined,
        min_confidence: onlyHighConfidence ? 0.9 : undefined,
        limit: 500,
      };

      const data = await leadsApi.getLeads(params);
      setLeads(data.items || []);
      if (data.summary) {
        setSummary(data.summary);
      }
    } catch (err) {
      console.error("Error fetching leads:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // Check active pipeline background status
  const checkActiveRun = async () => {
    try {
      const status = await leadsApi.getRunStatus();
      setActiveRunState(status);
      if (status.status === "completed" && activeRunState?.status === "running") {
        fetchRuns();
        fetchLeads();
      }
    } catch (err) {
      console.error("Error polling run status:", err);
    }
  };

  useEffect(() => {
    fetchRuns();
    const interval = setInterval(checkActiveRun, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    fetchLeads();
  }, [
    selectedRunId,
    tierFilter,
    searchQuery,
    stateFilter,
    onlyWithLinkedIn,
    onlyWithPhone,
    onlyHighConfidence,
  ]);

  // Compute displayed leads based on local filters (e.g. source, region, email presence)
  const displayedLeads = useMemo(() => {
    return leads.filter((l) => {
      if (intentSourceFilter === "LINKEDIN") {
        const matchesLi =
          (l.intent_source || "").toLowerCase().includes("linkedin") ||
          (l.intent_status || "").toLowerCase().includes("linkedin") ||
          l.has_recent_linkedin_post;
        if (!matchesLi) return false;
      } else if (intentSourceFilter === "INDEED") {
        const matchesIndeed =
          (l.intent_source || "").toLowerCase().includes("indeed") ||
          (l.intent_status || "").toLowerCase().includes("indeed");
        if (!matchesIndeed) return false;
      }

      if (regionFilter !== "ALL") {
        const leadReg = (l.region || "US").toUpperCase();
        if (leadReg !== regionFilter.toUpperCase()) return false;
      }

      if (emailFilter === "BOTH" && (!l.company_email || !l.decision_maker_email)) {
        return false;
      }
      if (emailFilter === "COMPANY" && !l.company_email) {
        return false;
      }

      return true;
    });
  }, [leads, intentSourceFilter, regionFilter, emailFilter]);

  // Selection helpers
  const handleToggleSelectAll = () => {
    if (selectedLeadIds.size === displayedLeads.length) {
      setSelectedLeadIds(new Set());
    } else {
      const allKeys = new Set(displayedLeads.map((l) => l.company_name));
      setSelectedLeadIds(allKeys);
    }
  };

  const handleToggleSelectLead = (companyName) => {
    setSelectedLeadIds((prev) => {
      const next = new Set(prev);
      if (next.has(companyName)) next.delete(companyName);
      else next.add(companyName);
      return next;
    });
  };

  // Export handlers
  const handleExportExcel = () => {
    try {
      const targetLeads =
        selectedLeadIds.size > 0
          ? displayedLeads.filter((l) => selectedLeadIds.has(l.company_name))
          : displayedLeads;

      leadsApi.exportToExcelClient(targetLeads, null, summary);
      showNotification(`Exported ${targetLeads.length} leads to Excel (.xlsx)`);
    } catch (err) {
      alert(err.message);
    }
  };

  const handleExportCsv = () => {
    try {
      window.location.href = leadsApi.getBackendCsvUrl({
        run_id: selectedRunId,
        tier: tierFilter !== "ALL" ? tierFilter : undefined,
        query: searchQuery || undefined,
      });
      showNotification("CSV export initiated");
    } catch (err) {
      alert("Failed to export CSV");
    }
  };

  // Unique states present in data
  const availableStates = useMemo(() => {
    const states = new Set();
    leads.forEach((l) => {
      if (l.location && l.location.includes(",")) {
        const part = l.location.split(",")[1]?.trim();
        if (part && part.length === 2) states.add(part.toUpperCase());
      }
    });
    return Array.from(states).sort();
  }, [leads]);

  return (
    <div className="space-y-6 pb-20">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-2xl shadow-indigo-600/40 animate-in slide-in-from-bottom-5">
          <CheckCircle2 className="h-4 w-4" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Hero Banner & Controls */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="flex items-center gap-1.5 rounded-full bg-indigo-500/15 px-3 py-1 text-xs font-bold text-indigo-400 border border-indigo-500/20">
              <Sparkles className="h-3.5 w-3.5" /> B2B Intelligence Portal
            </span>
            <span className="text-xs text-slate-400">• Prokizen Global LLP</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            Bookkeeping Leads &amp; Decision Maker Discovery
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-slate-400 max-w-2xl">
            Targeting US companies with 10–15 employees needing bookkeeping services, verified via company LinkedIn activity or Indeed job postings, with verified decision-maker emails.
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Run Pipeline */}
          <button
            onClick={() => setIsRunModalOpen(true)}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 via-indigo-600 to-purple-600 px-5 py-2.5 text-xs sm:text-sm font-bold text-white shadow-lg shadow-indigo-600/30 hover:scale-[1.02] active:scale-[0.98] transition-all"
          >
            <Play className="h-4 w-4 fill-current text-emerald-300" />
            <span>Run Pipeline</span>
          </button>

          {/* Excel Export */}
          <button
            onClick={handleExportExcel}
            className="flex items-center gap-2 rounded-xl border border-emerald-500/40 bg-emerald-500/15 px-4 py-2.5 text-xs sm:text-sm font-bold text-emerald-300 hover:bg-emerald-500/25 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <FileSpreadsheet className="h-4 w-4 text-emerald-400" />
            <span>Download Excel (.xlsx)</span>
          </button>

          {/* CSV Export */}
          <button
            onClick={handleExportCsv}
            title="Download CSV"
            className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900 p-2.5 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <Download className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Active Running Pipeline Banner */}
      {activeRunState && activeRunState.status === "running" && (
        <div className="rounded-2xl border border-indigo-500/40 bg-indigo-950/40 p-4 backdrop-blur-xl shadow-lg shadow-indigo-500/10 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-400 animate-spin">
                <Loader2 className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm text-white">
                    {activeRunState.current_step || "Pipeline running..."}
                  </span>
                  <span className="rounded bg-indigo-500/20 px-2 py-0.5 text-[10px] font-semibold text-indigo-300">
                    Live Execution
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Target: {activeRunState.requested_count} companies • Mode:{" "}
                  {activeRunState.mode?.toUpperCase()} • {activeRunState.elapsed_seconds || 0}s elapsed
                </p>
              </div>
            </div>
            <button
              onClick={() => setIsRunModalOpen(true)}
              className="rounded-xl border border-indigo-500/40 bg-indigo-500/20 px-3.5 py-1.5 text-xs font-semibold text-indigo-200 hover:bg-indigo-500/30 transition-colors"
            >
              View Terminal Logs
            </button>
          </div>

          {/* Progress bar */}
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-300"
              style={{
                width: `${Math.min(
                  100,
                  Math.round(
                    (activeRunState.processed_count / (activeRunState.requested_count || 1)) * 100
                  )
                )}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* Executive KPI Stats Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {/* Card 1: Total Leads */}
        <div className="glass-card rounded-2xl p-4 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Discovered</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400">
              <Building2 className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-white">{summary.total_leads}</div>
          <div className="mt-1 flex items-center gap-1.5 text-[11px] text-slate-400">
            <span className="font-semibold text-indigo-400">{summary.filtered_leads}</span> matching filters
          </div>
        </div>

        {/* Card 2: Intent-Verified Leads */}
        <div className="glass-card rounded-2xl p-4 transition-all border-emerald-500/20 bg-emerald-950/10">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
              Verified Intent Leads
            </span>
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
              <Sparkles className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-emerald-300">{summary.verified_count || summary.full_lead_count}</div>
          <div className="mt-1 flex items-center gap-1.5 text-[11px] text-emerald-400">
            <span className="font-bold">{summary.full_lead_rate}%</span> of total batch
          </div>
        </div>

        {/* Card 3: Websites Verified */}
        <div className="glass-card rounded-2xl p-4 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Websites Resolved</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-sky-500/10 text-sky-400">
              <Globe className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-sky-300">
            {summary.full_lead_count + summary.website_only_count}
          </div>
          <div className="mt-1 flex items-center gap-1.5 text-[11px] text-slate-400">
            <span className="font-semibold text-sky-400">{summary.verification_rate}%</span> website verified
          </div>
        </div>

        {/* Card 4: LinkedIn Profiles Found */}
        <div className="glass-card rounded-2xl p-4 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">LinkedIn Profiles</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-purple-500/10 text-purple-400">
              <LinkedInIcon className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-purple-300">{leads.filter(l => l.company_linkedin_url || l.decision_maker_linkedin_url).length}</div>
          <div className="mt-1 flex items-center gap-1.5 text-[11px] text-slate-400">
            <span>Company &amp; Executive URLs</span>
          </div>
        </div>

        {/* Card 5: Quality Confidence Score */}
        <div className="glass-card rounded-2xl p-4 transition-all col-span-2 sm:col-span-1">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Avg Quality Score</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/10 text-amber-400">
              <ShieldCheck className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-amber-300">
            {(summary.avg_confidence * 100).toFixed(0)}%
          </div>
          <div className="mt-1 flex items-center gap-1.5 text-[11px] text-slate-400">
            <span>Strict Verification Layer</span>
          </div>
        </div>
      </div>

      {/* Dataset & Run Selector Bar */}
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/90 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            <History className="h-4 w-4 text-indigo-400" />
            <span>Select Run Dataset:</span>
          </div>

          <div className="relative">
            <select
              value={selectedRunId}
              onChange={(e) => setSelectedRunId(e.target.value)}
              className="appearance-none rounded-xl border border-slate-700 bg-slate-950 py-2 pl-3.5 pr-8 text-xs sm:text-sm font-semibold text-slate-200 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="latest">Latest Discovery Run (Most Recent)</option>
              <option value="all">All Combined Finds (De-duplicated Across Runs)</option>
              <optgroup label="Archived Discovery Runs">
                {runs.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.filename} ({r.total_leads} leads • {r.full_leads} full • {r.modified_at?.slice(0, 16)})
                  </option>
                ))}
              </optgroup>
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-3 h-3.5 w-3.5 text-slate-400" />
          </div>

          <button
            onClick={() => {
              fetchRuns();
              fetchLeads();
              showNotification("Refreshed latest data");
            }}
            title="Refresh leads and runs"
            className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        {/* Total Runs Count Badge */}
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span>{runs.length} historical run archives</span>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          {/* Search Box */}
          <div className="relative flex-1 max-w-lg">
            <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search company name, domain, location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl border border-slate-800 bg-slate-950/90 pl-10 pr-4 py-2 text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-2.5 text-xs text-slate-500 hover:text-white"
              >
                Clear
              </button>
            )}
          </div>

          {/* Filter Pills & Toggles */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Region Filter Buttons */}
            <div className="flex items-center rounded-xl border border-slate-800 bg-slate-950 p-0.5">
              <button
                type="button"
                onClick={() => setRegionFilter("ALL")}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                  regionFilter === "ALL"
                    ? "bg-slate-800 text-white font-semibold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                All Regions
              </button>
              <button
                type="button"
                onClick={() => setRegionFilter("US")}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                  regionFilter === "US"
                    ? "bg-indigo-500/20 text-indigo-300 font-semibold border border-indigo-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                🇺🇸 US
              </button>
              <button
                type="button"
                onClick={() => setRegionFilter("UK")}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                  regionFilter === "UK"
                    ? "bg-indigo-500/20 text-indigo-300 font-semibold border border-indigo-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                🇬🇧 UK
              </button>
              <button
                type="button"
                onClick={() => setRegionFilter("AU")}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                  regionFilter === "AU"
                    ? "bg-indigo-500/20 text-indigo-300 font-semibold border border-indigo-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                🇦🇺 AU
              </button>
              <button
                type="button"
                onClick={() => setRegionFilter("CA")}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                  regionFilter === "CA"
                    ? "bg-indigo-500/20 text-indigo-300 font-semibold border border-indigo-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                🇨🇦 CA
              </button>
            </div>

            {/* Email Coverage Filter */}
            <div className="flex items-center rounded-xl border border-slate-800 bg-slate-950 p-0.5">
              <button
                type="button"
                onClick={() => setEmailFilter("ALL")}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                  emailFilter === "ALL"
                    ? "bg-slate-800 text-white font-semibold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                All Emails
              </button>
              <button
                type="button"
                onClick={() => setEmailFilter("COMPANY")}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                  emailFilter === "COMPANY"
                    ? "bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Company Email Verified
              </button>
              <button
                type="button"
                onClick={() => setEmailFilter("BOTH")}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                  emailFilter === "BOTH"
                    ? "bg-indigo-500/20 text-indigo-300 font-semibold border border-indigo-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Both Emails Present
              </button>
            </div>

            {/* Intent Source Filter Buttons */}
            <div className="flex items-center rounded-xl border border-slate-800 bg-slate-950 p-0.5">
              <button
                type="button"
                onClick={() => setIntentSourceFilter("ALL")}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                  intentSourceFilter === "ALL"
                    ? "bg-slate-800 text-white font-semibold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                All Sources
              </button>
              <button
                type="button"
                onClick={() => setIntentSourceFilter("LINKEDIN")}
                className={`flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                  intentSourceFilter === "LINKEDIN"
                    ? "bg-sky-500/20 text-sky-300 font-semibold border border-sky-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <LinkedInIcon className="h-3 w-3 text-sky-400" />
                <span>LinkedIn</span>
              </button>
              <button
                type="button"
                onClick={() => setIntentSourceFilter("INDEED")}
                className={`flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                  intentSourceFilter === "INDEED"
                    ? "bg-purple-500/20 text-purple-300 font-semibold border border-purple-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Briefcase className="h-3 w-3 text-purple-400" />
                <span>Indeed</span>
              </button>
            </div>

            {/* Has Decision Maker Profile Toggle */}
            <button
              onClick={() => setOnlyWithLinkedIn(!onlyWithLinkedIn)}
              className={`flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-medium transition-colors ${
                onlyWithLinkedIn
                  ? "border-indigo-500 bg-indigo-500/20 text-indigo-300 font-semibold"
                  : "border-slate-800 bg-slate-950 text-slate-400 hover:text-slate-200"
              }`}
            >
              <LinkedInIcon className="h-3.5 w-3.5" />
              <span>Has LinkedIn Profile</span>
            </button>

            {/* State filter dropdown */}
            {availableStates.length > 0 && (
              <select
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
                className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-300 focus:border-indigo-500 focus:outline-none"
              >
                <option value="ALL">All States</option>
                {availableStates.map((st) => (
                  <option key={st} value={st}>
                    State: {st}
                  </option>
                ))}
              </select>
            )}

            {/* Reset all filters */}
            {(searchQuery ||
              onlyWithLinkedIn ||
              intentSourceFilter !== "ALL" ||
              regionFilter !== "ALL" ||
              emailFilter !== "ALL" ||
              stateFilter !== "ALL") && (
              <button
                onClick={() => {
                  setSearchQuery("");
                  setOnlyWithLinkedIn(false);
                  setIntentSourceFilter("ALL");
                  setRegionFilter("ALL");
                  setEmailFilter("ALL");
                  setStateFilter("ALL");
                }}
                className="text-xs text-indigo-400 hover:underline px-2"
              >
                Reset
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Floating Selection Batch Toolbar (When items are selected) */}
      {selectedLeadIds.size > 0 && (
        <div className="flex items-center justify-between rounded-xl border border-indigo-500/40 bg-indigo-950/80 p-3.5 backdrop-blur-xl animate-in fade-in">
          <div className="flex items-center gap-3">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500 text-xs font-bold text-white">
              {selectedLeadIds.size}
            </span>
            <span className="text-xs sm:text-sm font-semibold text-white">
              Companies Selected
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleExportExcel}
              className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow hover:bg-emerald-500 transition-colors"
            >
              <FileSpreadsheet className="h-3.5 w-3.5" />
              <span>Export {selectedLeadIds.size} to Excel</span>
            </button>

            <button
              onClick={() => setSelectedLeadIds(new Set())}
              className="text-xs text-slate-400 hover:text-white px-2"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Main Finds Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl backdrop-blur-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            {/* Table Header */}
            <thead className="border-b border-slate-800 bg-slate-950/80 text-[11px] font-bold uppercase tracking-wider text-slate-400">
              <tr>
                <th className="py-3.5 pl-4 pr-2 w-10">
                  <input
                    type="checkbox"
                    checked={displayedLeads.length > 0 && selectedLeadIds.size === displayedLeads.length}
                    onChange={handleToggleSelectAll}
                    className="rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-0 cursor-pointer"
                  />
                </th>
                <th className="py-3.5 px-3">Company &amp; Region</th>
                <th className="py-3.5 px-3">Employees</th>
                <th className="py-3.5 px-3">Website &amp; Phone</th>
                <th className="py-3.5 px-3">Bookkeeping Intent &amp; Source</th>
                <th className="py-3.5 px-3 text-emerald-400">Company Email (Min Req)</th>
                <th className="py-3.5 px-3">Decision Maker</th>
                <th className="py-3.5 px-3 text-indigo-400">Decision Maker Email</th>
                <th className="py-3.5 px-3">LinkedIn Profiles</th>
                <th className="py-3.5 pr-4 pl-3 text-right">Action</th>
              </tr>
            </thead>

            {/* Table Body */}
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={10} className="py-20 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center gap-3">
                      <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
                      <p className="font-medium text-slate-300">Loading discovered company leads...</p>
                    </div>
                  </td>
                </tr>
              ) : displayedLeads.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-20 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center gap-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-800/60 text-slate-500">
                        <Building2 className="h-6 w-6" />
                      </div>
                      <p className="font-semibold text-slate-200 text-sm">No companies match this filter</p>
                      <p className="text-xs text-slate-500 max-w-sm">
                        Try clearing active search queries or click "Run Discovery Pipeline" to find fresh leads.
                      </p>
                      <button
                        onClick={() => setIsRunModalOpen(true)}
                        className="mt-2 flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow hover:bg-indigo-500 transition-colors"
                      >
                        <Play className="h-3.5 w-3.5 fill-current" />
                        <span>Run Discovery Pipeline</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                displayedLeads.map((lead, idx) => {
                  const isSelected = selectedLeadIds.has(lead.company_name);
                  const companyLi = lead.company_linkedin_url || lead.linkedin;
                  const dmLarge = lead.decision_maker_linkedin_url;
                  const dmName = lead.decision_maker_name || lead.owner_name;
                  const dmTitle = lead.decision_maker_title || lead.owner_title;
                  const compEmail = lead.company_email;
                  const dmEmail = lead.decision_maker_email || (lead.email !== compEmail ? lead.email : null);
                  const regCode = (lead.region || "US").toUpperCase();
                  const isIndeed = (lead.intent_source || "").toLowerCase().includes("indeed") || (lead.intent_status || "").toLowerCase().includes("indeed");
                  const isLinkedIn = (lead.intent_source || "").toLowerCase().includes("linkedin") || (lead.intent_status || "").toLowerCase().includes("linkedin");
                  const isConfirmed = lead.intent_status?.startsWith("CONFIRMED") || isIndeed || isLinkedIn;

                  return (
                    <tr
                      key={idx}
                      className={`group transition-colors hover:bg-slate-800/40 ${
                        isSelected ? "bg-indigo-950/20" : ""
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="py-3.5 pl-4 pr-2">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleToggleSelectLead(lead.company_name)}
                          className="rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-0 cursor-pointer"
                        />
                      </td>

                      {/* 1. Company Name & Region */}
                      <td className="py-3.5 px-3">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-100 group-hover:text-indigo-300 transition-colors">
                            {lead.company_name}
                          </span>
                          <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold bg-slate-800 text-indigo-300 border border-slate-700">
                            {regCode === "US" ? "🇺🇸 US" : regCode === "UK" ? "🇬🇧 UK" : regCode === "AU" ? "🇦🇺 AU" : regCode === "CA" ? "🇨🇦 CA" : regCode}
                          </span>
                        </div>
                        {lead.location && (
                          <div className="flex items-center gap-1.5 mt-0.5 text-[11px] text-slate-400">
                            <MapPin className="h-3 w-3 text-slate-500" />
                            <span>{lead.location}</span>
                          </div>
                        )}
                      </td>

                      {/* Employees (10-15) */}
                      <td className="py-3.5 px-3">
                        {lead.employee_count ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-slate-800 px-2.5 py-1 text-[11px] font-semibold text-slate-200 border border-slate-700">
                            <Users className="h-3 w-3 text-indigo-400" />
                            <span>{lead.employee_count}</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400 border border-emerald-500/20">
                            10–15
                          </span>
                        )}
                      </td>

                      {/* 2. Website & Phone */}
                      <td className="py-3.5 px-3">
                        <div className="flex flex-col gap-0.5">
                          {lead.website ? (
                            <a
                              href={lead.website.startsWith("http") ? lead.website : `https://${lead.website}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 font-semibold text-indigo-400 hover:text-indigo-300 hover:underline max-w-[190px] truncate"
                            >
                              <Globe className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
                              <span className="truncate">{lead.website.replace(/^https?:\/\//, "").replace(/\/$/, "")}</span>
                              <ExternalLink className="h-3 w-3 shrink-0 opacity-70" />
                            </a>
                          ) : (
                            <span className="text-slate-600 italic">—</span>
                          )}
                          {lead.phone && (
                            <span className="text-[11px] text-slate-400 font-mono">
                              {lead.phone}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* 3. Bookkeeping Intent & Source */}
                      <td className="py-3.5 px-3 min-w-[230px]">
                        <div className="flex flex-col gap-1">
                          {isIndeed ? (
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-purple-500/15 border border-purple-500/30 px-2.5 py-0.5 text-[10px] font-bold text-purple-300 w-fit">
                              <Briefcase className="h-3 w-3 text-purple-400" /> Confirmed via Indeed
                            </span>
                          ) : isLinkedIn ? (
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-500/15 border border-sky-500/30 px-2.5 py-0.5 text-[10px] font-bold text-sky-300 w-fit">
                              <LinkedInIcon className="h-3 w-3 text-sky-400" /> Confirmed via LinkedIn
                            </span>
                          ) : isConfirmed ? (
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2.5 py-0.5 text-[10px] font-bold text-emerald-300 w-fit">
                              <CheckCircle2 className="h-3 w-3 text-emerald-400" /> Confirmed
                            </span>
                          ) : (
                            <span className="inline-flex rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-bold text-slate-400 w-fit">
                              {lead.intent_status || "Not checked"}
                            </span>
                          )}
                          {lead.intent_reason && (
                            <span className="block max-w-xs text-[11px] text-slate-400 leading-tight">
                              {lead.intent_reason}
                            </span>
                          )}
                          {lead.indeed_job_url && (
                            <a
                              href={lead.indeed_job_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-[10px] font-semibold text-purple-400 hover:text-purple-300 hover:underline"
                            >
                              <span>View Indeed Job Posting</span>
                              <ExternalLink className="h-2.5 w-2.5" />
                            </a>
                          )}
                        </div>
                      </td>

                      {/* 4. Company Email (Required Minimum) */}
                      <td className="py-3.5 px-3 min-w-[210px]">
                        {compEmail ? (
                          <div className="flex flex-col gap-0.5">
                            <div className="flex items-center gap-1.5">
                              <Mail className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                              <a href={`mailto:${compEmail}`} className="font-semibold text-emerald-300 hover:underline truncate max-w-[160px]">
                                {compEmail}
                              </a>
                              <button
                                type="button"
                                onClick={() => handleCopyEmail(compEmail)}
                                title="Copy Company Email"
                                className="text-slate-400 hover:text-white p-0.5 transition-colors"
                              >
                                <Copy className="h-3 w-3" />
                              </button>
                            </div>
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-400">
                              <CheckCircle2 className="h-2.5 w-2.5" /> Company Email Verified
                            </span>
                          </div>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] text-amber-400/90 font-medium italic">
                            <AlertCircle className="h-3 w-3 text-amber-400" /> Pending / Missing
                          </span>
                        )}
                      </td>

                      {/* 5. Decision Maker Name & Title */}
                      <td className="py-3.5 px-3">
                        {dmName ? (
                          <div className="flex flex-col">
                            <div className="flex items-center gap-1.5 font-medium text-slate-200 truncate max-w-[170px]">
                              <Users className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
                              <span>{dmName}</span>
                            </div>
                            {dmTitle && (
                              <span className="text-[10px] text-slate-400 pl-5 truncate max-w-[170px]">
                                {dmTitle}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-500 italic text-[11px]">Not resolved</span>
                        )}
                      </td>

                      {/* 6. Decision Maker Email */}
                      <td className="py-3.5 px-3 min-w-[210px]">
                        {dmEmail ? (
                          <div className="flex flex-col gap-0.5">
                            <div className="flex items-center gap-1.5">
                              <Mail className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
                              <a href={`mailto:${dmEmail}`} className="font-semibold text-indigo-300 hover:underline truncate max-w-[160px]">
                                {dmEmail}
                              </a>
                              <button
                                type="button"
                                onClick={() => handleCopyEmail(dmEmail)}
                                title="Copy Decision Maker Email"
                                className="text-slate-400 hover:text-white p-0.5 transition-colors"
                              >
                                <Copy className="h-3 w-3" />
                              </button>
                            </div>
                            <span className={`text-[10px] font-bold ${lead.email_status === "VALID" ? "text-emerald-400" : "text-amber-400"}`}>
                              {lead.email_status === "VALID" ? "✓ Deliverable Decision Maker" : (lead.email_status || "Verified")}
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-500 italic text-[11px]">Pending / Not found</span>
                        )}
                      </td>

                      {/* 7. LinkedIn Profiles (Company & Decision Maker) */}
                      <td className="py-3.5 px-3">
                        <div className="flex flex-col gap-1">
                          {companyLi && (
                            <a
                              href={companyLi.startsWith("http") ? companyLi : `https://${companyLi}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300 hover:underline max-w-[160px] truncate"
                            >
                              <LinkedInIcon className="h-3 w-3 shrink-0 text-sky-400" />
                              <span className="truncate">Company Page</span>
                              <ExternalLink className="h-2.5 w-2.5 opacity-70" />
                            </a>
                          )}
                          {dmLarge && (
                            <a
                              href={dmLarge.startsWith("http") ? dmLarge : `https://${dmLarge}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 hover:underline max-w-[160px] truncate"
                            >
                              <LinkedInIcon className="h-3 w-3 shrink-0 text-indigo-400" />
                              <span className="truncate">DM Profile</span>
                              <ExternalLink className="h-2.5 w-2.5 opacity-70" />
                            </a>
                          )}
                          {!companyLi && !dmLarge && <span className="text-slate-600 italic">—</span>}
                        </div>
                      </td>

                      {/* Action */}
                      <td className="py-3.5 pr-4 pl-3 text-right">
                        <button
                          onClick={() => setInspectedLead(lead)}
                          className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-[11px] font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition-colors"
                        >
                          <Eye className="h-3 w-3 text-indigo-400" />
                          <span>Inspect</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer with Summary */}
        <div className="flex items-center justify-between border-t border-slate-800 bg-slate-950/60 px-5 py-3 text-xs text-slate-400">
          <span>
            Showing <strong className="text-slate-200">{leads.length}</strong> company leads
          </span>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              {summary.full_lead_count} Full Leads
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-sky-400" />
              {summary.website_only_count} Websites Only
            </span>
          </div>
        </div>
      </div>

      {/* Integrated Modals */}
      <RunModal
        isOpen={isRunModalOpen}
        onClose={() => setIsRunModalOpen(false)}
        onRunComplete={() => {
          fetchRuns();
          fetchLeads();
        }}
      />

      <LeadDrawer
        lead={inspectedLead}
        isOpen={Boolean(inspectedLead)}
        onClose={() => setInspectedLead(null)}
      />
    </div>
  );
}
