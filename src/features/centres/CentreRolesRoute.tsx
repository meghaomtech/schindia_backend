import { useMemo, useState } from 'react';
import { useStore } from '@/store/store';
import { useCentreOutlet } from './useCentreOutlet';
import { Tabs } from '@/components/ui/Tabs';
import { PERMISSION_CATEGORIES } from '@/lib/permissions';
import { Button } from '@/components/ui/Button';
import { TrashIcon, PlusIcon, MailIcon, UserIcon } from '@/components/ui/icons';
import { AddRoleModal } from './AddRoleModal';
import { AssignPersonModal } from './AssignPersonModal';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import type { Role } from '@/lib/types';

type ViewTab = 'people' | 'permissions';

const TAB_ITEMS: { key: ViewTab; label: string }[] = [
  { key: 'people', label: 'People' },
  { key: 'permissions', label: 'Permissions matrix' },
];

export function CentreRolesRoute() {
  const { centre } = useCentreOutlet();
  const { roles, updateRolePermission, deleteRole, removeRoleMember } = useStore();
  const [showAddRole, setShowAddRole] = useState(false);
  const [showAssignPerson, setShowAssignPerson] = useState(false);
  const [assignToRoleId, setAssignToRoleId] = useState<string | undefined>(undefined);
  const [expandedRole, setExpandedRole] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ViewTab>('people');
  const [peopleSearch, setPeopleSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');

  const centreRoles = roles.filter((r) => r.centreId === centre.id);

  const allPeople = useMemo(() => {
    return centreRoles.flatMap((role) =>
      role.members.map((m) => ({
        ...m,
        roleId: role.id,
        roleName: role.name,
        roleDescription: role.description,
        permissionCount: role.permissions.filter((p) => p.edit || p.visible).length,
      }))
    );
  }, [centreRoles]);

  const filteredPeople = useMemo(() => {
    let list = allPeople;
    if (roleFilter !== 'all') {
      list = list.filter((p) => p.roleId === roleFilter);
    }
    if (peopleSearch.trim()) {
      const q = peopleSearch.toLowerCase();
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.email.toLowerCase().includes(q) ||
          p.roleName.toLowerCase().includes(q)
      );
    }
    return list;
  }, [allPeople, roleFilter, peopleSearch]);

  function handleEditToggle(roleId: string, permKey: string, currentEdit: boolean) {
    if (!currentEdit) {
      updateRolePermission(roleId, permKey, { edit: true, visible: true });
    } else {
      updateRolePermission(roleId, permKey, { edit: false });
    }
  }

  function handleVisibleToggle(roleId: string, permKey: string, currentVisible: boolean) {
    if (!currentVisible) {
      updateRolePermission(roleId, permKey, { visible: true });
    } else {
      updateRolePermission(roleId, permKey, { visible: false, edit: false });
    }
  }

  function handleDeleteRole(role: Role) {
    const hasMembers = role.members.length > 0;
    const msg = hasMembers
      ? `"${role.name}" has ${role.members.length} member(s) assigned. Are you sure you want to delete this role?`
      : `Are you sure you want to delete the "${role.name}" role?`;
    if (confirm(msg)) {
      deleteRole(role.id);
    }
  }

  function handleRemoveMember(roleId: string, memberId: string, memberName: string) {
    if (confirm(`Remove ${memberName} from this role?`)) {
      removeRoleMember(roleId, memberId);
    }
  }

  const roleBadgeTone = (roleName: string) => {
    switch (roleName.toLowerCase()) {
      case 'manager': return 'olive' as const;
      case 'teacher': return 'beige' as const;
      case 'parent': return 'gold' as const;
      default: return 'beige' as const;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Roles & Permissions</h2>
          <p className="text-sm text-text-muted">
            Manage people and configure permissions for {centre.name}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => { setAssignToRoleId(undefined); setShowAssignPerson(true); }}>
            <UserIcon width={16} height={16} /> Add person
          </Button>
          <Button variant="primary" onClick={() => setShowAddRole(true)}>
            <PlusIcon width={16} height={16} /> Add role
          </Button>
        </div>
      </div>

      <Tabs<ViewTab> items={TAB_ITEMS} active={activeTab} onChange={setActiveTab} />

      {activeTab === 'people' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex-1 max-w-sm">
              <Input
                value={peopleSearch}
                onChange={(e) => setPeopleSearch(e.target.value)}
                placeholder="Search by name, email, or role..."
              />
            </div>
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="input max-w-[180px]"
            >
              <option value="all">All roles</option>
              {centreRoles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.members.length})
                </option>
              ))}
            </select>
          </div>

          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="card p-3 text-center">
              <div className="text-2xl font-bold text-olive">{allPeople.length}</div>
              <div className="text-xs text-text-muted">Total people</div>
            </div>
            {centreRoles.map((r) => (
              <div key={r.id} className="card p-3 text-center">
                <div className="text-2xl font-bold text-text">{r.members.length}</div>
                <div className="text-xs text-text-muted">{r.name}s</div>
              </div>
            ))}
          </div>

          {/* People list */}
          {filteredPeople.length === 0 ? (
            <div className="card p-8 text-center text-text-muted space-y-3">
              <div>
                {allPeople.length === 0
                  ? 'No people assigned to roles yet.'
                  : 'No results match your search.'}
              </div>
              {centreRoles.length > 0 && (
                <Button onClick={() => { setAssignToRoleId(undefined); setShowAssignPerson(true); }}>
                  <UserIcon width={16} height={16} /> Assign a person to a role
                </Button>
              )}
            </div>
          ) : (
            <div className="card overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-bg-elev">
                    <th className="text-left px-4 py-3 font-medium text-text-muted">Person</th>
                    <th className="text-left px-4 py-3 font-medium text-text-muted">Email</th>
                    <th className="text-left px-4 py-3 font-medium text-text-muted">Role</th>
                    <th className="text-left px-4 py-3 font-medium text-text-muted">Permissions</th>
                    <th className="text-right px-4 py-3 font-medium text-text-muted">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPeople.map((person) => (
                    <tr key={`${person.roleId}-${person.id}`} className="border-b border-border/50 hover:bg-beige/30">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <span className="w-8 h-8 rounded-full bg-olive/10 text-olive inline-flex items-center justify-center">
                            <UserIcon width={14} height={14} />
                          </span>
                          <span className="font-medium text-text">{person.name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5 text-text-muted">
                          <MailIcon width={13} height={13} />
                          <span>{person.email}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <Badge tone={roleBadgeTone(person.roleName)}>{person.roleName}</Badge>
                      </td>
                      <td className="px-4 py-3 text-text-muted">
                        {person.permissionCount} active
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleRemoveMember(person.roleId, person.id, person.name)}
                          className="text-xs text-text-dim hover:text-danger"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'permissions' && (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-bg-elev">
                  <th className="text-left px-4 py-3 font-medium text-text-muted min-w-[280px] sticky left-0 bg-bg-elev z-10">
                    Permission
                  </th>
                  {centreRoles.map((role) => (
                    <th key={role.id} colSpan={2} className="px-2 py-3 text-center border-l border-border">
                      <div className="flex items-center justify-center gap-2">
                        <span className="font-semibold text-text">{role.name}</span>
                        <button
                          onClick={() => handleDeleteRole(role)}
                          className="text-text-dim hover:text-danger p-0.5 rounded"
                          title={`Delete ${role.name}`}
                        >
                          <TrashIcon width={14} height={14} />
                        </button>
                      </div>
                      <button
                        onClick={() => setExpandedRole(expandedRole === role.id ? null : role.id)}
                        className="text-[10px] text-text-dim hover:text-olive mt-0.5"
                      >
                        {role.members.length} member{role.members.length !== 1 ? 's' : ''} ▾
                      </button>
                      <button
                        onClick={() => { setAssignToRoleId(role.id); setShowAssignPerson(true); }}
                        className="text-[10px] text-olive hover:text-olive/80 mt-0.5 font-medium"
                      >
                        + Add person
                      </button>
                      {expandedRole === role.id && role.members.length > 0 && (
                        <div className="mt-1 text-[10px] text-text-muted font-normal space-y-0.5">
                          {role.members.map((m) => (
                            <div key={m.id}>{m.name}</div>
                          ))}
                        </div>
                      )}
                    </th>
                  ))}
                </tr>
                <tr className="border-b border-border bg-bg-elev">
                  <th className="sticky left-0 bg-bg-elev z-10"></th>
                  {centreRoles.map((role) => (
                    <Fragment key={role.id}>
                      <th className="px-2 py-1.5 text-[10px] uppercase tracking-wide text-text-dim font-medium border-l border-border">
                        Edit
                      </th>
                      <th className="px-2 py-1.5 text-[10px] uppercase tracking-wide text-text-dim font-medium">
                        View
                      </th>
                    </Fragment>
                  ))}
                </tr>
              </thead>
              <tbody>
                {PERMISSION_CATEGORIES.map((cat) => (
                  <Fragment key={cat.name}>
                    <tr className="bg-beige/50">
                      <td
                        colSpan={1 + centreRoles.length * 2}
                        className="px-4 py-2 font-semibold text-olive text-xs uppercase tracking-wide sticky left-0"
                      >
                        {cat.name}
                      </td>
                    </tr>
                    {cat.permissions.map((perm) => (
                      <tr key={perm.key} className="border-b border-border/50 hover:bg-beige/30">
                        <td className="px-4 py-2 text-text sticky left-0 bg-white">
                          {perm.label}
                        </td>
                        {centreRoles.map((role) => {
                          const rp = role.permissions.find((p) => p.key === perm.key);
                          const edit = rp?.edit ?? false;
                          const visible = rp?.visible ?? false;
                          return (
                            <Fragment key={role.id}>
                              <td className="px-2 py-2 text-center border-l border-border/50">
                                <input
                                  type="checkbox"
                                  checked={edit}
                                  onChange={() => handleEditToggle(role.id, perm.key, edit)}
                                  className="w-4 h-4 rounded border-border text-olive accent-olive cursor-pointer"
                                />
                              </td>
                              <td className="px-2 py-2 text-center">
                                <input
                                  type="checkbox"
                                  checked={visible}
                                  onChange={() => handleVisibleToggle(role.id, perm.key, visible)}
                                  className="w-4 h-4 rounded border-border text-olive accent-olive cursor-pointer"
                                />
                              </td>
                            </Fragment>
                          );
                        })}
                      </tr>
                    ))}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <AddRoleModal
        open={showAddRole}
        onClose={() => setShowAddRole(false)}
        centreId={centre.id}
      />

      <AssignPersonModal
        open={showAssignPerson}
        onClose={() => setShowAssignPerson(false)}
        centreId={centre.id}
        preselectedRoleId={assignToRoleId}
      />
    </div>
  );
}

function Fragment({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
