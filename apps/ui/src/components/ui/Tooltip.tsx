'use client';

import { ReactNode, useState, useRef } from 'react';

type TooltipSide = 'top' | 'bottom' | 'left' | 'right';

interface TooltipProps {
  content:  ReactNode;
  children: ReactNode;
  side?:    TooltipSide;
  delay?:   number;
}

const SIDE_CLS: Record<TooltipSide, string> = {
  top:    'bottom-full left-1/2 -translate-x-1/2 mb-2',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
  left:   'right-full top-1/2 -translate-y-1/2 mr-2',
  right:  'left-full top-1/2 -translate-y-1/2 ml-2',
};

export function Tooltip({ content, children, side = 'top', delay = 300 }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = () => {
    timeoutRef.current = setTimeout(() => setVisible(true), delay);
  };
  const hide = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setVisible(false);
  };

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      {visible && (
        <span
          role="tooltip"
          className={[
            'absolute z-50 pointer-events-none whitespace-nowrap',
            'bg-ink-800 border border-ink-line text-slate-200 text-xs rounded-lg px-2.5 py-1.5 shadow-lg',
            SIDE_CLS[side],
          ].join(' ')}
        >
          {content}
        </span>
      )}
    </span>
  );
}

export default Tooltip;
