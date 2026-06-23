import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Field, Input, Textarea } from '@/components/ui/Input';
import { useStore } from '@/store/store';
import { uid } from '@/lib/ids';
import { PERMISSION_CATEGORIES, buildEmptyPermissions, buildPermissionsForPreset } from '@/lib/permissions';
import type { ID, RoleMember, RolePermission } from '@/lib/types';
import type { DefaultRolePreset } from '@/lib/permissions';

interface Props {
  open: boolean;
  onClose: () => void;
  centreId: ID;
}

type Step = 'info' | 'permissions';

const PRESETS: { key: DefaultRolePreset | 'custom'; label: string }[] = [
  { key: 'Manager', label: 'Manager (default)' },
  { key: 'Teacher', label: 'Teacher (default)' },
  { key: 'Parent', label: 'Parent (default)' },
  { key: 'custom', label: 'Custom (blank)' },
];

export function AddRoleModal({ open, onClose, centreId }: Props) {
  const { addRole } = useStore();
  const [step, setStep] = useState<Step>('info');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [preset, setPreset] = useState<DefaultRolePreset | 'custom'>('custom');
  const [memberName, setMemberName] = useState('');
  const [memberEmail, setMemberEmail] = useState('');
  const [members, setMembers] = useState<RoleMember[]>([]);
  const [permissions, setPermissions] = useState<RolePermission[]>(buildEmptyPermissions());

  function reset() {
    setStep('info');
    setName('');
    setDescription('');
    setPreset('custom');
    setMemberName('');
    setMemberEmail('');
    setMembers([]);
    setPermissions(buildEmptyPermissions());
  }

  function handlePresetChange(p: DefaultRolePreset | 'custom') {
    setPreset(p);
    if (p !== 'custom') {
      setPermissions(buildPermissionsForPreset(p));
    } else {
      setPermissions(buildEmptyPermissions());
    }
  }

  function handleAddMember() {
    if (!memberName.trim() || !memberEmail.trim()) return;
    setMembers([...members, { id: uid('rm'), name: memberName.trim(), email: memberEmail.trim() }]);
    setMemberName('');
    setMemberEmail('');
  }

  function handleRemoveMember(id: string) {
    setMembers(members.filter((m) => m.id !== id));
  }

  function handleEditToggle(key: string, currentEdit: boolean) {
    setPermissions((prev) =>
      prev.map((p) =>
        p.key === key
          ? { ...p, edit: !currentEdit, visible: !currentEdit ? true : p.visible }
          : p
      )
    );
  }

  function handleVisibleToggle(key: string, currentVisible: boolean) {
    setPermissions((prev) =>
      prev.map((p) =>
        p.key === key
          ? { ...p, visible: !currentVisible, edit: !currentVisible ? p.edit : false }
          : p
      )
    );
  }

  function handleSubmit() {
    if (!name.trim()) return;
    addRole({
      id: uid('role'),
      centreId,
      name: name.trim(),
      description: description.trim(),
      permissions,
      members,
    });
    reset();
    onClose();
  }

  const canProceed = name.trim().length > 0;

  return (
    <Modal
      open={open}
      onClose={() => { reset(); onClose(); }}
      title={step === 'info' ? 'Add new role' : `Permissions — ${name}`}
      size="lg"
      footer={
        step === 'info' ? (
          <>
            <Button onClick={() => { reset(); onClose(); }}>Cancel</Button>
            <Button variant="primary" disabled={!canProceed} onClick={() => setStep('permissions')}>
              Next: Set permissions →
            </Button>
          </>
        ) : (
          <>
            <Button onClick={() => setStep('info')}>← Back</Button>
            <Button variant="primary" onClick={handleSubmit}>
              Create role
            </Button>
          </>
        )
      }
    >
      {step === 'info' && (
        <div className="space-y-4">
          <Field label="Role name" required>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Staff, Receptionist..."
            />
          </Field>

          <Field label="Description">
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of this role's responsibilities"
              rows={2}
            />
          </Field>

          <Field label="Start from preset">
            <div className="flex flex-wrap gap-2 mt-1">
              {PRESETS.map((p) => (
                <button
                  key={p.key}
                  type="button"
                  onClick={() => handlePresetChange(p.key)}
                  className={[
                    'px-3 py-1.5 rounded-md text-xs font-medium border',
                    preset === p.key
                      ? 'bg-olive/15 border-olive text-olive'
                      : 'border-border text-text-muted hover:border-olive hover:text-olive',
                  ].join(' ')}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </Field>

          <div className="border-t border-border pt-4">
            <div className="text-sm font-medium mb-2">Members</div>
            <p className="text-xs text-text-muted mb-3">
              Add people who will have this role at this centre.
            </p>
            <div className="flex gap-2 items-end">
              <div className="flex-1">
                <Field label="Name">
                  <Input
                    value={memberName}
                    onChange={(e) => setMemberName(e.target.value)}
                    placeholder="Full name"
                  />
                </Field>
              </div>
              <div className="flex-1">
                <Field label="Email">
                  <Input
                    value={memberEmail}
                    onChange={(e) => setMemberEmail(e.target.value)}
                    placeholder="email@example.com"
                    type="email"
                  />
                </Field>
              </div>
              <Button onClick={handleAddMember} disabled={!memberName.trim() || !memberEmail.trim()}>
                Add
              </Button>
            </div>
            {members.length > 0 && (
              <div className="mt-3 space-y-1">
                {members.map((m) => (
                  <div key={m.id} className="flex items-center justify-between px-3 py-1.5 bg-beige rounded-md text-sm">
                    <span>{m.name} <span className="text-text-muted">({m.email})</span></span>
                    <button
                      onClick={() => handleRemoveMember(m.id)}
                      className="text-text-dim hover:text-danger text-xs"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {step === 'permissions' && (
        <div className="max-h-[60vh] overflow-y-auto -mx-5 px-5">
          <p className="text-xs text-text-muted mb-4">
            Tick permissions for this role. Checking Edit automatically enables View.
          </p>
          {PERMISSION_CATEGORIES.map((cat) => (
            <div key={cat.name} className="mb-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-olive bg-beige/50 px-3 py-1.5 rounded -mx-1 mb-2">
                {cat.name}
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[10px] uppercase text-text-dim">
                    <th className="text-left py-1 font-medium">Permission</th>
                    <th className="w-16 text-center py-1 font-medium">Edit</th>
                    <th className="w-16 text-center py-1 font-medium">View</th>
                  </tr>
                </thead>
                <tbody>
                  {cat.permissions.map((perm) => {
                    const rp = permissions.find((p) => p.key === perm.key);
                    const edit = rp?.edit ?? false;
                    const visible = rp?.visible ?? false;
                    return (
                      <tr key={perm.key} className="border-b border-border/30">
                        <td className="py-1.5 text-text">{perm.label}</td>
                        <td className="text-center">
                          <input
                            type="checkbox"
                            checked={edit}
                            onChange={() => handleEditToggle(perm.key, edit)}
                            className="w-4 h-4 accent-olive cursor-pointer"
                          />
                        </td>
                        <td className="text-center">
                          <input
                            type="checkbox"
                            checked={visible}
                            onChange={() => handleVisibleToggle(perm.key, visible)}
                            className="w-4 h-4 accent-olive cursor-pointer"
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}
