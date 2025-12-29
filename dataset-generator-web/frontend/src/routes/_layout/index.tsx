import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import {
  FileText,
  Search,
  Plus,
  TrendingUp,
  Database,
  Sparkles,
  ArrowRight,
  BarChart3
} from "lucide-react"

import useAuth from "@/hooks/useAuth"
import { CasesService } from "@/client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "Dashboard - Dataset Generator",
      },
    ],
  }),
})

function StatCard({
  title,
  value,
  description,
  icon: Icon,
  trend
}: {
  title: string
  value: number | string
  description: string
  icon: any
  trend?: { value: string; positive: boolean }
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground mt-1">
          {description}
        </p>
        {trend && (
          <div className="flex items-center mt-2">
            <TrendingUp className={`h-3 w-3 mr-1 ${trend.positive ? 'text-green-500' : 'text-red-500'}`} />
            <span className={`text-xs ${trend.positive ? 'text-green-500' : 'text-red-500'}`}>
              {trend.value}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function QuickAction({
  title,
  description,
  icon: Icon,
  onClick
}: {
  title: string
  description: string
  icon: any
  onClick: () => void
}) {
  return (
    <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={onClick}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="rounded-lg bg-primary/10 p-2 mb-2">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
        </div>
        <CardTitle className="text-lg">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
    </Card>
  )
}

function RecentCasesList({ cases }: { cases: any[] }) {
  const navigate = useNavigate()

  if (!cases || cases.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
        <p>No cases yet. Create your first case to get started!</p>
      </div>
    )
  }

  // Sort by updated_at descending and take only the 3 most recent
  const recentCases = [...cases]
    .sort((a, b) => {
      const dateA = new Date(a.updated_at).getTime()
      const dateB = new Date(b.updated_at).getTime()
      return dateB - dateA
    })
    .slice(0, 3)

  return (
    <div className="space-y-3">
      {recentCases.map((caseItem: any) => (
        <div
          key={caseItem.case_id}
          className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent cursor-pointer transition-colors"
          onClick={() => navigate({ to: "/case/$id", params: { id: caseItem.case_id } })}
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="font-medium truncate">{caseItem.title}</h4>
              <Badge variant="secondary" className="text-xs">
                {caseItem.num_queries || 0} queries
              </Badge>
            </div>
            {caseItem.description && (
              <p className="text-sm text-muted-foreground truncate mt-1">
                {caseItem.description}
              </p>
            )}
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground ml-2 shrink-0" />
        </div>
      ))}
    </div>
  )
}

function DashboardContent() {
  const { data: cases, isLoading } = useQuery({
    queryKey: ["cases"],
    queryFn: () => CasesService.readCases({ skip: 0, limit: 100 }),
  })
  const navigate = useNavigate()

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader className="space-y-0 pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16 mb-2" />
                <Skeleton className="h-3 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  const totalCases = cases?.length || 0
  const totalQueries = cases?.reduce((sum: number, c: any) => sum + (c.num_queries || 0), 0) || 0
  const casesWithQueries = cases?.filter((c: any) => (c.num_queries || 0) > 0).length || 0

  const hasData = totalCases > 0

  return (
    <div className="space-y-6">
      {/* Welcome Banner for new users */}
      {!hasData && (
        <Card className="bg-linear-to-r from-primary/10 via-primary/5 to-background border-primary/20">
          <CardHeader>
            <div className="flex items-start gap-4">
              <div className="rounded-full bg-primary/20 p-3">
                <Sparkles className="h-6 w-6 text-primary" />
              </div>
              <div className="flex-1">
                <CardTitle className="text-xl mb-2">Welcome to Dataset Generator!</CardTitle>
                <CardDescription className="text-base">
                  Start creating high-quality evaluation datasets for your LLM search applications.
                  Create cases, add queries, and rate results to build comprehensive test datasets.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
        </Card>
      )}

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Cases"
          value={totalCases}
          description="Evaluation test cases"
          icon={FileText}
          trend={totalCases > 0 ? { value: `${casesWithQueries} active`, positive: true } : undefined}
        />
        <StatCard
          title="Total Queries"
          value={totalQueries}
          description="Search queries defined"
          icon={Search}
        />
        <StatCard
          title="Active Cases"
          value={casesWithQueries}
          description="Cases with queries"
          icon={BarChart3}
        />
        <StatCard
          title="Avg Queries/Case"
          value={totalCases > 0 ? (totalQueries / totalCases).toFixed(1) : "0"}
          description="Query density"
          icon={TrendingUp}
        />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Quick Actions */}
        <div>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Quick Actions
          </h2>
          <div className="grid gap-4">
            <QuickAction
              title="Create New Case"
              description="Start a new evaluation test case"
              icon={Plus}
              onClick={() => navigate({ to: "/cases", search: { create: true } })}
            />
            <QuickAction
              title="View All Cases"
              description="Browse and manage your cases"
              icon={Database}
              onClick={() => navigate({ to: "/cases" })}
            />
          </div>
        </div>

        {/* Recent Cases */}
        <div>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Recent Cases
          </h2>
          <Card>
            <CardContent className="pt-6">
              <RecentCasesList cases={cases || []} />
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Tips Section */}
      {!hasData && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              Getting Started Tips
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex gap-3">
                <div className="rounded-full bg-primary/10 p-2 h-fit">
                  <span className="text-sm font-bold text-primary">1</span>
                </div>
                <div>
                  <h4 className="font-medium mb-1">Create a Case</h4>
                  <p className="text-sm text-muted-foreground">
                    Define your evaluation scenario with a title and description
                  </p>
                </div>
              </div>
              <div className="flex gap-3">
                <div className="rounded-full bg-primary/10 p-2 h-fit">
                  <span className="text-sm font-bold text-primary">2</span>
                </div>
                <div>
                  <h4 className="font-medium mb-1">Add Queries</h4>
                  <p className="text-sm text-muted-foreground">
                    Define the search queries you want to evaluate
                  </p>
                </div>
              </div>
              <div className="flex gap-3">
                <div className="rounded-full bg-primary/10 p-2 h-fit">
                  <span className="text-sm font-bold text-primary">3</span>
                </div>
                <div>
                  <h4 className="font-medium mb-1">Rate Results</h4>
                  <p className="text-sm text-muted-foreground">
                    Compare LLM ratings with your own to build quality datasets
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function Dashboard() {
  const { user: currentUser } = useAuth()

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 border-b px-6 py-2 bg-background">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Hi, {currentUser?.full_name || currentUser?.email} 👋
          </h1>
        </div>
      </header>
      <div className="page-content flex-1 overflow-y-auto px-6 py-6">
        <DashboardContent />
      </div>
    </div>
  )
}
