import React from 'react';

type IconProps = {
  as?: React.ElementType;
  size?: number | string;
  className?: string;
  ariaLabel?: string;
  onClick?: React.MouseEventHandler;
};

export default function Icon({ as: As, size = 16, className = '', ariaLabel, onClick }: IconProps) {
  if (!As) return null;

  const ariaProps = ariaLabel
    ? { 'aria-label': ariaLabel, role: 'img' as const }
    : { 'aria-hidden': true } as const;

  // Many icon libraries accept a `size` prop; lucide-react does.
  return <As size={size} className={className} {...ariaProps} onClick={onClick} />;
}
