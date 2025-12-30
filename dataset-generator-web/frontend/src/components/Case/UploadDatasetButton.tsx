import { useState } from "react"
import { UploadIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import useCustomToast from "@/hooks/useCustomToast"
import { CasesService, type ApiError } from "@/client"

interface UploadDatasetButtonProps {
  caseId: string
  onUploadSuccess: () => void
}

export function UploadDatasetButton({ caseId, onUploadSuccess }: UploadDatasetButtonProps) {
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [showProgressDialog, setShowProgressDialog] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const { showSuccessToast, showErrorToast } = useCustomToast()

  // Handle file selection
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Validate file extension
    const fileName = file.name.toLowerCase()
    if (!fileName.endsWith('.json') && !fileName.endsWith('.gz')) {
      showErrorToast("Invalid file format. Only .json and .gz files are supported")
      return
    }

    setSelectedFile(file)
    setShowConfirmDialog(true)
  }

  // Handle upload confirmation
  const handleConfirmUpload = async () => {
    if (!selectedFile) return

    setShowConfirmDialog(false)
    setShowProgressDialog(true)

    try {
      // Create FormData
      const formData = new FormData()
      formData.append('file', selectedFile)

      // Call the API
      await CasesService.uploadDataset({
        id: caseId,
        formData: {
          file: selectedFile
        }
      })

      setShowProgressDialog(false)
      showSuccessToast("Dataset uploaded successfully")
      onUploadSuccess()
    } catch (error) {
      setShowProgressDialog(false)
      const apiError = error as ApiError
      const errorBody = apiError.body as any
      const errorMessage = errorBody?.detail || apiError.message || "Failed to upload dataset. Please try again."
      showErrorToast(errorMessage)
    } finally {
      setSelectedFile(null)
    }
  }

  // Handle upload cancellation
  const handleCancelUpload = () => {
    setShowConfirmDialog(false)
    setSelectedFile(null)
  }

  return (
    <>
      {/* Hidden file input */}
      <input
        type="file"
        id="dataset-upload-input"
        accept=".json,.gz"
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />

      {/* Upload button */}
      <Button
        onClick={() => document.getElementById('dataset-upload-input')?.click()}
        variant="default"
      >
        <UploadIcon className="mr-2 h-4 w-4" />
        Upload Dataset
      </Button>

      {/* Confirmation Dialog */}
      <Dialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Upload</DialogTitle>
            <DialogDescription>
              This operation overrides all queries, documents, and ratings already assigned to this case.
              Are you sure you want to proceed?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={handleCancelUpload}>
              Cancel
            </Button>
            <Button variant="default" onClick={handleConfirmUpload}>
              OK
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Progress Dialog */}
      <Dialog open={showProgressDialog} onOpenChange={() => {}}>
        <DialogContent showCloseButton={false} className="sm:max-w-md">
          <div className="flex flex-col items-center justify-center gap-4 py-8">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="text-lg font-medium">Uploading in progress</p>
            <p className="text-muted-foreground text-sm">Please wait...</p>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

