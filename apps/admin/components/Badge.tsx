import clsx from 'clsx';

interface BadgeProps {
  label: string;
  variant?: 'success' | 'warning' | 'error' | 'info' | 'neutral';
}

const variantClasses: Record<NonNullable<BadgeProps['variant']>, string> = {
  success: 'bg-success/10 text-success border-success/30',
  warning: 'bg-warning/10 text-warning border-warning/30',
  error:   'bg-error/10 text-error border-error/30',
  info:    'bg-teal/10 text-teal border-teal/30',
  neutral: 'bg-light-grey text-dark-grey border-light-grey',
};

export function statusVariant(status: string): BadgeProps['variant'] {
  switch (status.toLowerCase()) {
    case 'active':
    case 'approved':
    case 'success':
    case 'completed':
      return 'success';
    case 'pending':
    case 'processing':
    case 'suspended':
      return 'warning';
    case 'rejected':
    case 'failed':
    case 'closed':
      return 'error';
    default:
      return 'neutral';
  }
}

export default function Badge({ label, variant = 'neutral' }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border',
        variantClasses[variant],
      )}
    >
      {label}
    </span>
  );
}
