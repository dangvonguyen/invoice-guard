import { type SubmitEvent, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { UploadCloud } from 'lucide-react'

import type { InvoiceUploadResponse } from '@/entities/invoice'
import { uploadInvoice } from '@/entities/invoice'
import { formatFileSize } from '@/shared/lib/formatFileSize'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/shared/ui/dialog'
import { Field, FieldError, FieldGroup } from '@/shared/ui/field'

export interface UploadInvoiceDialogProps {
  onUploaded: (invoice: InvoiceUploadResponse) => void
}

export function UploadInvoiceDialog({ onUploaded }: UploadInvoiceDialogProps) {
  const [open, setOpen] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [hasError, setHasError] = useState(false)

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    onDrop: ([dropped]) => {
      if (dropped) setFile(dropped)
    },
  })

  function handleOpenChange(nextOpen: boolean): void {
    setOpen(nextOpen)
    if (nextOpen) {
      setFile(null)
      setHasError(false)
    }
  }

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    if (!file) return

    setIsSubmitting(true)
    setHasError(false)
    const result = await uploadInvoice(file)
    setIsSubmitting(false)

    if (result.kind === 'error') {
      setHasError(true)
      return
    }
    onUploaded(result.invoice)
    handleOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger render={<Button />}>Upload Invoice</DialogTrigger>
      <DialogContent>
        <form onSubmit={(event) => void handleSubmit(event)}>
          <DialogHeader>
            <DialogTitle className="font-semibold">Upload Invoice</DialogTitle>
          </DialogHeader>

          <FieldGroup className="pt-4">
            <Field>
              <div
                {...getRootProps()}
                className={cn(
                  'flex flex-col gap-1 cursor-pointer items-center justify-center rounded-lg border-dashed border-input border-2 bg-muted/50 px-4 text-center transition-colors hover:bg-muted/70 select-none',
                  isDragActive && 'border-ring bg-muted/70',
                )}
              >
                <UploadCloud
                  className="size-12 text-muted-foreground mb-2 mt-10"
                  aria-hidden="true"
                />
                <span className="text-base font-semibold">
                  {file ? file.name : 'Drag & Drop File here'}
                </span>
                <span className="text-xs text-muted-foreground">
                  {file ? formatFileSize(file.size) : 'Or click to select.'}
                </span>
                <span
                  className={cn(
                    'text-xs text-muted-foreground font-semibold pt-8 pb-2',
                    file && 'invisible',
                  )}
                >
                  PDF only, up to 10MB.
                </span>
              </div>
              <input {...getInputProps({ id: 'invoice-file' })} />
            </Field>

            <FieldError>{hasError ? 'Something went wrong. Please try again.' : null}</FieldError>
          </FieldGroup>

          <DialogFooter className="pt-4 border-t-0 bg-background">
            <DialogClose render={<Button type="button" variant="outline" />}>Cancel</DialogClose>
            <Button type="submit" disabled={!file || isSubmitting}>
              Upload
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
