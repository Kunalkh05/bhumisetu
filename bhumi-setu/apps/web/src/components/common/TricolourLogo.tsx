import React from 'react';
import { NationalEmblem } from './NationalEmblem';
import { IndianFlag } from './IndianFlag';

interface TricolourLogoProps {
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  language?: 'en' | 'hi';
}

export const TricolourLogo: React.FC<TricolourLogoProps> = ({ 
  size = 'md', 
  showText = true,
  language = 'en' 
}) => {
  const emblemPixelSize = size === 'sm' ? 40 : size === 'lg' ? 62 : 48;
  const flagWidth = size === 'sm' ? 36 : size === 'lg' ? 51 : 42;

  return (
    <div className="flex items-center gap-3.5 select-none">
      {/* Official State Emblem of India + National Flag of India */}
      <div className="relative flex-shrink-0 flex items-center gap-2">
        {/* National Emblem (Lion Capital of Ashoka with Satyameva Jayate) */}
        <div className="flex flex-col items-center justify-center p-1 bg-white border border-slate-300 shadow-2xs">
          <NationalEmblem 
            size={emblemPixelSize} 
            color="#002b49" 
            showSlogan={false} 
          />
        </div>

        {/* Proper Indian National Flag (Tiranga) with 3:2 ratio and 24-spoke Ashoka Chakra */}
        <div className="hidden sm:flex flex-col items-center justify-center">
          <IndianFlag width={flagWidth} showBorder={true} />
        </div>
      </div>

      {/* Official Bilingual Portal Typography (Bhoomi Rashi / Land Acquisition Portal Hierarchy) */}
      {showText && (
        <div className="flex flex-col justify-center">
          {/* Ministry & Government Header */}
          <div className="flex items-center gap-2">
            <span className="text-[11px] sm:text-xs font-bold text-[#b22222] tracking-wide uppercase font-serif">
              {language === 'en' ? 'भारत सरकार' : 'GOVERNMENT OF INDIA'}
            </span>
            <span className="text-slate-400 text-xs">•</span>
            <span className="text-[11px] sm:text-xs font-semibold text-slate-700">
              {language === 'en' ? 'Ministry of Rural Development' : 'ग्रामीण विकास मंत्रालय'}
            </span>
          </div>

          {/* Main Portal Title */}
          <div className="flex items-baseline gap-2 mt-0.5">
            <div className="flex items-center">
              <span className="text-xl sm:text-2xl font-black font-serif tracking-tight text-[#002b49] drop-shadow-xs">
                {language === 'en' ? 'BHUMISETU' : 'भूमिसेतु'}
              </span>
              <span className="text-xs sm:text-sm font-bold text-[#FF9933] ml-1.5 font-serif">
                {language === 'en' ? 'भूमिसेतु' : 'BHUMISETU'}
              </span>
            </div>
            
            {/* National Statutory Portal Badge */}
            <span className="hidden md:inline-block px-1.5 py-0.2 text-[9px] font-bold bg-[#fff8e7] text-[#994d00] border border-[#e6b800] uppercase">
              {language === 'en' ? 'National Portal' : 'राष्ट्रीय पोर्टल'}
            </span>
          </div>

          {/* Statutory Legislation Reference */}
          <div className="text-[10px] sm:text-[11px] text-slate-600 font-medium flex items-center gap-1.5">
            <span>{language === 'en' ? 'RFCTLARR Act 2013 Statutory Compliance & Compensation System' : 'भूमि अधिग्रहण, उचित मुआवजा एवं पुनर्वास सांविधिक प्रणाली'}</span>
          </div>
        </div>
      )}
    </div>
  );
};
