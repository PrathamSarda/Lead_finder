import { useAuth } from "../../context/AuthContext";
import {
  Activity,
  CheckCircle2,
  FileSpreadsheet,
  Globe,
  Loader2,
  LogOut,
  Play,
  ShieldCheck,
  User,
} from "lucide-react";

export default function Navbar({ activeRun, onOpenRunModal, onExportExcel }) {
  const { user, logout } = useAuth();

  return (
    <header className="flex h-18 items-center justify-between border-b border-slate-800/80 bg-slate-950/80 px-6 backdrop-blur-xl">
      {/* Left: Active Pipeline Status & Health */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
          </span>
          <span className="hidden sm:inline">Engine Active</span>
          <span className="text-slate-400">• FMCSA & Web Enrichment</span>
        </div>

        {/* If pipeline is currently running */}
        {activeRun && activeRun.status === "running" && (
          <div
            onClick={onOpenRunModal}
            className="flex cursor-pointer items-center gap-2 rounded-full border border-indigo-500/40 bg-indigo-500/15 px-3 py-1 text-xs font-semibold text-indigo-300 animate-pulse hover:bg-indigo-500/25 transition-colors"
          >
            <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-400" />
            <span>
              Processing: {activeRun.processed_count}/{activeRun.requested_count}
            </span>
          </div>
        )}
      </div>

      {/* Right: Quick Actions and User Profile */}
      <div className="flex items-center gap-3">
        {/* Quick Excel Export CTA */}
        {onExportExcel && (
          <button
            onClick={onExportExcel}
            className="hidden sm:flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1.5 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <FileSpreadsheet className="h-4 w-4 text-emerald-400" />
            <span>Excel (.xlsx)</span>
          </button>
        )}

        {/* Run Discovery CTA */}
        <button
          onClick={onOpenRunModal}
          className="flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-md shadow-indigo-600/30 hover:bg-indigo-500 transition-all active:scale-[0.98]"
        >
          <Play className="h-3.5 w-3.5 fill-current" />
          <span>Run Discovery</span>
        </button>

        {/* Divider */}
        <div className="h-5 w-[1px] bg-slate-800" />

        {/* User Badge */}
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800 border border-slate-700 text-xs font-semibold text-slate-300">
            PG
          </div>
          <div className="hidden text-left lg:block">
            <p className="text-xs font-semibold text-slate-200">{user?.full_name || "Prokizen Client"}</p>
            <p className="text-[10px] text-slate-400">{user?.email || "client@prokizen.com"}</p>
          </div>
          <button
            onClick={logout}
            title="Log out or reset session"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
