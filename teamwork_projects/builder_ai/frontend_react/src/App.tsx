import React, { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Header } from './components/navigation/Header';
import { Footer } from './components/navigation/Footer';
import { LandingPage } from './pages/LandingPage';
import { StudioPage } from './pages/StudioPage';
import { CompliancePage } from './pages/CompliancePage';
import { BuildingModel } from './types/model';
import { fetchProjectModel, defaultVillaModel, sanitizeBuildingModel } from './services/api';
import { ErrorBoundary } from './components/common/ErrorBoundary';

export function App() {
  const [currentPage, setCurrentPage] = useState('landing');
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('builder_ai_theme') as 'dark' | 'light') || 'dark';
  });
  const [model, setModel] = useState<BuildingModel>(defaultVillaModel);

  useEffect(() => {
    fetchProjectModel(1).then((data) => {
      if (data) setModel(sanitizeBuildingModel(data));
    });
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    localStorage.setItem('builder_ai_theme', nextTheme);
  };

  const isLight = theme === 'light';

  return (
    <ErrorBoundary fallbackTitle="BuilderAI Studio Ready">
      <div className={`min-h-screen flex flex-col relative selection:bg-neutral-900 selection:text-white transition-colors duration-200 ${
        isLight ? 'bg-white text-black' : 'bg-black text-white'
      }`}>
        {/* Floating Global Header */}
        {currentPage !== 'studio' && (
          <Header
            currentPage={currentPage}
            onNavigate={setCurrentPage}
            theme={theme}
            onToggleTheme={toggleTheme}
          />
        )}

        {/* Main Content Router with Page Transitions */}
        <main className="flex-1 w-full flex flex-col">
          <AnimatePresence mode="wait">
            {currentPage === 'landing' && (
              <motion.div
                key="landing"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.35 }}
                className="w-full flex-1"
              >
                <LandingPage model={model} onNavigate={setCurrentPage} theme={theme} />
              </motion.div>
            )}

            {currentPage === 'studio' && (
              <motion.div
                key="studio"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="w-full h-screen"
              >
                <StudioPage
                  model={model}
                  onUpdateModel={(m) => setModel(sanitizeBuildingModel(m))}
                  onNavigate={setCurrentPage}
                  theme={theme}
                  onToggleTheme={toggleTheme}
                />
              </motion.div>
            )}

            {currentPage === 'compliance' && (
              <motion.div
                key="compliance"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.35 }}
                className="w-full flex-1"
              >
                <CompliancePage
                  model={model}
                  onUpdateModel={(m) => setModel(sanitizeBuildingModel(m))}
                  onNavigate={setCurrentPage}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </main>

        {/* Global Footer on Non-Studio Pages */}
        {currentPage !== 'studio' && (
          <Footer onNavigate={setCurrentPage} theme={theme} />
        )}
      </div>
    </ErrorBoundary>
  );
}

export default App;
