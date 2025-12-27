import { zodResolver } from "@hookform/resolvers/zod"
import { ReactNode } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type UserPublic } from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormField,
  FormCase,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"

const createUserSchema = z
  .object({
    email: z.string().email({ message: "Invalid email address" }),
    full_name: z.string().optional(),
    password: z
      .string()
      .min(1, { message: "Password is required" })
      .min(8, { message: "Password must be at least 8 characters" }),
    confirm_password: z
      .string()
      .min(1, { message: "Please confirm your password" }),
    is_superuser: z.boolean(),
    is_active: z.boolean(),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "The passwords don't match",
    path: ["confirm_password"],
  })

const editUserSchema = z
  .object({
    email: z.string().email({ message: "Invalid email address" }),
    full_name: z.string().optional(),
    password: z
      .string()
      .min(8, { message: "Password must be at least 8 characters" })
      .optional()
      .or(z.literal("")),
    confirm_password: z.string().optional(),
    is_superuser: z.boolean().optional(),
    is_active: z.boolean().optional(),
  })
  .refine((data) => !data.password || data.password === data.confirm_password, {
    message: "The passwords don't match",
    path: ["confirm_password"],
  })

type CreateFormData = z.infer<typeof createUserSchema>
type EditFormData = z.infer<typeof editUserSchema>

interface UserFormDialogProps {
  mode: "create" | "edit"
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: CreateFormData | EditFormData) => void
  isLoading: boolean
  trigger?: ReactNode
  user?: UserPublic
}

const UserFormDialog = ({
  mode,
  isOpen,
  onOpenChange,
  onSubmit,
  isLoading,
  trigger,
  user,
}: UserFormDialogProps) => {
  const isEditMode = mode === "edit"

  const form = useForm<CreateFormData | EditFormData>({
    resolver: zodResolver(isEditMode ? editUserSchema : createUserSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: isEditMode && user
      ? {
          email: user.email,
          full_name: user.full_name ?? undefined,
          is_superuser: user.is_superuser,
          is_active: user.is_active,
        }
      : {
          email: "",
          full_name: "",
          password: "",
          confirm_password: "",
          is_superuser: false,
          is_active: false,
        },
  })

  const handleSubmit = (data: CreateFormData | EditFormData) => {
    if (isEditMode) {
      // exclude confirm_password from submission data and remove password if empty
      const { confirm_password: _, ...submitData } = data as EditFormData
      if (!submitData.password) {
        delete submitData.password
      }
      onSubmit(submitData)
    } else {
      onSubmit(data)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      {trigger}
      <DialogContent className="sm:max-w-md">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)}>
            <DialogHeader>
              <DialogTitle>{isEditMode ? "Edit User" : "Add User"}</DialogTitle>
              <DialogDescription>
                {isEditMode
                  ? "Update the user details below."
                  : "Fill in the form below to add a new user to the system."}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormCase>
                    <FormLabel>
                      Email <span className="text-destructive">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Email"
                        type="email"
                        {...field}
                        required
                      />
                    </FormControl>
                    <FormMessage />
                  </FormCase>
                )}
              />

              <FormField
                control={form.control}
                name="full_name"
                render={({ field }) => (
                  <FormCase>
                    <FormLabel>Full Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Full name" type="text" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormCase>
                )}
              />

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormCase>
                    <FormLabel>
                      {isEditMode ? "Set Password" : "Set Password"}{" "}
                      {!isEditMode && <span className="text-destructive">*</span>}
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Password"
                        type="password"
                        {...field}
                        required={!isEditMode}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormCase>
                )}
              />

              <FormField
                control={form.control}
                name="confirm_password"
                render={({ field }) => (
                  <FormCase>
                    <FormLabel>
                      Confirm Password{" "}
                      {!isEditMode && <span className="text-destructive">*</span>}
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Password"
                        type="password"
                        {...field}
                        required={!isEditMode}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormCase>
                )}
              />

              <FormField
                control={form.control}
                name="is_superuser"
                render={({ field }) => (
                  <FormCase className="flex items-center gap-3 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <FormLabel className="font-normal">Is superuser?</FormLabel>
                  </FormCase>
                )}
              />

              <FormField
                control={form.control}
                name="is_active"
                render={({ field }) => (
                  <FormCase className="flex items-center gap-3 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <FormLabel className="font-normal">Is active?</FormLabel>
                  </FormCase>
                )}
              />
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline" disabled={isLoading}>
                  Cancel
                </Button>
              </DialogClose>
              <LoadingButton type="submit" loading={isLoading}>
                Save
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

export default UserFormDialog

