import { useQuery } from '@tanstack/react-query';
import { userApi } from '../api/client';
import { useAuth } from '../context/AuthContext';

interface User {
  id: number;
  email: string;
  name: string | null;
  avatar_url: string | null;
  role: string;
  is_active: boolean;
}

export default function Users() {
  const { user: currentUser } = useAuth();
  
  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => userApi.list().then(res => res.data),
  });

  const roleColors: Record<string, string> = {
    admin: 'bg-purple-100 text-purple-800',
    user: 'bg-blue-100 text-blue-800',
    viewer: 'bg-gray-100 text-gray-800',
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Benutzer</h1>

      {/* Users Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? (
          <div className="col-span-full text-center py-8 text-gray-500">Laden...</div>
        ) : (
          users?.map((user: User) => (
            <div
              key={user.id}
              className={`bg-white rounded-xl shadow-sm border p-6 ${
                !user.is_active ? 'opacity-50' : ''
              }`}
            >
              <div className="flex items-center gap-4">
                {user.avatar_url ? (
                  <img
                    src={user.avatar_url}
                    alt={user.name || user.email}
                    className="w-12 h-12 rounded-full"
                  />
                ) : (
                  <div className="w-12 h-12 rounded-full bg-gray-200 flex items-center justify-center">
                    <span className="text-xl font-medium text-gray-600">
                      {(user.name || user.email).charAt(0).toUpperCase()}
                    </span>
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">
                    {user.name || user.email}
                    {user.id === currentUser?.id && (
                      <span className="text-xs text-gray-500 ml-2">(Du)</span>
                    )}
                  </p>
                  <p className="text-sm text-gray-500 truncate">{user.email}</p>
                </div>
              </div>
              <div className="mt-4 flex items-center justify-between">
                <span className={`px-2 py-1 text-xs rounded-full ${roleColors[user.role]}`}>
                  {user.role === 'admin' ? 'Admin' : user.role === 'user' ? 'Benutzer' : 'Betrachter'}
                </span>
                {!user.is_active && (
                  <span className="text-xs text-red-600">Deaktiviert</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
