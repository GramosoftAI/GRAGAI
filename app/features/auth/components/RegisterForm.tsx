"use client";

import React, { useState } from 'react';
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import { useRegister } from "../hooks/useRegister";
import { routes } from "../../../services/routes";

export default function RegisterForm() {
  const router = useRouter();
  const { register, error, isSubmitting } = useRegister();
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    tenant_name: "",
    email: "",
    password: "",
    confirm_password: ""
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.password !== formData.confirm_password) {
      alert("Passwords do not match");
      return;
    }
    register(formData);
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-[#e8e8e8] font-sans p-4 overflow-hidden">
      <div className="card-container">
        <div className="circle1" />
        <div className="circle2" />
        <div className="container">
          <form className="log-card" onSubmit={handleSubmit}>
            <p className="heading">Create Account</p>
            <p className="para">Join the future of knowledge graphs</p>
            
            {error && (
              <p className="text-red-500 text-xs font-bold mt-1 text-center">{error}</p>
            )}

            <div className="input-group">
              <div className="flex gap-4 mb-1">
                <div className="flex-1">
                  <p className="text">First Name</p>
                  <input className="input" type="text" name="first_name" placeholder="First" value={formData.first_name} onChange={handleChange} required />
                </div>
                <div className="flex-1">
                  <p className="text">Last Name</p>
                  <input className="input" type="text" name="last_name" placeholder="Last" value={formData.last_name} onChange={handleChange} required />
                </div>
              </div>

              <p className="text">Tenant Name</p>
              <input className="input" type="text" name="tenant_name" placeholder="e.g. Acme Corp" value={formData.tenant_name} onChange={handleChange} required />
              
              <p className="text">Email</p>
              <input className="input" type="email" name="email" placeholder="name@company.com" value={formData.email} onChange={handleChange} required />
              
              <div className="flex gap-4">
                <div className="flex-1">
                  <p className="text">Password</p>
                  <div className="relative">
                    <input 
                      className="input pr-10" 
                      type={showPassword ? "text" : "password"} 
                      name="password" 
                      placeholder="••••••••" 
                      value={formData.password} 
                      onChange={handleChange} 
                      required 
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-[#2879f3] transition-colors focus:outline-none"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                <div className="flex-1">
                  <p className="text">Confirm</p>
                  <div className="relative">
                    <input 
                      className="input pr-10" 
                      type={showConfirmPassword ? "text" : "password"} 
                      name="confirm_password" 
                      placeholder="••••••••" 
                      value={formData.confirm_password} 
                      onChange={handleChange} 
                      required 
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-[#2879f3] transition-colors focus:outline-none"
                    >
                      {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <button className="btn" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Register"}
            </button>
            
            <p className="no-account">
              Already have an account?
              <a 
                className="link cursor-pointer ml-1" 
                onClick={() => router.push(routes.login)}
              >
                Sign In
              </a>
            </p>
          </form>
        </div>
      </div>

      <style jsx>{`
        .card-container { width: 100%; max-width: 540px; position: relative; transition: all 0.3s ease; }
        .container { display: flex; height: 100%; width: 100%; align-items: center; justify-content: center; }
        .circle1 { height: 120px; width: 120px; border-radius: 50%; background-color: #2879f3; position: absolute; top: -20px; left: -20px; z-index: 0; opacity: 0.9; }
        .circle2 { height: 120px; width: 120px; border-radius: 50%; background-color: #f37e10; position: absolute; right: -20px; bottom: -20px; z-index: 0; opacity: 0.9; }
        .log-card { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif; position: relative; z-index: 10; width: 100%; background: rgba(255, 255, 255, 0.95); border-radius: 28px; display: flex; flex-direction: column; box-shadow: 0 15px 45px rgba(0, 0, 0, 0.08); backdrop-filter: blur(10px); padding: 40px 44px; }
        .heading { font-size: 38px; font-weight: 900; margin-bottom: 2px; color: #0f172a; text-align: center; letter-spacing: -0.02em; }
        .para { font-size: 14px; font-weight: 600; color: #64748b; text-align: center; margin-bottom: 8px; }
        .text { margin-top: 12px; margin-bottom: 4px; font-size: 11px; font-weight: 800; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-left: 2px; }
        .input-group { margin-top: 5px; margin-bottom: 8px; }
        .input { box-sizing: border-box; margin-bottom: 2px; width: 100%; border: 2px solid #f1f5f9; padding: 12px 16px; background-color: #f8fafc; border-radius: 12px; font-weight: 700; color: #2879f3; outline: none; font-size: 15px; transition: all 0.2s; }
        .input:hover, .input:focus { border-color: #2879f3; background-color: white; box-shadow: 0 2px 10px rgba(40, 121, 243, 0.06); }
        .btn { width: 100%; margin-top: 16px; margin-bottom: 12px; padding: 14px; border: none; background-color: #2879f3; color: white; font-size: 17px; font-weight: 900; border-radius: 14px; cursor: pointer; transition: all 0.2s; }
        .btn:hover { background-color: #1d64d1; transform: translateY(-1px); }
        .btn:disabled { background-color: #94a3b8; cursor: not-allowed; }
        .no-account { font-size: 14px; font-weight: 600; color: #64748b; text-align: center; }
        .link { font-weight: 900; color: #2879f3; text-decoration: underline; }
        .link:hover { color: #f37e10; }
      `}</style>
    </div>
  );
}