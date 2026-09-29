import React, { useState } from 'react';

interface NationalEmblemProps {
  className?: string;
  size?: number;
  color?: string;
  showSlogan?: boolean;
}

/**
 * Official State Emblem of India (Lion Capital of Ashoka) with the 3 visible lions,
 * Dharma Chakra abacus, and "सत्यमेव जयते" (Satyameva Jayate) in authentic Devanagari script.
 */
export const NationalEmblem: React.FC<NationalEmblemProps> = ({
  className = '',
  size = 56,
  color = '#002b49',
  showSlogan = true
}) => {
  const [imgError, setImgError] = useState(false);

  return (
    <div className={`flex flex-col items-center justify-center select-none ${className}`}>
      {!imgError ? (
        <img
          src="/assets/emblem.svg"
          alt="State Emblem of India - Satyameva Jayate"
          width={size}
          height={Math.round(size * 1.55)}
          className="object-contain"
          referrerPolicy="no-referrer"
          onError={() => setImgError(true)}
          style={{ 
            width: `${size}px`, 
            height: 'auto',
            maxHeight: `${Math.round(size * 1.6)}px`
          }}
        />
      ) : (
        /* Vector Fallback if asset fails to load */
        <div className="flex flex-col items-center justify-center">
          <svg
            width={size}
            height={size * 1.3}
            viewBox="0 0 200 260"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="drop-shadow-xs"
            aria-label="State Emblem of India"
          >
            {/* Lion Crown & Mane */}
            <path
              d="M100 12 C82 12 74 22 74 36 C74 48 80 56 82 68 C84 76 78 84 76 96 C74 108 82 118 100 118 C118 118 126 108 124 96 C122 84 116 76 118 68 C120 56 126 48 126 36 C126 22 118 12 100 12 Z"
              fill={color}
            />
            <path d="M78 20 C72 16 68 22 72 30 C76 28 78 24 78 20 Z" fill={color} />
            <path d="M122 20 C128 16 132 22 128 30 C124 28 122 24 122 20 Z" fill={color} />
            <ellipse cx="91" cy="42" rx="3.5" ry="2.5" fill="#ffffff" />
            <ellipse cx="109" cy="42" rx="3.5" ry="2.5" fill="#ffffff" />
            <circle cx="91" cy="42" r="1.5" fill={color} />
            <circle cx="109" cy="42" r="1.5" fill={color} />
            <path d="M96 46 L104 46 L100 53 Z" fill="#ffffff" />
            <path d="M92 56 C95 53 105 53 108 56 C106 63 94 63 92 56 Z" fill="#ffffff" />
            <rect x="96" y="56" width="2" height="3" fill={color} />
            <rect x="102" y="56" width="2" height="3" fill={color} />
            <path d="M68 28 C56 26 44 38 46 54 C48 64 56 70 54 82 C52 92 46 100 52 110 C58 116 68 116 74 112 C72 98 70 86 70 72 C70 56 68 42 68 28 Z" fill={color} />
            <path d="M132 28 C144 26 156 38 154 54 C152 64 144 70 146 82 C148 92 154 100 148 110 C142 116 132 116 126 112 C128 98 130 86 130 72 C130 56 132 42 132 28 Z" fill={color} />
            <rect x="36" y="136" width="128" height="8" rx="2" fill={color} />
            <rect x="42" y="144" width="116" height="34" fill={color} />
            <circle cx="100" cy="161" r="13" fill="#ffffff" />
            <circle cx="100" cy="161" r="11" stroke={color} strokeWidth="1.5" fill="none" />
            <circle cx="100" cy="161" r="3" fill={color} />
            <rect x="36" y="178" width="128" height="6" rx="1" fill={color} />
            <path d="M48 184 L152 184 L144 200 L56 200 Z" fill={color} />
            <rect x="30" y="200" width="140" height="8" rx="2" fill={color} />
          </svg>
          {showSlogan && (
            <div 
              className="text-center font-bold tracking-wider uppercase font-serif mt-0.5 leading-none"
              style={{ color: color, fontSize: Math.max(10, Math.round(size * 0.18)) }}
            >
              सत्यमेव जयते
            </div>
          )}
        </div>
      )}
    </div>
  );
};
