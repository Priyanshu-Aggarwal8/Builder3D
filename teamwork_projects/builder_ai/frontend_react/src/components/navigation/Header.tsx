import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, Menu, X, Sun, Moon, Building2, Layers } from 'lucide-react';

interface HeaderProps {
  currentPage: string;
  onNavigate: (page: string) => void;
  theme?: 'dark' | 'light';
  onToggleTheme?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentPage,
  onNavigate,
  theme = 'dark',
  onToggleTheme,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const isLight = theme === 'light';

  const navItems = [
    { id: 'landing', label: 'Overview' },
    { id: 'studio', label: '3D Studio' },
    { id: 'compliance', label: 'Compliance' },
  ];

  const handleNav = (id: string) => {
    onNavigate(id);
    setMobileMenuOpen(false);
  };

  return (
    <>
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className={`fixed top-5 left-4 right-4 md:left-8 md:right-8 z-50 flex items-center justify-between px-6 py-3 rounded-full transition-colors duration-200 ${
          isLight
            ? 'bg-white/95 border border-black/80 shadow-sm text-black'
            : 'bg-black/95 border border-white/20 shadow-xl text-white'
        }`}
      >
        {/* Brand Logo */}
        <button
          onClick={() => handleNav('landing')}
          className="flex items-center gap-3 text-left group cursor-pointer focus:outline-none"
        >
          <div className={`w-2.5 h-2.5 rounded-full transition-transform group-hover:scale-125 ${
            isLight ? 'bg-black' : 'bg-white'
          }`} />
          <span className="font-black text-xs md:text-sm tracking-[0.2em] uppercase">
            BUILDER.AI
          </span>
          <span className={`hidden sm:inline-block px-2 py-0.5 text-[9px] font-bold tracking-wider rounded uppercase border ${
            isLight
              ? 'bg-black/5 text-black border-black/20'
              : 'bg-white/10 text-white border-white/20'
          }`}>
            OpenBIM
          </span>
        </button>

        {/* Desktop Navigation Links */}
        <nav className={`hidden md:flex items-center gap-1 p-1 rounded-full border ${
          isLight ? 'bg-neutral-100 border-neutral-200' : 'bg-neutral-900 border-neutral-800'
        }`}>
          {navItems.map((item) => {
            const isActive = currentPage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleNav(item.id)}
                className={`relative px-4 py-1.5 text-xs font-bold tracking-tight rounded-full transition-all ${
                  isActive
                    ? isLight
                      ? 'bg-black text-white shadow-sm'
                      : 'bg-white text-black shadow-sm'
                    : isLight
                    ? 'text-neutral-600 hover:text-black'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Action Controls */}
        <div className="hidden md:flex items-center gap-2">
          {/* Theme Switcher */}
          {onToggleTheme && (
            <button
              onClick={onToggleTheme}
              className={`p-2 rounded-full border transition-all ${
                isLight
                  ? 'bg-neutral-100 border-neutral-300 text-black hover:bg-neutral-200'
                  : 'bg-neutral-900 border-neutral-800 text-white hover:bg-neutral-800'
              }`}
              title={`Switch to ${isLight ? 'Dark' : 'Light'} Mode`}
            >
              {isLight ? <Moon className="w-3.5 h-3.5 stroke-[1.5]" /> : <Sun className="w-3.5 h-3.5 stroke-[1.5]" />}
            </button>
          )}

          <button
            onClick={() => handleNav('studio')}
            className={`flex items-center gap-2 px-5 py-2 text-xs font-black tracking-tight rounded-full transition-transform hover:scale-105 active:scale-95 cursor-pointer ${
              isLight
                ? 'bg-black text-white hover:bg-neutral-800'
                : 'bg-white text-black hover:bg-neutral-200'
            }`}
          >
            <span>Launch Studio</span>
            <ArrowRight className="w-3.5 h-3.5 stroke-[2]" />
          </button>
        </div>

        {/* Mobile Hamburger Toggle */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 md:hidden"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </motion.header>

      {/* Mobile Drawer Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`fixed top-20 left-4 right-4 z-40 p-5 rounded-3xl border shadow-2xl flex flex-col gap-3 md:hidden ${
              isLight ? 'bg-white border-black text-black' : 'bg-black border-white/20 text-white'
            }`}
          >
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => handleNav(item.id)}
                className={`w-full text-left py-2.5 px-4 rounded-xl text-xs font-bold ${
                  currentPage === item.id
                    ? isLight ? 'bg-black text-white' : 'bg-white text-black'
                    : isLight ? 'text-neutral-700 hover:bg-neutral-100' : 'text-neutral-300 hover:bg-neutral-900'
                }`}
              >
                {item.label}
              </button>
            ))}
            <button
              onClick={() => handleNav('studio')}
              className={`w-full py-3 rounded-full font-black text-xs mt-2 ${
                isLight ? 'bg-black text-white' : 'bg-white text-black'
              }`}
            >
              Launch Studio
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};
