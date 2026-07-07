/**
 * Reusable data table.
 *
 * columns: [{ key, header, render? }]
 * data: array of row objects
 */
export default function Table({ columns, data, emptyMessage = "No records found." }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-300 py-12 text-sm text-slate-500">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className="px-4 py-3 text-left font-medium text-slate-500"
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {data.map((row, rowIndex) => (
            <tr key={row.id ?? rowIndex} className="hover:bg-slate-50">
              {columns.map((column) => (
                <td key={column.key} className="px-4 py-3 text-slate-700">
                  {column.render ? column.render(row) : row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
