import { useQuery } from '@tanstack/react-query';
import { timesheetApi } from '../api/client';
import { Clock, FileText, Euro, TrendingUp } from 'lucide-react';

export default function Dashboard() {
  const { data: summary, isLoading } = useQuery({
    queryKey: ['timesheet-summary'],
    queryFn: () => timesheetApi.summary().then(res => res.data),
  });

  const stats = [
    {
      name: 'Stunden (Monat)',
      value: summary?.total_hours?.toFixed(1) || '0',
      icon: Clock,
      color: 'bg-blue-500',
    },
    {
      name: 'Verrechenbar',
      value: summary?.total_billable_hours?.toFixed(1) || '0',
      icon: TrendingUp,
      color: 'bg-green-500',
    },
    {
      name: 'Umsatz (€)',
      value: summary?.total_amount?.toLocaleString('de-DE', { minimumFractionDigits: 2 }) || '0,00',
      icon: Euro,
      color: 'bg-yellow-500',
    },
    {
      name: 'Einträge',
      value: summary?.entries_count || '0',
      icon: FileText,
      color: 'bg-purple-500',
    },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat) => (
          <div
            key={stat.name}
            className="bg-white rounded-xl shadow-sm p-6 border border-gray-100"
          >
            <div className="flex items-center">
              <div className={`${stat.color} p-3 rounded-lg`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">{stat.name}</p>
                <p className="text-2xl font-bold text-gray-900">
                  {isLoading ? '...' : stat.value}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Schnellaktionen</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a
            href="/timesheets"
            className="flex items-center p-4 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
          >
            <Clock className="w-8 h-8 text-blue-600" />
            <div className="ml-3">
              <p className="font-medium text-gray-900">Stunden erfassen</p>
              <p className="text-sm text-gray-500">Neuen Zeiteintrag erstellen</p>
            </div>
          </a>
          <a
            href="/invoices"
            className="flex items-center p-4 bg-green-50 rounded-lg hover:bg-green-100 transition-colors"
          >
            <FileText className="w-8 h-8 text-green-600" />
            <div className="ml-3">
              <p className="font-medium text-gray-900">Rechnung erstellen</p>
              <p className="text-sm text-gray-500">Aus Zeiteinträgen generieren</p>
            </div>
          </a>
          <a
            href="/users"
            className="flex items-center p-4 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors"
          >
            <TrendingUp className="w-8 h-8 text-purple-600" />
            <div className="ml-3">
              <p className="font-medium text-gray-900">Team verwalten</p>
              <p className="text-sm text-gray-500">Benutzer und Rollen</p>
            </div>
          </a>
        </div>
      </div>
    </div>
  );
}
