export interface PermissionDef {
  key: string;
  label: string;
  category: string;
}

export interface PermissionCategory {
  name: string;
  permissions: PermissionDef[];
}

export const PERMISSION_CATEGORIES: PermissionCategory[] = [
  {
    name: 'Children',
    permissions: [
      { key: 'children.view_info', label: 'View child information', category: 'Children' },
      { key: 'children.register_status', label: 'Register child status', category: 'Children' },
      { key: 'children.view_private_info', label: 'View child private info', category: 'Children' },
      { key: 'children.transfer_sites', label: 'Transfer children across sites', category: 'Children' },
      { key: 'children.sign_in_out', label: 'Sign children in and out', category: 'Children' },
      { key: 'children.add', label: 'Add children', category: 'Children' },
      { key: 'children.sibling_linking', label: 'Manage sibling linking', category: 'Children' },
      { key: 'children.manage_notes', label: 'Manage child notes', category: 'Children' },
      { key: 'children.view_notes', label: 'View child notes', category: 'Children' },
      { key: 'children.manage_contacts', label: 'Manage contacts', category: 'Children' },
      { key: 'children.manage_session_requests', label: 'Manage children session requests (leave or reschedule)', category: 'Children' },
    ],
  },
  {
    name: 'Staff',
    permissions: [
      { key: 'staff.access_remotely', label: 'Access app remotely', category: 'Staff' },
      { key: 'staff.add', label: 'Add staff', category: 'Staff' },
      { key: 'staff.view_profiles', label: 'View staff profiles', category: 'Staff' },
      { key: 'staff.edit_profiles', label: 'Edit staff profiles', category: 'Staff' },
      { key: 'staff.edit_profile_pictures', label: 'Edit staff profile pictures', category: 'Staff' },
      { key: 'staff.manage_personal_details', label: 'Manage staff personal details', category: 'Staff' },
      { key: 'staff.view_contract_info', label: 'View staff contract info', category: 'Staff' },
      { key: 'staff.manage_contract_info', label: 'Manage staff contract info', category: 'Staff' },
      { key: 'staff.view_todos', label: 'View all staff to-dos', category: 'Staff' },
      { key: 'staff.manage_leave', label: 'Manage staff leave', category: 'Staff' },
      { key: 'staff.view_absence_statuses', label: 'View staff absence statuses', category: 'Staff' },
      { key: 'staff.manage_absences', label: 'Manage staff absences', category: 'Staff' },
      { key: 'staff.view_absences', label: 'View staff absences', category: 'Staff' },
      { key: 'staff.approve_absence_requests', label: 'Approve staff absence requests', category: 'Staff' },
      { key: 'staff.manage_own_sign_in', label: 'Manage own sign in', category: 'Staff' },
      { key: 'staff.edit_own_attendance', label: 'Edit own attendance', category: 'Staff' },
      { key: 'staff.view_all_attendance', label: 'View all staff attendance', category: 'Staff' },
      { key: 'staff.edit_all_attendance', label: 'Edit all staff attendance', category: 'Staff' },
    ],
  },
  {
    name: 'Communication & Events',
    permissions: [
      { key: 'comms.view_calendar', label: 'View site calendar', category: 'Communication & Events' },
      { key: 'comms.add_calendar_events', label: 'Add calendar events', category: 'Communication & Events' },
      { key: 'comms.view_news_feed', label: 'View news feed (all)', category: 'Communication & Events' },
      { key: 'comms.send_news_posts', label: 'Send news feed posts', category: 'Communication & Events' },
      { key: 'comms.edit_all_posts', label: "Edit all users' posts", category: 'Communication & Events' },
      { key: 'comms.manage_classroom_messages', label: 'Manage classroom messages', category: 'Communication & Events' },
      { key: 'comms.send_private_messages', label: 'Send private messages to parents', category: 'Communication & Events' },
      { key: 'comms.send_org_messages', label: 'Send organisation messages', category: 'Communication & Events' },
    ],
  },
  {
    name: 'Registration & Forms',
    permissions: [
      { key: 'registration.manage_contracts', label: 'Manage contracts', category: 'Registration & Forms' },
      { key: 'registration.view_contracts', label: 'View contracts', category: 'Registration & Forms' },
      { key: 'registration.delete_contracts', label: 'Delete contracts', category: 'Registration & Forms' },
    ],
  },
  {
    name: 'Learning',
    permissions: [
      { key: 'learning.manage_observations', label: 'Manage observations', category: 'Learning' },
      { key: 'learning.view_observations', label: 'View observations', category: 'Learning' },
      { key: 'learning.review_send_observations', label: 'Review and send observations', category: 'Learning' },
      { key: 'learning.review_observations', label: 'Review observations', category: 'Learning' },
      { key: 'learning.manage_activity_library', label: 'Manage activity library', category: 'Learning' },
      { key: 'learning.manage_activity_plans', label: 'Manage activity plans', category: 'Learning' },
      { key: 'learning.view_activity_plans', label: 'View activity plans', category: 'Learning' },
    ],
  },
  {
    name: 'Finances',
    permissions: [
      { key: 'finance.configure_payments', label: 'Configure in-app payments', category: 'Finances' },
      { key: 'finance.configure_settings', label: 'Configure finance settings', category: 'Finances' },
      { key: 'finance.manage_child_plans', label: 'Manage child plans', category: 'Finances' },
      { key: 'finance.view_child_plans', label: 'View child plans', category: 'Finances' },
      { key: 'finance.manage_plans_basic', label: 'Manage plans (basic)', category: 'Finances' },
      { key: 'finance.manage_child_purchases', label: 'Manage child purchases', category: 'Finances' },
      { key: 'finance.override_invoicing_profile', label: 'Override invoicing profile', category: 'Finances' },
      { key: 'finance.manage_funding', label: 'Manage funding', category: 'Finances' },
      { key: 'finance.manage_child_discounts', label: 'Manage child discounts', category: 'Finances' },
      { key: 'finance.manage_child_surcharges', label: 'Manage child surcharges', category: 'Finances' },
      { key: 'finance.manage_invoices', label: 'Manage invoices', category: 'Finances' },
      { key: 'finance.view_invoices', label: 'View invoices', category: 'Finances' },
      { key: 'finance.manage_invoices_basic', label: 'Manage invoices (basic)', category: 'Finances' },
      { key: 'finance.cancel_invoices', label: 'Cancel invoices', category: 'Finances' },
      { key: 'finance.edit_billing_details', label: 'Edit billing details', category: 'Finances' },
      { key: 'finance.manage_bill_payer_accounts', label: 'Manage bill payer accounts', category: 'Finances' },
      { key: 'finance.manage_bill_payer_payments', label: 'Manage bill payer payments', category: 'Finances' },
      { key: 'finance.manage_bill_payer_surcharges', label: 'Manage bill payer surcharges', category: 'Finances' },
      { key: 'finance.manage_bill_payer_credits', label: 'Manage bill payer credits', category: 'Finances' },
      { key: 'finance.manage_bill_payer_tags', label: 'Manage bill payer tags', category: 'Finances' },
      { key: 'finance.assign_bill_payer_tags', label: 'Assign bill payer tags', category: 'Finances' },
      { key: 'finance.view_occupancy_reports', label: 'View occupancy reports', category: 'Finances' },
      { key: 'finance.view_financial_reports', label: 'View financial reports', category: 'Finances' },
    ],
  },
  {
    name: 'Administration',
    permissions: [
      { key: 'admin.manage_staff_logins', label: 'Manage staff logins', category: 'Administration' },
      { key: 'admin.configure_parent_logins', label: 'Configure parent logins', category: 'Administration' },
      { key: 'admin.manage_departments_rooms', label: 'Manage departments and rooms', category: 'Administration' },
      { key: 'admin.manage_departments', label: 'Manage departments', category: 'Administration' },
      { key: 'admin.add_rooms', label: 'Add rooms', category: 'Administration' },
      { key: 'admin.delete_rooms', label: 'Delete rooms', category: 'Administration' },
      { key: 'admin.edit_rooms', label: 'Edit rooms', category: 'Administration' },
      { key: 'admin.configure_centre_settings', label: 'Configure centre settings', category: 'Administration' },
      { key: 'admin.edit_tags', label: 'Edit tags', category: 'Administration' },
      { key: 'admin.configure_features', label: 'Configure features', category: 'Administration' },
    ],
  },
  {
    name: 'Security',
    permissions: [
      { key: 'security.configure', label: 'Configure security', category: 'Security' },
    ],
  },
  {
    name: 'Data Management',
    permissions: [
      { key: 'data.manage_exports', label: 'Manage data exports', category: 'Data Management' },
      { key: 'data.delete_org_personal_data', label: 'Delete organisation personal data', category: 'Data Management' },
      { key: 'data.manage_content_reports', label: 'Manage content reports', category: 'Data Management' },
    ],
  },
];

