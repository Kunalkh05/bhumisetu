import React from 'react';

interface IndianFlagProps {
  width?: number;
  height?: number;
  className?: string;
  showBorder?: boolean;
  waveEffect?: boolean;
}

/**
 * Mathematically and geometrically accurate Indian National Flag (Tiranga)
 * Follows Flag Code of India specifications:
 * - 3:2 Aspect Ratio (Width:Height = 3:2)
 * - Three equal horizontal bands: Saffron (Top), White (Middle), Green (Bottom)
 * - Ashoka Chakra in Navy Blue (#000080) at the center of the white band with exactly 24 spokes.
 */
export const IndianFlag: React.FC<IndianFlagProps> = ({
  width = 48,
  height,
  className = '',
  showBorder = true,
  waveEffect = false
}) => {
  // If height is not provided, maintain the official 3:2 ratio
  const flagHeight = height || Math.round((width * 2) / 3);
  const flagWidth = width;

  return (
    <div 
      className={`inline-flex items-center justify-center select-none overflow-hidden ${showBorder ? 'border border-slate-300 shadow-2xs' : ''} ${className}`}
      style={{ width: flagWidth, height: flagHeight }}
      title="National Flag of India (Tiranga)"
    >
      <svg
        viewBox="0 0 90 60"
        width={flagWidth}
        height={flagHeight}
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full block"
      >
        {/* Top Band: India Saffron (Kesari) #FF671F / #FF9933 */}
        <rect x="0" y="0" width="90" height="20" fill="#FF9933" />

        {/* Middle Band: White #FFFFFF */}
        <rect x="0" y="20" width="90" height="20" fill="#FFFFFF" />

        {/* Bottom Band: India Green #138808 / #046A38 */}
        <rect x="0" y="40" width="90" height="20" fill="#138808" />

        {/* === CENTRAL ASHOKA CHAKRA (Navy Blue #000080) === */}
        {/* Center: (45, 30), Radius: 8.5 (fits comfortably within height 20 of white band) */}
        <g id="ashoka-chakra">
          {/* Outer ring */}
          <circle cx="45" cy="30" r="8.2" stroke="#000080" strokeWidth="1.2" fill="none" />
          
          {/* Inner ring */}
          <circle cx="45" cy="30" r="2.2" stroke="#000080" strokeWidth="0.8" fill="none" />
          
          {/* Central hub solid dot */}
          <circle cx="45" cy="30" r="1.1" fill="#000080" />

          {/* 24 Equal Spokes (Each at 15 degrees: 360 / 24 = 15°) */}
          {[...Array(24)].map((_, i) => {
            const angle = (i * 15 * Math.PI) / 180;
            const x2 = 45 + 8.0 * Math.cos(angle);
            const y2 = 30 + 8.0 * Math.sin(angle);
            return (
              <line
                key={i}
                x1="45"
                y1="30"
                x2={x2}
                y2={y2}
                stroke="#000080"
                strokeWidth="0.5"
              />
            );
          })}

          {/* 24 Small Outer Dots/Rim Accents around the Chakra perimeter */}
          {[...Array(24)].map((_, i) => {
            const dotAngle = ((i * 15 + 7.5) * Math.PI) / 180;
            const dx = 45 + 7.6 * Math.cos(dotAngle);
            const dy = 30 + 7.6 * Math.sin(dotAngle);
            return (
              <circle
                key={`dot-${i}`}
                cx={dx}
                cy={dy}
                r="0.35"
                fill="#000080"
              />
            );
          })}
        </g>

        {/* Optional subtle silk wave reflection for realistic depth */}
        {waveEffect && (
          <path
            d="M0 0 Q22.5 10 45 0 T90 0 L90 60 Q67.5 50 45 60 T0 60 Z"
            fill="white"
            opacity="0.08"
          />
        )}
      </svg>
    </div>
  );
};
