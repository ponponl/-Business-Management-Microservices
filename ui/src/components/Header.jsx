// src/components/Header.jsx
import React from 'react';
import { Bell } from 'lucide-react';

export default function Header({ title }) {
  return (
    <header className="bg-white border-b border-slate-200 h-13 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
      <div className="text-xs text-slate-500">
        Nghiệp vụ / <span className="text-slate-800 font-semibold">{title}</span>
      </div>
      <div className="flex items-center space-x-3">
        <button className="w-8 h-8 rounded-lg border border-slate-200 flex items-center justify-center text-slate-500 hover:bg-slate-50 relative cursor-pointer">
          <Bell className="w-4 h-4" />
          <span className="w-2 h-2 bg-amber-500 rounded-full absolute top-1.5 right-1.5"></span>
        </button>
        <div className="w-8 h-8 rounded-lg bg-sky-600 text-white font-semibold text-xs flex items-center justify-center shadow-sm">
          A
        </div>
      </div>
    </header>
  );
}