export const ALL_PERMISSION_KEYS = PERMISSION_CATEGORIES.flatMap((cat) =>
  cat.permissions.map((p) => p.key)
);

export type DefaultRolePreset = 'Manager' | 'Teacher' | 'Parent';

type PermissionPreset = Record<string, { edit: boolean; visible: boolean }>;

const MANAGER_PERMISSIONS: PermissionPreset = {
  'children.view_info': { edit: true, visible: true },
  'children.register_status': { edit: true, visible: true },
  'children.view_private_info': { edit: true, visible: true },
  'children.sign_in_out': { edit: true, visible: true },
  'children.add': { edit: true, visible: true },
  'children.manage_notes': { edit: true, visible: true },
  'children.view_notes': { edit: true, visible: true },
  'staff.view_profiles': { edit: true, visible: true },
  'comms.view_calendar': { edit: true, visible: true },
  'comms.add_calendar_events': { edit: true, visible: true },
  'comms.view_news_feed': { edit: true, visible: true },
  'comms.send_news_posts': { edit: true, visible: true },
  'comms.manage_classroom_messages': { edit: true, visible: true },
  'registration.view_contracts': { edit: true, visible: true },
  'learning.manage_observations': { edit: true, visible: true },
  'learning.view_observations': { edit: true, visible: true },
  'learning.view_activity_plans': { edit: true, visible: true },
  'finance.view_invoices': { edit: true, visible: true },
  'finance.view_occupancy_reports': { edit: true, visible: true },
  'finance.view_financial_reports': { edit: true, visible: true },
};

