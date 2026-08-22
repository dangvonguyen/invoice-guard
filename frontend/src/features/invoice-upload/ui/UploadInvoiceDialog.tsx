import { useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useFetcher } from 'react-router';
import { UploadCloud } from 'lucide-react';

import type { UploadedInvoice } from '@/entities/invoice';
import { formatFileSize } from '@/shared/lib/formatFileSize';
import { cn } from '@/shared/lib/utils';
import { Button } from '@/shared/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/shared/ui/dialog';
import { Field, FieldError, FieldGroup } from '@/shared/ui/field';

export function UploadInvoiceDialog() {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [hasError, setHasError] = useState(false);
  const fetcher = useFetcher<UploadedInvoice | null>();

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    onDrop: ([dropped]) => {
      if (dropped) setFile(dropped);
    },
  });

  function handleOpenChange(nextOpen: boolean): void {
    setOpen(nextOpen);
    if (nextOpen) {
      setFile(null);
      setHasError(false);
    }
  }

  useEffect(() => {
    if (fetcher.state !== 'idle' || fetcher.data === undefined) return;

    if (fetcher.data === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setHasError(true);
    } else {
      setOpen(false);
    }
  }, [fetcher.state, fetcher.data]);

  const isSubmitting = fetcher.state !== 'idle';

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger render={<Button />}>Upload Invoice</DialogTrigger>
      <DialogContent>
        <fetcher.Form method="post" encType="multipart/form-data">
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
              <input {...getInputProps({ id: 'invoice-file', name: 'file' })} />
            </Field>

            <FieldError>{hasError ? 'Something went wrong. Please try again.' : null}</FieldError>
          </FieldGroup>

          <DialogFooter className="pt-4 border-t-0 bg-background">
            <DialogClose render={<Button type="button" variant="outline" />}>Cancel</DialogClose>
            <Button type="submit" disabled={!file || isSubmitting}>
              Upload
            </Button>
          </DialogFooter>
        </fetcher.Form>
      </DialogContent>
    </Dialog>
  );
}
