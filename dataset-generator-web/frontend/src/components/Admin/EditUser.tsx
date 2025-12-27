import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Pencil } from "lucide-react"
import { useState } from "react"

import { type UserPublic, UsersService } from "@/client"
import UserFormDialog from "@/components/Admin/UserFormDialog"
import { DropdownMenuItem } from "@/components/ui/dropdown-menu"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface EditUserProps {
  user: UserPublic
  onSuccess: () => void
}

const EditUser = ({ user, onSuccess }: EditUserProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: (data: any) =>
      UsersService.updateUser({ userId: user.user_id, requestBody: data }),
    onSuccess: () => {
      showSuccessToast("User updated successfully")
      setIsOpen(false)
      onSuccess()
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const onSubmit = (data: any) => {
    mutation.mutate(data)
  }

  return (
    <UserFormDialog
      mode="edit"
      isOpen={isOpen}
      onOpenChange={setIsOpen}
      onSubmit={onSubmit}
      isLoading={mutation.isPending}
      user={user}
      trigger={
        <DropdownMenuItem
          onSelect={(e) => e.preventDefault()}
          onClick={() => setIsOpen(true)}
        >
          <Pencil />
          Edit User
        </DropdownMenuItem>
      }
    />
  )
}

export default EditUser
