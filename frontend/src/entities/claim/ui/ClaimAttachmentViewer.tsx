import { useEffect } from 'react';

import type { ClaimAttachment } from '../model/types';

export interface ClaimAttachmentViewerProps {
  url: string;
  attachment: ClaimAttachment;
}

export function ClaimAttachmentViewer({ url, attachment }: ClaimAttachmentViewerProps) {
  useEffect(() => {
    return () => URL.revokeObjectURL(url);
  }, [url]);

  return attachment.contentType.startsWith('image/') ? (
    <img
      src={url}
      alt={`Receipt: ${attachment.filename}`}
      className="max-h-112 w-full rounded-sm bg-muted object-contain"
    />
  ) : (
    <iframe
      src={url}
      title={`Receipt: ${attachment.filename}`}
      className="h-112 w-full rounded-sm bg-muted"
    />
  );
}
