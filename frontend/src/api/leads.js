import apiClient from "./client";
import * as XLSX from "xlsx";

export const leadsApi = {
  /**
   * Fetch leads with filtering, search and stats
   */
  getLeads: async (params = {}) => {
    const res = await apiClient.get("/leads", { params });
    return res.data;
  },

  /**
   * List available historical runs & outputs
   */
  getRuns: async () => {
    const res = await apiClient.get("/leads/runs");
    return res.data;
  },

  /**
   * Trigger discovery / test case run
   */
  triggerRun: async ({ count = 10, state = null, mode = "discovery" }) => {
    const res = await apiClient.post("/leads/run", { count, state, mode });
    return res.data;
  },

  /**
   * Poll active pipeline run status & live logs
   */
  getRunStatus: async () => {
    const res = await apiClient.get("/leads/run/status");
    return res.data;
  },

  /**
   * Cancel active pipeline run
   */
  cancelRun: async () => {
    const res = await apiClient.post("/leads/run/cancel");
    return res.data;
  },

  /**
   * Direct backend download link for Excel
   */
  getBackendExcelUrl: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return `/api/v1/leads/export/excel${query ? `?${query}` : ""}`;
  },

  /**
   * Direct backend download link for CSV
   */
  getBackendCsvUrl: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return `/api/v1/leads/export/csv${query ? `?${query}` : ""}`;
  },

  /**
   * Client-side instant Excel (.xlsx) export using SheetJS
   * Works smoothly with active filters, custom selection, or full dataset.
   */
  exportToExcelClient: (leads, filename = null, summaryStats = null) => {
    if (!leads || leads.length === 0) {
      throw new Error("No leads available to export.");
    }

    const cleanName = filename || `Prokizen_Leads_${new Date().toISOString().slice(0, 10)}.xlsx`;

    // Map clean tabular data matching the 5 required parameters
    const tableData = leads.map((lead, idx) => ({
      "#": idx + 1,
      "Company Name": lead.company_name || "",
      "Website": lead.website || "",
      "Company LinkedIn": lead.company_linkedin_url || lead.linkedin || "",
      "Decision Maker Name": lead.decision_maker_name || lead.owner_name || "",
      "Decision Maker LinkedIn": lead.decision_maker_linkedin_url || "",
    }));

    const wb = XLSX.utils.book_new();

    // Sheet 1: Main Leads Table
    const ws = XLSX.utils.json_to_sheet(tableData);

    // Auto calculate column widths
    const colWidths = [
      { wch: 4 },  // #
      { wch: 32 }, // Company Name
      { wch: 32 }, // Website
      { wch: 36 }, // Company LinkedIn
      { wch: 28 }, // Decision Maker Name
      { wch: 38 }, // Decision Maker LinkedIn
    ];
    ws["!cols"] = colWidths;

    XLSX.utils.book_append_sheet(wb, ws, "Company Leads");

    // Sheet 2: Executive Summary & Provenance
    if (summaryStats) {
      const summaryRows = [
        { Metric: "Executive Summary", Value: "Prokizen Global LLP B2B Lead Intelligence" },
        { Metric: "Generated Timestamp", Value: new Date().toLocaleString() },
        { Metric: "Total Leads in Export", Value: leads.length },
        { Metric: "Total Discovered in Source", Value: summaryStats.total_leads || leads.length },
        { Metric: "Verified Leads (Total)", Value: summaryStats.verified_count || 0 },
        { Metric: "Full Leads (Website + Contact)", Value: summaryStats.full_lead_count || 0 },
        { Metric: "Websites Only", Value: summaryStats.website_only_count || 0 },
        { Metric: "Needs Review", Value: summaryStats.needs_review_count || 0 },
        { Metric: "Unresolved", Value: summaryStats.unresolved_count || 0 },
        { Metric: "Verified Emails Extracted", Value: summaryStats.emails_count || 0 },
        { Metric: "Verified Phones Extracted", Value: summaryStats.phones_count || 0 },
        { Metric: "Average Verification Confidence", Value: `${summaryStats.avg_confidence || 0}` },
      ];
      const wsSummary = XLSX.utils.json_to_sheet(summaryRows);
      wsSummary["!cols"] = [{ wch: 30 }, { wch: 45 }];
      XLSX.utils.book_append_sheet(wb, wsSummary, "Pipeline Summary");
    }

    XLSX.writeFile(wb, cleanName);
  },
};
