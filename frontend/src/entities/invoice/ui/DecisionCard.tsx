import { Badge } from '@/shared/ui/badge'
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/shared/ui/card'

import type { DecisionView } from '../model/types'

export interface DecisionCardProps {
  decision: DecisionView
}

export function DecisionCard({ decision }: DecisionCardProps) {
  const decidedAt = new Date(decision.decided_at)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Decision</CardTitle>
        <CardAction>
          <Badge variant={decision.outcome === 'approved' ? 'secondary' : 'destructive'}>
            {decision.outcome === 'approved' ? 'Approved' : 'Rejected'}
          </Badge>
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-2 text-sm">
        <p>{decision.reason}</p>
        <p className="text-muted-foreground">
          Decided by {decision.decided_by} on{' '}
          {decidedAt.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
          })}
        </p>
      </CardContent>
    </Card>
  )
}
