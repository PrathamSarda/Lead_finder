import Card from "../components/ui/Card";
import Table from "../components/ui/Table";

const COLUMNS = [
  { key: "name", header: "Company" },
  { key: "industry", header: "Industry" },
  { key: "employee_count", header: "Employees" },
  { key: "location", header: "Location" },
  { key: "contact_email", header: "Email" },
  { key: "status", header: "Status" },
];

// No data fetching wired up yet — replace with a React Query hook
// (e.g. useCompanies) once GET /api/v1/companies is ready to be consumed.
const SAMPLE_DATA = [];

/**
 * Lists companies discovered by the automation pipeline
 * (LinkedIn, Indeed, Google, Wellfound). No live data yet — this page
 * wires up the reusable Table component against the Company schema
 * defined in the backend.
 */
export default function Companies() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Companies</h1>
        <p className="mt-1 text-sm text-slate-500">
          Leads discovered across LinkedIn, Indeed, Google, and Wellfound.
        </p>
      </div>

      <Card title="All companies" description="Sourced companies and their contact status.">
        <Table columns={COLUMNS} data={SAMPLE_DATA} emptyMessage="No companies found yet." />
      </Card>
    </div>
  );
}
