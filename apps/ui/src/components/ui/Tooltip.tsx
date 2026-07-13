'use client';

import { ReactNode, useState, useRef, useId } from 'react';

type TooltipSide = 'top' | 'bottom' | 'left' | 'right';

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  side?: TooltipSide;
  delay?: number;
}

const SIDE_CLS: Record<TooltipSide, string> = {
  top:    'bottom-full left-1/2 -translate-x-1/2 mb-1.5',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-1.5',
  left:   'right-full top-1/2 -translate-y-1/2 mr-1.5',
  right:  'left-full top-1/2 -translate-y-1/2 ml-1.5',
};

const ARROW_CLS: Record<TooltipSide, string> = {
  top:    'top-full left-1/2 -translate-x-1/2 border-t-earth-800 border-x-transparent border-b-transparent border-4',
  bottom: 'bottom-full left-1/2 -translate-x-1/2 border-b-earth-800 border-x-transparent border-t-transparent border-4',
  left:   'left-full top-1/2 -translate-y-1/2 border-l-earth-800 border-y-transparent border-r-transparent border-4',
  right:  'right-full top-1/2 -translate-y-1/2 border-r-earth-800 border-y-transparent border-l-transparent border-4',
};

export function Tooltip({ content, children, side = 'top', delay = 300 }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tooltipId = useId();

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
      aria-describedby={visible ? tooltipId : undefined}
    >
      {children}
      {visible && (
        <span
          id={tooltipId}
          role="tooltip"
          className={[
            'absolute z-50 pointer-events-none whitespace-nowrap',
            'bg-earth-800 text-earth-100 text-xs rounded-token px-2 py-1 shadow-token-sm',
            SIDE_CLS[side],
          ].join(' ')}
        >
          {content}
          {/* Arrow */}
          <span className={`absolute border ${ARROW_CLS[side]}`} />
        </span>
      )}
    </span>
  );
}

export default Tooltip;
