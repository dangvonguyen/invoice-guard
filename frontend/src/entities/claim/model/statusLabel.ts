import type { ClaimStatus } from './types';

const STATUS_LABELS: Record<ClaimStatus, string> = {
  submitted: 'Submitted',
  under_review: 'Under Review',
  returned_for_info: 'Needs Your Input',
  approved: 'Approved',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn',
};

export function claimStatusLabel(status: ClaimStatus): string {
  return STATUS_LABELS[status];
}

const STATUS_BADGE_CLASSES: Record<ClaimStatus, string> = {
  submitted: 'bg-slate-100 text-slate-700 dark:bg-slate-500/15 dark:text-slate-300',
  under_review: 'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300',
  returned_for_info: 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300',
  approved: 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300',
  rejected: 'bg-red-100 text-red-800 dark:bg-red-500/20 dark:text-red-200',
  withdrawn: 'bg-slate-100 text-slate-600 dark:bg-slate-500/15 dark:text-slate-400',
};

export function claimStatusBadgeClassName(status: ClaimStatus): string {
  return STATUS_BADGE_CLASSES[status];
}

const STATUS_NOTICES: Record<ClaimStatus, string> = {
  submitted: 'Waiting for a reviewer to pick this up.',
  under_review: 'Finance is reviewing this claim.',
  returned_for_info: 'Please review the details below and resubmit.',
  approved: 'This claim has been approved.',
  rejected: 'This claim has been rejected.',
  withdrawn: 'You withdrew this claim.',
};

export function claimStatusNotice(status: ClaimStatus): string {
  return STATUS_NOTICES[status];
}

const STATUS_NOTICE_CLASSES: Record<ClaimStatus, string> = {
  submitted: 'bg-slate-50 text-slate-700 dark:bg-slate-500/10 dark:text-slate-300',
  under_review: 'bg-amber-50 text-amber-800 dark:bg-amber-500/10 dark:text-amber-300',
  returned_for_info: 'bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-300 font-[350]',
  approved: 'bg-green-50 text-green-700 dark:bg-green-500/10 dark:text-green-300',
  rejected: 'bg-red-50 text-red-800 dark:bg-red-500/10 dark:text-red-200',
  withdrawn: 'bg-slate-50 text-slate-600 dark:bg-slate-500/10 dark:text-slate-400',
};

export function claimStatusNoticeClassName(status: ClaimStatus): string {
  return STATUS_NOTICE_CLASSES[status];
}
