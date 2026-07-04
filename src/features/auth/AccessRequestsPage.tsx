import { useState, useCallback, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import type { AccessRequest } from './AuthContext';
import { Button } from '@/components/ui/Button';
import { PageHeader } from '@/components/ui/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function statusColor(status: string): 'gold' | 'green' | 'danger' {
  if (status === 'pending') return 'gold';
  if (status === 'approved') return 'green';
  return 'danger';
}

export function AccessRequestsPage() {
  const { isRoot, getAccessRequests, approveRequest, rejectRequest } = useAuth();
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchRequests = useCallback(async () => {
    try {
      setError(null);
      const data = await getAccessRequests();
      setRequests(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load requests.');
    } finally {
      setLoading(false);
    }
  }, [getAccessRequests]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  if (!isRoot) {
    return <Navigate to="/admin" replace />;
  }

  const pendingRequests = requests.filter((r) => r.status === 'pending');
  const processedRequests = requests.filter((r) => r.status !== 'pending');

  async function handleApprove(req: AccessRequest) {
    setActionLoading(req.id);
    try {
      await approveRequest(req.id);
      await fetchRequests();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve request.');
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReject(req: AccessRequest) {
    setActionLoading(req.id);
    try {
      await rejectRequest(req.id);
      await fetchRequests();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject request.');
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Access Requests"
        subtitle="Manage admin access requests to the portal"
      />

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-danger/10 border border-danger/30 text-danger text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <svg className="animate-spin h-6 w-6 text-olive" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
      ) : (
        <>
          {/* Pending Requests */}
          <section className="mb-8">
            <h2 className="text-base font-semibold text-charcoal mb-3 flex items-center gap-2">
              Pending Requests
              {pendingRequests.length > 0 && (
                <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-amber-500 rounded-full">
                  {pendingRequests.length}
                </span>
              )}
            </h2>

            {pendingRequests.length === 0 ? (
              <EmptyState
                title="No pending requests"
                description="All access requests have been processed."
              />
            ) : (
              <div className="space-y-3">
                {pendingRequests.map((req) => (
                  <div
                    key={req.id}
                    className="card p-4 flex items-center justify-between gap-4"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-olive/10 flex items-center justify-center text-sm font-semibold text-olive shrink-0">
                          {req.name.charAt(0).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-charcoal truncate">{req.name}</p>
                          <p className="text-xs text-text-muted truncate">{req.email}</p>
                        </div>
                      </div>
                      <p className="text-xs text-text-dim mt-1 ml-10">
                        Requested {formatDate(req.requestedAt)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Button
                        variant="primary"
                        onClick={() => handleApprove(req)}
                        disabled={actionLoading === req.id}
                        className="text-xs px-3 py-1.5"
                      >
                        {actionLoading === req.id ? '...' : 'Approve'}
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={() => handleReject(req)}
                        disabled={actionLoading === req.id}
                        className="text-xs px-3 py-1.5 text-danger hover:bg-danger/10"
                      >
                        Reject
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Processed Requests */}
          {processedRequests.length > 0 && (
            <section>
              <h2 className="text-base font-semibold text-charcoal mb-3">
                Processed Requests
              </h2>
              <div className="space-y-2">
                {processedRequests.map((req) => (
                  <div
                    key={req.id}
                    className="card p-3 flex items-center justify-between gap-4"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center text-xs font-semibold text-text-muted shrink-0">
                        {req.name.charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm text-charcoal truncate">{req.name}</p>
                        <p className="text-xs text-text-muted truncate">{req.email}</p>
                      </div>
                    </div>
                    <Badge tone={statusColor(req.status)}>
                      {req.status === 'approved' ? 'Approved' : 'Rejected'}
                    </Badge>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
