import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';

import type { EmployeeIdentity } from '../model/types';

export interface EmployeeIdentityBlockProps {
  employee: EmployeeIdentity;
}

export function EmployeeIdentityBlock({ employee }: EmployeeIdentityBlockProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Submitted by</CardTitle>
      </CardHeader>
      <CardContent className="text-sm">
        <p className="font-medium">{employee.name}</p>
        <p className="text-muted-foreground">{employee.email}</p>
      </CardContent>
    </Card>
  );
}
