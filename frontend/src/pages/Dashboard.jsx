import Card from "../components/ui/Card";
import Table from "../components/ui/Table";

const SAMPLE_COLUMNS = [
  { key: "name", header: "Name" },
  { key: "status", header: "Status" },
  { key: "updated", header: "Last updated" },
];

const SAMPLE_DATA = [];

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">
          This is a placeholder overview page — wire up real metrics and widgets here.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card title="Metric one">
          <p className="text-3xl font-semibold text-slate-900">—</p>
        </Card>
        <Card title="Metric two">
          <p className="text-3xl font-semibold text-slate-900">—</p>
        </Card>
        <Card title="Metric three">
          <p className="text-3xl font-semibold text-slate-900">—</p>
        </Card>
      </div>

      <Card title="Recent activity" description="Latest items will appear here.">
        <Table columns={SAMPLE_COLUMNS} data={SAMPLE_DATA} emptyMessage="No activity yet." />
      </Card>
    </div>
  );
}
