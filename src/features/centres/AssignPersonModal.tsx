import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Field, Input, Select } from '@/components/ui/Input';
import { useStore } from '@/store/store';
import { uid } from '@/lib/ids';
import type { ID } from '@/lib/types';

interface Props {
  open: boolean;
  onClose: () => void;
  centreId: ID;
  preselectedRoleId?: ID;
}

export function AssignPersonModal({ open, onClose, centreId, preselectedRoleId }: Props) {
  const { roles, addRoleMember } = useStore();
  const centreRoles = roles.filter((r) => r.centreId === centreId);

  const [roleId, setRoleId] = useState(preselectedRoleId ?? centreRoles[0]?.id ?? '');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');

  function reset() {
    setRoleId(preselectedRoleId ?? centreRoles[0]?.id ?? '');
    setName('');
    setEmail('');
  }

  function handleSubmit() {
    if (!roleId || !name.trim() || !email.trim()) return;
    addRoleMember(roleId, { id: uid('rm'), name: name.trim(), email: email.trim() });
    reset();
    onClose();
  }

  const selectedRole = centreRoles.find((r) => r.id === roleId);

  return (
    <Modal
      open={open}
      onClose={() => { reset(); onClose(); }}
      title="Assign person to role"
      size="sm"
      footer={
        <>
          <Button onClick={() => { reset(); onClose(); }}>Cancel</Button>
          <Button
            variant="primary"
            disabled={!roleId || !name.trim() || !email.trim()}
            onClick={handleSubmit}
          >
            Assign
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Role" required>
          <Select
            value={roleId}
            onChange={(e) => setRoleId(e.target.value)}
          >
            {centreRoles.length === 0 ? (
              <option value="">No roles available</option>
            ) : (
              centreRoles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.members.length} members)
                </option>
              ))
            )}
          </Select>
        </Field>

        {selectedRole && (
          <div className="text-xs text-text-muted bg-beige/50 rounded-md px-3 py-2">
            {selectedRole.description || `Members with this role get ${selectedRole.permissions.filter(p => p.edit || p.visible).length} active permissions.`}
          </div>
        )}

        <Field label="Full name" required>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. John Smith"
          />
        </Field>

        <Field label="Email" required>
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="e.g. john@example.com"
          />
        </Field>
      </div>
    </Modal>
  );
}
