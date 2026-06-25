import type { SVGProps } from 'react';

type IconProps = SVGProps<SVGSVGElement>;

const baseProps = {
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.75,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
} as const;

function Svg({ children, ...rest }: IconProps & { children: React.ReactNode }) {
  return (
    <svg {...baseProps} aria-hidden="true" {...rest}>
      {children}
    </svg>
  );
}

// — Navigation —

export function CentresIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 11.5 12 4l9 7.5" />
      <path d="M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9" />
    </Svg>
  );
}

export function SessionsIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M7 5V3M17 5V3M3 10h18" />
      <circle cx="8" cy="14" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="12" cy="14" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="16" cy="14" r="0.9" fill="currentColor" stroke="none" />
    </Svg>
  );
}

export function TimetableIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3" y="4" width="18" height="17" rx="2" />
      <path d="M3 9h18" />
      <path d="M9 4v17M15 4v17" />
      <path d="M3 14h18" />
    </Svg>
  );
}

export function ChildrenIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="9" cy="8" r="3.25" />
      <path d="M3.5 19c.7-2.9 3-4.75 5.5-4.75S13.8 16.1 14.5 19" />
      <circle cx="17" cy="9" r="2.5" />
      <path d="M14 19c.4-1.9 1.7-3 3-3s2.6 1.1 3 3" />
    </Svg>
  );
}

export function InfoIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M8 16V11" />
      <path d="M12 16V8" />
      <path d="M16 16v-3" />
    </Svg>
  );
}

// — Generic UI —

export function CloseIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6 6l12 12M18 6 6 18" />
    </Svg>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M5 12.5 10 17l9-10" />
    </Svg>
  );
}

export function TrashIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 7h16" />
      <path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
      <path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12" />
      <path d="M10 11v6M14 11v6" />
    </Svg>
  );
}

export function WarningIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 4 2.5 20h19L12 4z" />
      <path d="M12 10v5" />
      <circle cx="12" cy="17.5" r="0.6" fill="currentColor" stroke="none" />
    </Svg>
  );
}

export function StarIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 4.5l2.4 5 5.5.5-4.2 3.7 1.3 5.4L12 16.3l-5 2.8 1.3-5.4-4.2-3.7 5.5-.5z" />
    </Svg>
  );
}

export function RecurringIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 12a8 8 0 0 1 13.7-5.7L20 8" />
      <path d="M20 4v4h-4" />
      <path d="M20 12a8 8 0 0 1-13.7 5.7L4 16" />
      <path d="M4 20v-4h4" />
    </Svg>
  );
}

// — Domain —

export function MapPinIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z" />
      <circle cx="12" cy="9.5" r="2.5" />
    </Svg>
  );
}

export function PhoneIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M5 4h3.5l1.7 4.3-2.2 1.3a12 12 0 0 0 6.4 6.4l1.3-2.2 4.3 1.7V19a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z" />
    </Svg>
  );
}

export function MobileIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="7" y="3" width="10" height="18" rx="2" />
      <path d="M11 18h2" />
    </Svg>
  );
}

export function MailIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M3 7l9 6 9-6" />
    </Svg>
  );
}

export function UserIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M4.5 20c1-3.5 4-5.5 7.5-5.5s6.5 2 7.5 5.5" />
    </Svg>
  );
}

export function UsersIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="9" cy="8" r="3.25" />
      <path d="M3.5 19c.7-2.9 3-4.75 5.5-4.75S13.8 16.1 14.5 19" />
      <circle cx="17" cy="9" r="2.5" />
      <path d="M14 19c.4-1.9 1.7-3 3-3s2.6 1.1 3 3" />
    </Svg>
  );
}

export function TeacherIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 9.5 12 5.5l9 4-9 4-9-4z" />
      <path d="M7.5 11.5V15c0 1.4 2 2.5 4.5 2.5s4.5-1.1 4.5-2.5v-3.5" />
      <path d="M21 9.5V15" />
    </Svg>
  );
}

export function ReceiptIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6 3h12v18l-2-1.5L14 21l-2-1.5L10 21l-2-1.5L6 21z" />
      <path d="M9 8h6M9 12h6M9 16h4" />
    </Svg>
  );
}

export function CalendarIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M3 10h18" />
      <path d="M8 3v4M16 3v4" />
    </Svg>
  );
}

export function ClockIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </Svg>
  );
}

export function DoorIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M5 21V4a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v17" />
      <path d="M3 21h18" />
      <circle cx="15" cy="12.5" r="0.8" fill="currentColor" stroke="none" />
    </Svg>
  );
}

export function ClipboardIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="6" y="4" width="12" height="17" rx="2" />
      <rect x="9" y="2.5" width="6" height="3" rx="1" />
      <path d="M9 11h6M9 14h6M9 17h4" />
    </Svg>
  );
}

export function ChartIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M8 16V11" />
      <path d="M12 16V8" />
      <path d="M16 16v-3" />
    </Svg>
  );
}

export function RolesIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 2l7 4v5c0 5.25-3.5 9.74-7 11-3.5-1.26-7-5.75-7-11V6l7-4z" />
      <circle cx="12" cy="10" r="2.5" />
      <path d="M8.5 16c.6-1.5 1.8-2.5 3.5-2.5s2.9 1 3.5 2.5" />
    </Svg>
  );
}

export function PlusIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 5v14M5 12h14" />
    </Svg>
  );
}

export function AccessRequestsIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M4.5 20c1-3.5 4-5.5 7.5-5.5s6.5 2 7.5 5.5" />
      <path d="M18 8l2 2 4-4" />
    </Svg>
  );
}

export function LogoutIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="M16 17l5-5-5-5" />
      <path d="M21 12H9" />
    </Svg>
  );
}
