import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus } from "lucide-react"
import { useState } from "react"

import { type UserCreate, UsersService } from "@/client"
import UserFormDialog from "@/components/Admin/UserFormDialog"
import { Button } from "@/components/ui/button"
import { DialogTrigger } from "@/components/ui/dialog"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const AddUser = () => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: (data: UserCreate) =>
      UsersService.createUser({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("User created successfully")
      setIsOpen(false)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const onSubmit = (data: any) => {
    mutation.mutate(data as UserCreate)
  }

  return (
    <UserFormDialog
      mode="create"
      isOpen={isOpen}
      onOpenChange={setIsOpen}
      onSubmit={onSubmit}
      isLoading={mutation.isPending}
      trigger={
        <DialogTrigger asChild>
          <Button className="my-0">
            <Plus className="mr-2" />
            Add User
          </Button>
        </DialogTrigger>
      }
    />
  )
}

export default AddUser
