import { SubmitClaimForm } from '@/features/submit-claim';

export function ClaimNewPage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-5 py-10">
      <h1 className="text-2xl font-semibold">New claim</h1>
      <SubmitClaimForm />
    </div>
  );
}
