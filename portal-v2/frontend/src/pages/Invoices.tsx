import { useQuery } from '@tanstack/react-query';
import { invoiceApi } from '../api/client';
import { FileText, Download, ExternalLink } from 'lucide-react';
import { format } from 'date-fns';
import { de } from 'date-fns/locale';

interface Invoice {
  id: number;
  invoice_number: string;
  customer_id: number;
  issue_date: string;
  due_date: string;
  subtotal: number;
  tax_amount: number;
  total: number;
  status: string;
  pdf_url: string | null;
}

export default function Invoices() {
  const { data: invoices, isLoading } = useQuery({
    queryKey: ['invoices'],
    queryFn: () => invoiceApi.list().then(res => res.data),
  });

  const statusColors: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-800',
    sent: 'bg-blue-100 text-blue-800',
    paid: 'bg-green-100 text-green-800',
    cancelled: 'bg-red-100 text-red-800',
  };

  const statusLabels: Record<string, string> = {
    draft: 'Entwurf',
    sent: 'Gesendet',
    paid: 'Bezahlt',
    cancelled: 'Storniert',
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Rechnungen</h1>
      </div>

      {/* Invoices Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nummer</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Datum</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fällig</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Netto</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">MwSt</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Gesamt</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">PDF</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr>
                <td colSpan={8} className="px-6 py-8 text-center text-gray-500">
                  Laden...
                </td>
              </tr>
            ) : invoices?.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-6 py-8 text-center text-gray-500">
                  Keine Rechnungen vorhanden
                </td>
              </tr>
            ) : (
              invoices?.map((inv: Invoice) => (
                <tr key={inv.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap font-medium">
                    {inv.invoice_number}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {format(new Date(inv.issue_date), 'dd.MM.yyyy', { locale: de })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {inv.due_date ? format(new Date(inv.due_date), 'dd.MM.yyyy', { locale: de }) : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    €{inv.subtotal.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-gray-500">
                    €{inv.tax_amount.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right font-semibold">
                    €{inv.total.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs rounded-full ${statusColors[inv.status]}`}>
                      {statusLabels[inv.status] || inv.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    {inv.pdf_url ? (
                      <a
                        href={inv.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800"
                      >
                        <Download className="w-5 h-5" />
                      </a>
                    ) : (
                      <span className="text-gray-300">
                        <FileText className="w-5 h-5" />
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
