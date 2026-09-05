import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

import { Button } from '@/shared/ui/button';

import { getClaimAttachmentBlob } from '../api/getClaimAttachment';
import type { ClaimAttachment } from '../model/types';

export interface ClaimAttachmentViewerProps {
  claimId: string;
  attachment: ClaimAttachment;
}

type Result =
  { attempt: number; status: 'error' } | { attempt: number; status: 'loaded'; objectUrl: string };

export function ClaimAttachmentViewer({ claimId, attachment }: ClaimAttachmentViewerProps) {
  const [result, setResult] = useState<Result | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;

    getClaimAttachmentBlob(claimId)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setResult({ attempt, status: 'loaded', objectUrl });
      })
      .catch(() => {
        if (!cancelled) setResult({ attempt, status: 'error' });
      });

    return () => {
      cancelled = true;
      if (objectUrl !== null) URL.revokeObjectURL(objectUrl);
    };
  }, [claimId, attempt]);

  const isLoading = result?.attempt !== attempt;

  if (isLoading) {
    return (
      <div
        role="status"
        className="flex aspect-4/3 items-center justify-center rounded-xl bg-muted"
      >
        <Loader2 className="size-6 animate-spin text-muted-foreground" aria-hidden="true" />
        <span className="sr-only">Loading receipt…</span>
      </div>
    );
  }

  if (result.status === 'error') {
    return (
      <div className="flex aspect-4/3 flex-col items-center justify-center gap-3 rounded-xl bg-muted text-sm text-muted-foreground">
        <p>Couldn't load the receipt.</p>
        <Button variant="outline" size="sm" onClick={() => setAttempt((n) => n + 1)}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <>
      {attachment.contentType.startsWith('image/') ? (
        <img
          src={result.objectUrl}
          alt={`Receipt: ${attachment.filename}`}
          className="max-h-112 w-full rounded-sm bg-muted object-contain"
        />
      ) : (
        <iframe
          src={result.objectUrl}
          title={`Receipt: ${attachment.filename}`}
          className="h-112 w-full rounded-sm bg-muted"
        />
      )}
    </>
  );
}
