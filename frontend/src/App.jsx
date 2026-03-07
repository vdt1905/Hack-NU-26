import React, { useState } from 'react';
import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { ToastProvider } from './components/Toasts';

// Pipeline Pages
import { Landing } from './pages/Landing';
import { Upload } from './pages/Upload';
import { Configure } from './pages/Configure';
import { Process } from './pages/Process';
import { Latex } from './pages/Latex';
import { McpAgent } from './pages/McpAgent';
import { Editor } from './pages/Editor';

// Main layout with Sidebar + Navbar
function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="min-h-screen bg-[var(--color-surface-50)] text-[var(--color-text-main)] flex font-sans overflow-hidden">
      <div className="py-4 pl-4 shrink-0 flex">
        <Sidebar isOpen={sidebarOpen} toggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
      </div>

      <div className="flex flex-1 flex-col h-screen overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-y-auto w-full p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <ToastProvider>
      <Routes>
        {/* Landing (full-screen, no sidebar) */}
        <Route path="/" element={<Landing />} />

        {/* Pipeline routes with sidebar layout */}
        <Route element={<AppLayout />}>
          <Route path="/upload" element={<Upload />} />
          <Route path="/configure" element={<Configure />} />
          <Route path="/process" element={<Process />} />
          <Route path="/editor" element={<Editor />} />
          <Route path="/latex" element={<Latex />} />
          <Route path="/agent" element={<McpAgent />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ToastProvider>
  );
}

export default App;
