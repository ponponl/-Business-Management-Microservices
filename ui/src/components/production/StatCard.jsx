import React from 'react';

export default function StatCard({ title, value, icon, colorClass }) {
    return (
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
                <p className="text-sm font-medium text-slate-500 mb-1">{title}</p>
                <h3 className="text-3xl font-bold text-slate-800">{value}</h3>
            </div>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${colorClass}`}>
                <i className={`${icon} text-lg`}></i>
            </div>
        </div>
    );
}
