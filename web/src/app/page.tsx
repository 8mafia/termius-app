'use client'

import { useEffect } from 'react'
import { useQuery } from 'react-query'
import Link from 'next/link'
import { Plus, Terminal, Server, Users, Shield } from 'lucide-react'

import { useAuthStore } from '@/stores/auth'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

// Dashboard stats component
function DashboardStats() {
  const { user } = useAuthStore()

  const { data: stats, isLoading } = useQuery(
    'dashboard-stats',
    async () => {
      const response = await api.get('/users/stats')
      return response.data
    },
    {
      enabled: !!user,
    }
  )

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="pb-2">
              <div className="h-4 bg-gray-200 rounded w-20"></div>
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-gray-200 rounded w-16"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const statCards = [
    {
      title: 'SSH Hosts',
      value: stats?.hosts_count || 0,
      icon: Server,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      title: 'Active Sessions',
      value: stats?.active_sessions_count || 0,
      icon: Terminal,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      title: 'Account Age',
      value: `${stats?.account_age_days || 0} days`,
      icon: Shield,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
    {
      title: 'Team Members',
      value: '1', // Placeholder
      icon: Users,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {statCards.map((stat, index) => (
        <Card key={index}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {stat.title}
            </CardTitle>
            <stat.icon className={`h-4 w-4 ${stat.color}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stat.value}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// Recent hosts component
function RecentHosts() {
  const { user } = useAuthStore()

  const { data: hosts, isLoading } = useQuery(
    'recent-hosts',
    async () => {
      const response = await api.get('/hosts?limit=5&sort=last_connected_at&order=desc')
      return response.data.data
    },
    {
      enabled: !!user,
    }
  )

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Hosts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex items-center space-x-3 animate-pulse">
                <div className="h-8 w-8 bg-gray-200 rounded"></div>
                <div className="flex-1">
                  <div className="h-4 bg-gray-200 rounded w-32 mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-24"></div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Recent Hosts</CardTitle>
          <Link href="/hosts">
            <Button variant="outline" size="sm">
              View All
            </Button>
          </Link>
        </div>
        <CardDescription>
          Your recently connected SSH hosts
        </CardDescription>
      </CardHeader>
      <CardContent>
        {hosts && hosts.length > 0 ? (
          <div className="space-y-3">
            {hosts.map((host: any) => (
              <div key={host.id} className="flex items-center space-x-3 p-2 rounded-md hover:bg-gray-50">
                <div className="h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <Server className="h-4 w-4 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {host.name}
                  </p>
                  <p className="text-sm text-gray-500 truncate">
                    {host.username}@{host.hostname}:{host.port}
                  </p>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    host.connection_status === 'online'
                      ? 'bg-green-100 text-green-800'
                      : host.connection_status === 'offline'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {host.connection_status}
                  </span>
                  <Link href={`/terminal?host=${host.id}`}>
                    <Button size="sm" variant="outline">
                      Connect
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-6">
            <Server className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-sm font-medium text-gray-900 mb-1">No hosts yet</h3>
            <p className="text-sm text-gray-500 mb-4">
              Get started by adding your first SSH host
            </p>
            <Link href="/hosts/new">
              <Button size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Add Host
              </Button>
            </Link>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Quick actions component
function QuickActions() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
        <CardDescription>
          Common tasks and shortcuts
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Link href="/hosts/new">
            <Button variant="outline" className="w-full justify-start">
              <Plus className="h-4 w-4 mr-2" />
              Add New Host
            </Button>
          </Link>
          <Link href="/terminal">
            <Button variant="outline" className="w-full justify-start">
              <Terminal className="h-4 w-4 mr-2" />
              Open Terminal
            </Button>
          </Link>
          <Link href="/settings">
            <Button variant="outline" className="w-full justify-start">
              <Shield className="h-4 w-4 mr-2" />
              Security Settings
            </Button>
          </Link>
          <Link href="/docs">
            <Button variant="outline" className="w-full justify-start">
              <Terminal className="h-4 w-4 mr-2" />
              Documentation
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}

// Main dashboard component
export default function Dashboard() {
  const { user, isAuthenticated } = useAuthStore()

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      window.location.href = '/auth/login'
    }
  }, [isAuthenticated])

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-center">
          <Terminal className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Terminal className="h-8 w-8 text-blue-600 mr-3" />
              <h1 className="text-xl font-semibold text-gray-900">ParSSH</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-700">
                Welcome, {user?.full_name || user?.email}
              </span>
              <Link href="/settings">
                <Button variant="ghost" size="sm">
                  Settings
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* Page header */}
          <div className="mb-8">
            <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
            <p className="mt-1 text-sm text-gray-600">
              Manage your SSH hosts and connections
            </p>
          </div>

          {/* Stats grid */}
          <div className="mb-8">
            <DashboardStats />
          </div>

          {/* Content grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Recent hosts */}
            <div className="lg:col-span-2">
              <RecentHosts />
            </div>

            {/* Quick actions */}
            <div className="lg:col-span-1">
              <QuickActions />
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}