const TEACHER_PERMISSIONS: PermissionPreset = {
  'children.view_info': { edit: true, visible: true },
  'children.sign_in_out': { edit: true, visible: true },
  'children.manage_notes': { edit: true, visible: true },
  'children.view_notes': { edit: true, visible: true },
  'comms.view_calendar': { edit: true, visible: true },
  'comms.view_news_feed': { edit: true, visible: true },
  'comms.send_news_posts': { edit: true, visible: true },
  'comms.manage_classroom_messages': { edit: true, visible: true },
  'learning.manage_observations': { edit: true, visible: true },
  'learning.view_observations': { edit: true, visible: true },
  'learning.manage_activity_plans': { edit: true, visible: true },
  'learning.view_activity_plans': { edit: true, visible: true },
};

const PARENT_PERMISSIONS: PermissionPreset = {
  'children.view_info': { edit: true, visible: true },
  'children.view_notes': { edit: true, visible: true },
  'comms.view_calendar': { edit: true, visible: true },
  'comms.view_news_feed': { edit: true, visible: true },
  'learning.view_activity_plans': { edit: true, visible: true },
  'finance.view_invoices': { edit: true, visible: true },
};

export const DEFAULT_ROLE_PRESETS: Record<DefaultRolePreset, { description: string; permissions: PermissionPreset }> = {
  Manager: {
    description: 'Full or near-full access to all features. Responsible for site configuration, staff management, and financial oversight.',
    permissions: MANAGER_PERMISSIONS,
  },
  Teacher: {
    description: 'Day-to-day operational access. Can manage children, communications, and learning content. Limited financial and admin access.',
    permissions: TEACHER_PERMISSIONS,
  },
  Parent: {
    description: "Limited read-only access to their own child's information, invoices, and communications from the setting.",
    permissions: PARENT_PERMISSIONS,
  },
};

export function buildPermissionsForPreset(preset: DefaultRolePreset) {
  const presetPerms = DEFAULT_ROLE_PRESETS[preset].permissions;
  return ALL_PERMISSION_KEYS.map((key) => ({
    key,
    edit: presetPerms[key]?.edit ?? false,
    visible: presetPerms[key]?.visible ?? false,
  }));
}

export function buildEmptyPermissions() {
  return ALL_PERMISSION_KEYS.map((key) => ({
    key,
    edit: false,
    visible: false,
  }));
}
