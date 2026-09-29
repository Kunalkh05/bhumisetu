import React from 'react';
import { useApp } from '../../context/AppContext';
import { ShieldCheck, Phone, Mail, Clock, ExternalLink } from 'lucide-react';

export const GovFooter: React.FC = () => {
  const { language } = useApp();

  const visitorCount = "012849203";

  return (
    <footer className="w-full bg-[#001f35] text-slate-300 text-xs mt-12 border-t border-[#0b3866]" role="contentinfo">
      {/* 1. S3WaaS Tricolour Stripe */}
      <div className="tiranga-strip"></div>

      {/* 2. S3WaaS 4-Column Structured Link Directory */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {/* Column 1: Platform Purpose & Civic-Tech Mission */}
          <div className="space-y-3">
            <div className="border-b border-slate-700 pb-2">
              <h3 className="font-bold text-sm text-white tracking-wide uppercase">
                {language === 'en' ? 'BHUMISETU PLATFORM' : 'भूमिसेतु मंच'}
              </h3>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              {language === 'en'
                ? 'Unified AI-Powered Land Intelligence & Verification Platform. An academic civic-tech demonstration providing preliminary verification and discovery across India’s land records ecosystem.'
                : 'एकीकृत एआई-संचालित भू-आसूचना एवं प्रारंभिक सत्यापन मंच। भारत के भू-अभिलेखों के प्राथमिक विश्लेषण हेतु एक शैक्षणिक नागरिक-तकनीक पहल।'}
            </p>
            <div className="pt-1 text-[11px] text-slate-400">
              <p className="font-semibold text-slate-300">Academic / SIH Demonstration Project</p>
              <p>Inspired by Digital India Land Modernization (DILRMP)</p>
            </div>
          </div>

          {/* Column 2: Government Initiatives & Links */}
          <div className="space-y-3">
            <div className="border-b border-slate-700 pb-2">
              <h3 className="font-bold text-sm text-white tracking-wide uppercase">
                {language === 'en' ? 'IMPORTANT LINKS' : 'महत्वपूर्ण लिंक'}
              </h3>
            </div>
            <ul className="space-y-1.5 text-[11px]">
              <li>
                <a href="https://india.gov.in" target="_blank" rel="noopener noreferrer" className="hover:text-[#f37021] flex items-center gap-1.5 transition-colors">
                  <ExternalLink className="w-3 h-3 text-slate-500" />
                  <span>National Portal of India (india.gov.in)</span>
                </a>
              </li>
              <li>
                <a href="https://digitalindia.gov.in" target="_blank" rel="noopener noreferrer" className="hover:text-[#f37021] flex items-center gap-1.5 transition-colors">
                  <ExternalLink className="w-3 h-3 text-slate-500" />
                  <span>Digital India</span>
                </a>
              </li>
              <li>
                <a href="https://rural.gov.in" target="_blank" rel="noopener noreferrer" className="hover:text-[#f37021] flex items-center gap-1.5 transition-colors">
                  <ExternalLink className="w-3 h-3 text-slate-500" />
                  <span>Ministry of Rural Development</span>
                </a>
              </li>
              <li>
                <a href="https://dolr.gov.in" target="_blank" rel="noopener noreferrer" className="hover:text-[#f37021] flex items-center gap-1.5 transition-colors">
                  <ExternalLink className="w-3 h-3 text-slate-500" />
                  <span>Department of Land Resources (DoLR)</span>
                </a>
              </li>
              <li>
                <a href="https://s3waas.gov.in" target="_blank" rel="noopener noreferrer" className="hover:text-[#f37021] flex items-center gap-1.5 transition-colors">
                  <ExternalLink className="w-3 h-3 text-slate-500" />
                  <span>S3WaaS Framework (NIC)</span>
                </a>
              </li>
            </ul>
          </div>

          {/* Column 3: Website Policies & Legal */}
          <div className="space-y-3">
            <div className="border-b border-slate-700 pb-2">
              <h3 className="font-bold text-sm text-white tracking-wide uppercase">
                {language === 'en' ? 'WEBSITE POLICIES' : 'वेबसाइट नीतियां'}
              </h3>
            </div>
            <ul className="space-y-1.5 text-[11px] text-slate-400">
              <li><a href="#" className="hover:text-white transition-colors">Website Policies &amp; Compliance</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Hyperlink &amp; Content Archival Policy</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Privacy Policy &amp; DPDP Act 2023</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Copyright &amp; Disclaimer Statement</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Terms of Use &amp; Citizen Charter</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Accessibility Statement</a></li>
            </ul>
          </div>

          {/* Column 4: Helpdesk & Working Hours */}
          <div className="space-y-3">
            <div className="border-b border-slate-700 pb-2">
              <h3 className="font-bold text-sm text-white tracking-wide uppercase">
                {language === 'en' ? 'CONTACT & HELPDESK' : 'संपर्क एवं सहायता'}
              </h3>
            </div>
            <div className="space-y-2 text-[11px] text-slate-300">
              <div className="flex items-center gap-2">
                <Phone className="w-3.5 h-3.5 text-[#f37021]" />
                <span>Toll-Free: <strong>1800-11-2013</strong> (9 AM - 6 PM)</span>
              </div>
              <div className="flex items-center gap-2">
                <Mail className="w-3.5 h-3.5 text-[#f37021]" />
                <span>Email: support-bhumisetu@gov.in</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-3.5 h-3.5 text-[#f37021]" />
                <span>Working Days: Monday to Friday</span>
              </div>
            </div>

            {/* S3WaaS Visitor Counter */}
            <div className="pt-2">
              <div className="text-[10px] text-slate-400 mb-1">
                {language === 'en' ? 'Website Visitor Count:' : 'कुल वेबसाइट दर्शक:'}
              </div>
              <div className="counter-box">
                {visitorCount.split('').map((digit, idx) => (
                  <span key={idx} className="counter-digit">
                    {digit}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* S3WaaS National Campaign Banners & Logo Ribbon */}
      <div className="bg-[#001728] border-t border-b border-slate-800 py-3.5 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="text-[11px] font-bold uppercase tracking-wider text-amber-300 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#f37021]"></span>
            <span>{language === 'en' ? 'Flagship National Campaigns' : 'प्रमुख राष्ट्रीय अभियान'}</span>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <a 
              href="https://digitalindia.gov.in" 
              target="_blank" 
              rel="noreferrer"
              className="px-2.5 py-1 bg-white/5 hover:bg-white/10 border border-slate-700 hover:border-slate-500 rounded-xs text-[11px] text-slate-200 transition-colors flex items-center gap-1.5"
            >
              <span className="font-bold text-sky-400">Digital India</span>
              <span className="text-[10px] text-slate-400 hidden sm:inline">&bull; Power To Empower</span>
            </a>

            <a 
              href="https://gatishakti.gov.in" 
              target="_blank" 
              rel="noreferrer"
              className="px-2.5 py-1 bg-white/5 hover:bg-white/10 border border-slate-700 hover:border-slate-500 rounded-xs text-[11px] text-slate-200 transition-colors flex items-center gap-1.5"
            >
              <span className="font-bold text-amber-400">PM GatiShakti</span>
              <span className="text-[10px] text-slate-400 hidden sm:inline">&bull; National Master Plan</span>
            </a>

            <a 
              href="https://svamitva.nic.in" 
              target="_blank" 
              rel="noreferrer"
              className="px-2.5 py-1 bg-white/5 hover:bg-white/10 border border-slate-700 hover:border-slate-500 rounded-xs text-[11px] text-slate-200 transition-colors flex items-center gap-1.5"
            >
              <span className="font-bold text-orange-400">SVAMITVA</span>
              <span className="text-[10px] text-slate-400 hidden sm:inline">&bull; Meri Zameen, Mera Haq</span>
            </a>

            <a 
              href="https://mygov.in" 
              target="_blank" 
              rel="noreferrer"
              className="px-2.5 py-1 bg-white/5 hover:bg-white/10 border border-slate-700 hover:border-slate-500 rounded-xs text-[11px] text-slate-200 transition-colors flex items-center gap-1.5"
            >
              <span className="font-bold text-emerald-400">MyGov</span>
              <span className="text-[10px] text-slate-400 hidden sm:inline">&bull; Meri Sarkar</span>
            </a>

            <a 
              href="https://data.gov.in" 
              target="_blank" 
              rel="noreferrer"
              className="px-2.5 py-1 bg-white/5 hover:bg-white/10 border border-slate-700 hover:border-slate-500 rounded-xs text-[11px] text-slate-200 transition-colors flex items-center gap-1.5"
            >
              <span className="font-bold text-purple-400">Data.gov.in</span>
              <span className="text-[10px] text-slate-400 hidden sm:inline">&bull; Open Data</span>
            </a>

            <a 
              href="https://india.gov.in" 
              target="_blank" 
              rel="noreferrer"
              className="px-2.5 py-1 bg-white/5 hover:bg-white/10 border border-slate-700 hover:border-slate-500 rounded-xs text-[11px] text-slate-200 transition-colors flex items-center gap-1.5"
            >
              <span className="font-bold text-blue-400">India.gov.in</span>
              <span className="text-[10px] text-slate-400 hidden sm:inline">&bull; National Portal</span>
            </a>
          </div>
        </div>
      </div>

      {/* 3. Mandatory Civic-Tech Academic Disclaimer & Credits (Section 20) */}
      <div className="bg-[#00101e] border-t border-slate-800 py-3.5 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto p-3 bg-amber-500/10 border border-amber-500/30 rounded-xs text-[11px] text-amber-200/90 leading-relaxed text-left">
          <strong>Mandatory Academic &amp; Legal Disclaimer: </strong>
          “BhuMiseTu is a prototype civic-tech platform created for demonstration and academic purposes. It is not an official Government of India portal. Information shown may be simulated or aggregated from publicly available sources and should not be treated as legal title verification, government certification, or legal advice.”
        </div>
      </div>

      {/* 4. S3WaaS Hosting Credits & Standards Compliance */}
      <div className="bg-[#001424] border-t border-slate-800 text-[11px] text-slate-400 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-wrap justify-between items-center gap-4">
          <div className="space-y-1 text-left">
            <p>
              {language === 'en'
                ? 'Academic Prototype developed for Smart India Hackathon / Civic-Tech Demonstration.'
                : 'स्मार्ट इंडिया हैकाथॉन / नागरिक-तकनीक प्रदर्शन हेतु विकसित शैक्षणिक प्रारूप।'}
            </p>
            <p className="text-[10px] text-slate-400">
              {language === 'en'
                ? 'Designed using S3WaaS & GIGW 3.0 government accessibility design guidelines.'
                : 'S3WaaS एवं GIGW 3.0 सरकारी सुगम्यता दिशानिर्देशों के अनुरूप संरचित।'}
            </p>
          </div>

          <div className="flex items-center gap-3 text-[10px]">
            <span className="text-slate-400">Last Updated: <strong className="text-slate-300">29 September 2026</strong></span>
            <span>•</span>
            <span className="flex items-center gap-1 text-emerald-400 font-semibold">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>GIGW 3.0 / WCAG 2.1 Compliant</span>
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
};
