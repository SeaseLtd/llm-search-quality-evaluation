import { createFileRoute } from "@tanstack/react-router"

import useAuth from "@/hooks/useAuth"

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

function Dashboard() {
  const { user: currentUser } = useAuth()

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 border-b px-6 py-4 bg-background">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Hi, {currentUser?.full_name || currentUser?.email} 👋
          </h1>
          <p className="text-muted-foreground">
            Welcome back, nice to see you again!
          </p>
        </div>
      </header>
      <div className="page-content flex-1 overflow-y-auto px-6 py-4">
        {/* Dashboard content goes here */}
      </div>
    </div>
  )
}
