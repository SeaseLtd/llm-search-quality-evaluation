import { EllipsisVertical } from "lucide-react"
import { useState } from "react"

import type { CasePublic } from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import DeleteCase from "@/components/Cases/DeleteCase.tsx"
import EditCase from "@/components/Cases/EditCase.tsx"

interface ItemActionsMenuProps {
  case_obj: CasePublic
}

export const CaseActionsMenu = ({ case_obj }: ItemActionsMenuProps) => {
  const [open, setOpen] = useState(false)

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <EllipsisVertical />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <EditCase case_obj={case_obj} onSuccess={() => setOpen(false)} />
        <DeleteCase id={case_obj.case_id} onSuccess={() => setOpen(false)} />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
