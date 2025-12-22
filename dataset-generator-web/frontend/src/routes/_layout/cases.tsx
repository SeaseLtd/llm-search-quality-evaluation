import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { Suspense } from "react"

import { CasesService } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import CreateCase from "@/components/Cases/CreateCase.tsx"
import { columns } from "@/components/Cases/columns"
import PendingCases from "@/components/Pending/PendingCases.tsx"

function getCasesQueryOptions() {
  return {
    queryFn: () => CasesService.readCases({ skip: 0, limit: 100 }),
    queryKey: ["cases"],
  }
}

export const Route = createFileRoute("/_layout/cases")({
  component: Cases,
  head: () => ({
    meta: [
      {
        title: "Cases - Dataset Generator",
      },
    ],
  }),
})

function CasesTableContent() {
  const { data: cases } = useSuspenseQuery(getCasesQueryOptions())
  const navigate = useNavigate()

  if (cases.data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Search className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">You don't have any cases yet</h3>
        <p className="text-muted-foreground">Create a new case to get started</p>
      </div>
    )
  }

  return (
    <DataTable
      columns={columns}
      data={cases.data}
      onRowClick={(caseObj) => {
        navigate({ to: "/case/$id", params: { id: String(caseObj.id) } })
      }}
    />
  )
}

function CasesTable() {
  return (
    <Suspense fallback={<PendingCases />}>
      <CasesTableContent />
    </Suspense>
  )
}

function Cases() {
  return (
    <div className="flex flex-col gap-6">
      <header className="sticky top-0 z-10 h-16 shrink-0 items-center gap-2 border-b px-4">
          <div className="flex items-center justify-between">
              <div>
                  <h1 className="text-2xl font-bold tracking-tight">Cases</h1>
                  <p className="text-muted-foreground">Create and manage your cases</p>
              </div>
              <CreateCase />
          </div>
      </header>
      <CasesTable />
    </div>
  )
}
