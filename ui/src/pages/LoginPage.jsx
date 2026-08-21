import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Ship, User, KeyRound, ArrowRight, Eye, EyeOff, Loader2 } from 'lucide-react';

export default function LoginPage({ onLoginSuccess }) {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    username: 'manager01', // Sửa email -> username
    password: 'Password@123',
    rememberMe: true,
  });

  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(''); // Thêm state hiển thị lỗi

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage('');

    try {
      // Gọi trực tiếp API Login của Auth Service
      const response = await fetch('http://localhost:8081/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: formData.username,
          password: formData.password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Đăng nhập thất bại!');
      }

      // 1. Lưu JWT Token vào LocalStorage
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user_role', data.role);

      // 2. Cập nhật State cho App
      if (onLoginSuccess) {
        onLoginSuccess({
          username: formData.username,
          role: data.role,
          token: data.access_token,
        });
      }

      // 3. Chuyển hướng sang trang Dashboard
      navigate('/');
    } catch (err) {
      setErrorMessage(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4 sm:p-6">
      <div className="w-full max-w-[420px]">
        
        {/* Card Đăng Nhập Trung Tâm */}
        <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/60 border border-slate-200/80 p-8 sm:p-9">
          
          {/* Header Brand */}
          <div className="flex items-center justify-center space-x-3 mb-8 pb-6 border-b border-slate-100">
            <div className="w-10 h-10 rounded-xl bg-sky-600 flex items-center justify-center font-bold text-white shadow-md shadow-sky-600/20">
              <Ship className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-bold text-base text-slate-900 tracking-tight leading-none">ABC LOGISTICS</h1>
              <span className="text-[11px] text-slate-500 font-medium">Hệ thống Quản trị Kinh doanh</span>
            </div>
          </div>

          {/* Tiêu đề Form */}
          <div className="text-center mb-6">
            <h2 className="text-lg font-bold text-slate-800">Đăng nhập Hệ thống</h2>
            <p className="text-xs text-slate-500 mt-1">Dành cho cán bộ công nhân viên ABC Logistics</p>
          </div>

          {/* Alert hiển thị lỗi khi sai TK/MK */}
          {errorMessage && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 text-xs rounded-xl text-center">
              {errorMessage}
            </div>
          )}

          {/* Form Nhập Liệu */}
          <form onSubmit={handleSubmit} className="space-y-4">
            
            {/* Input Username */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Tên tài khoản / Mã NV
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                  <User className="w-4 h-4" />
                </span>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  required
                  placeholder="Nhập tên tài khoản..."
                  className="w-full bg-slate-50 border border-slate-200 text-xs text-slate-800 rounded-xl pl-9 pr-3 py-2.5 focus:bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-500/15 outline-none transition"
                />
              </div>
            </div>

            {/* Input Mật Khẩu */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Mật khẩu
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                  <KeyRound className="w-4 h-4" />
                </span>
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  placeholder="Nhập mật khẩu..."
                  className="w-full bg-slate-50 border border-slate-200 text-xs text-slate-800 rounded-xl pl-9 pr-8 py-2.5 focus:bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-500/15 outline-none transition"
                />
                
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-600 cursor-pointer"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Ghi nhớ & Quên mật khẩu */}
            <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
              <label className="flex items-center space-x-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  name="rememberMe"
                  checked={formData.rememberMe}
                  onChange={handleChange}
                  className="rounded border-slate-300 text-sky-600 focus:ring-sky-500 cursor-pointer"
                />
                <span>Ghi nhớ đăng nhập</span>
              </label>
              <a href="#forgot" className="text-sky-600 hover:text-sky-700 font-semibold hover:underline">
                Quên mật khẩu?
              </a>
            </div>

            {/* Nút Đăng Nhập */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-sky-600 hover:bg-sky-700 disabled:bg-sky-400 text-white text-xs font-semibold rounded-xl shadow-md shadow-sky-600/10 transition flex items-center justify-center space-x-2 mt-2 cursor-pointer"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Đang kết nối Backend...</span>
                </>
              ) : (
                <>
                  <span>Đăng nhập</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center text-[11px] text-slate-400 mt-4 font-medium tracking-wide">
          CÔNG TY CỔ PHẦN LOGISTICS ABC © 2026
        </p>

      </div>
    </div>
  );
}