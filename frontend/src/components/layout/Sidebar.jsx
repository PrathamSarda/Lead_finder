import { NavLink } from "react-router-dom";
import {
  Building2,
  Compass,
  FileSpreadsheet,
  Layers,
  PlayCircle,
  Settings as SettingsIcon,
  Sparkles,
  TrendingUp,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Lead Intelligence", icon: Compass, badge: "Live" },
  { to: "/companies", label: "Discovered Finds", icon: Building2 },
  { to: "/settings", label: "System Config", icon: SettingsIcon },
];

export default function Sidebar({ onOpenRunModal }) {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-800/80 bg-slate-950/95 backdrop-blur-xl md:flex">
      {/* Brand Header */}
      <div className="flex h-18 items-center gap-3 border-b border-slate-800/80 px-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 shadow-lg shadow-indigo-500/20">
          <Sparkles className="h-5 w-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-bold tracking-tight text-white">LeadFinder</span>
            <span className="rounded bg-indigo-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-400">
              v2.0
            </span>
          </div>
          <p className="text-[11px] font-medium text-slate-400">Prokizen Global LLP</p>
        </div>
      </div>

      {/* Quick Launch CTA */}
      <div className="p-4">
        <button
          onClick={onOpenRunModal}
          className="group relative flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/25 transition-all hover:scale-[1.02] hover:shadow-indigo-600/40 active:scale-[0.98]"
        >
          <PlayCircle className="h-4 w-4 transition-transform group-hover:rotate-12" />
          <span>Run Test Cases</span>
          <span className="absolute right-0 top-0 h-full w-12 bg-white/10 skew-x-12 opacity-0 group-hover:opacity-100 transition-opacity" />
        </button>
      </div>

      {/* Navigation */}
      <div className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        Workspace
      </div>
      <nav className="flex-1 space-y-1.5 px-3">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center justify-between rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
                  isActive
                    ? "bg-indigo-600/15 text-indigo-300 font-semibold border border-indigo-500/30 shadow-inner"
                    : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                }`
              }
            >
              <div className="flex items-center gap-3">
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-500/20">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Target Metrics Pill */}
      <div className="m-4 rounded-xl border border-slate-800/90 bg-slate-900/60 p-3.5 text-xs">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="flex items-center gap-1.5 font-medium">
            <TrendingUp className="h-3.5 w-3.5 text-emerald-400" /> Daily Target
          </span>
          <span className="font-semibold text-white">80 / day</span>
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          US companies (1-20 employees) with verified domain & direct contacts.
        </p>
      </div>

      {/* Footer Info */}
      <div className="border-t border-slate-800/80 p-4 text-[11px] text-slate-400">
        <p className="font-medium text-slate-400">Company Lead Finder</p>
        <p>© 2026 Prokizen Global LLP</p>
      </div>
    </aside>
  );
}
